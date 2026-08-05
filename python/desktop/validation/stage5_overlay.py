"""
IndoLens Desktop – Tahap 5: Transparent Overlay Validation
==========================================================

Tujuan:
    Mengganti media visualisasi dari OpenCV Preview menjadi 
    Transparent Desktop Overlay menggunakan PyQt5.
    (Pipeline AI 100% menggunakan Tahap 4 tanpa modifikasi)

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python desktop\\stage5_overlay.py
"""

import sys
import os
import time
import ctypes
import ctypes.wintypes
from typing import List, Tuple, Optional

import numpy as np

# Tambahkan path root python agar bisa import dari modul yolo, facenet, dan recognition
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QComboBox, QDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics

# Import AI modules
try:
    from yolo.detector import load_model as yolo_load_model, predict_frame
    from facenet.embedding_generator import load_facenet_model, generate_embedding
    from recognition.embedding_matcher import load_all_embeddings, find_best_match
    from config.config import FACE_DISTANCE_THRESHOLD
    import torch
    HAS_AI = True
    COMPUTE_DEVICE = "CUDA (GPU)" if torch.cuda.is_available() else "CPU"
except ImportError as e:
    HAS_AI = False
    print(f"[Error] Gagal mengimpor modul AI: {e}")

# ---------------------------------------------------------------------------
# Pastikan DPI-aware
# ---------------------------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Capture & Windows API Helpers (Sama seperti Tahap 4)
# ---------------------------------------------------------------------------
try:
    import dxcam
    HAS_DXCAM = True
except ImportError:
    HAS_DXCAM = False

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

class _RECT(ctypes.Structure):
    _fields_ = [
        ("left",   ctypes.c_long),
        ("top",    ctypes.c_long),
        ("right",  ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

def _get_window_text(hwnd: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0: return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def _get_largest_child_window(hwnd: int) -> int:
    largest_hwnd = hwnd
    max_area = 0
    def enum_child(child, _):
        nonlocal largest_hwnd, max_area
        if not ctypes.windll.user32.IsWindowVisible(child): return True
        rect = _RECT()
        ctypes.windll.user32.GetClientRect(child, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        area = w * h
        if area > max_area:
            max_area, largest_hwnd = area, child
        return True
    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    ctypes.windll.user32.EnumChildWindows(hwnd, EnumChildProc(enum_child), 0)
    return largest_hwnd

def _get_client_rect_in_screen(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    target_hwnd = _get_largest_child_window(hwnd)
    client_rect = _RECT()
    if not ctypes.windll.user32.GetClientRect(target_hwnd, ctypes.byref(client_rect)): return None
    class POINT(ctypes.Structure): _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(target_hwnd, ctypes.byref(pt))
    left, top = pt.x, pt.y
    right, bottom = pt.x + client_rect.right, pt.y + client_rect.bottom
    if right <= left or bottom <= top: return None
    return (left, top, right, bottom)

def list_windows() -> List[Tuple[int, str]]:
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    results = []
    SKIP = {"Program Manager", "Windows Shell Experience Host", ""}
    def callback(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd): return True
        title = _get_window_text(hwnd)
        if not title or title in SKIP: return True
        rect = _RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if (rect.right - rect.left) > 0 and (rect.bottom - rect.top) > 0:
            results.append((hwnd, title))
        return True
    ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
    results.sort(key=lambda x: x[1].lower())
    return results

def window_exists(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindow(hwnd))

def check_fullscreen(rect: Tuple[int, int, int, int]) -> bool:
    screen_w = ctypes.windll.user32.GetSystemMetrics(0)
    screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    w = rect[2] - rect[0]
    h = rect[3] - rect[1]
    # Toleransi beberapa pixel
    return abs(w - screen_w) <= 10 and abs(h - screen_h) <= 10

class CaptureBackend:
    def __init__(self):
        self._mode, self._dxcam, self._mss = "none", None, None
        if HAS_DXCAM:
            try:
                self._dxcam = dxcam.create(output_color="BGR")
                self._mode = "dxcam"
                return
            except Exception: pass
        if HAS_MSS:
            try:
                self._mss, self._mode = mss.mss(), "mss"
                return
            except Exception: pass

    def grab(self, left: int, top: int, right: int, bottom: int) -> Optional[np.ndarray]:
        if self._mode == "dxcam" and self._dxcam:
            try:
                frame = self._dxcam.grab(region=(left, top, right, bottom))
                if frame is not None: return np.asarray(frame)
            except Exception: pass
        elif self._mode == "mss" and self._mss:
            try:
                shot = self._mss.grab({"left": left, "top": top, "width": right - left, "height": bottom - top})
                return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
            except Exception: pass
        return None

    def release(self):
        if self._dxcam: del self._dxcam
        if self._mss: self._mss.close()


# ---------------------------------------------------------------------------
# Thread: AI Pipeline (Tanpa blok GUI)
# ---------------------------------------------------------------------------

class InferenceThread(QThread):
    # Signals: (frame_width, frame_height, detections_list)
    update_detections = pyqtSignal(int, int, list)
    fullscreen_detected = pyqtSignal()
    window_closed = pyqtSignal()

    def __init__(self, hwnd: int, all_embeddings: dict):
        super().__init__()
        self.hwnd = hwnd
        self.all_actor_embeddings = all_embeddings
        self.backend = CaptureBackend()
        self.running = True

    def run(self):
        fps_list, yolo_list, facenet_list, eucl_list = [], [], [], []
        
        while self.running:
            t0 = time.perf_counter()
            
            if not window_exists(self.hwnd):
                self.window_closed.emit()
                break

            region = _get_client_rect_in_screen(self.hwnd)
            if region is None:
                time.sleep(0.05)
                continue

            if check_fullscreen(region):
                self.fullscreen_detected.emit()
                break # Revisi 1: Langsung hentikan loop AI jika target fullscreen

            frame = self.backend.grab(*region)
            if frame is None or frame.size == 0:
                time.sleep(0.01)
                continue
            
            h_frame, w_frame = frame.shape[:2]

            # YOLO Phase
            t_yolo = time.perf_counter()
            detections = predict_frame(frame)
            yolo_ms = (time.perf_counter() - t_yolo) * 1000

            # FaceNet + Euclidean Phase
            t_fn = time.perf_counter()
            t_eucl_total = 0.0
            faces_processed = 0

            output_detections = []

            for idx, det in enumerate(detections):
                crop_img = det.get("crop")
                rec_result = {"actor": "Tidak Dikenali", "distance": 999.0, "status": "unknown"}
                
                if crop_img is not None and crop_img.size > 0:
                    faces_processed += 1
                    
                    emb = generate_embedding(crop_img)
                    
                    if emb is not None and len(emb) == 128:
                        t_eucl = time.perf_counter()
                        rec_result = find_best_match(emb, self.all_actor_embeddings, threshold=FACE_DISTANCE_THRESHOLD)
                        t_eucl_total += (time.perf_counter() - t_eucl) * 1000
                
                # Terminal Logging only (Revisi 4.1 & 5)
                if rec_result["distance"] < 999.0:
                    print(f"[Euclidean Log] Face #{idx+1} | Actor: {rec_result['actor']} | Dist: {rec_result['distance']:.4f} | Status: {rec_result['status']}     ", end="\r")

                output_detections.append({
                    "bbox": det["bbox"],
                    "actor": rec_result["actor"],
                    "status": rec_result["status"]
                })

            fn_ms = (time.perf_counter() - t_fn) * 1000 - t_eucl_total
            
            # Metrics calculation for terminal
            if faces_processed > 0:
                yolo_list.append(yolo_ms)
                facenet_list.append(fn_ms)
                eucl_list.append(t_eucl_total)
                if len(yolo_list) > 30: yolo_list.pop(0)
                if len(facenet_list) > 30: facenet_list.pop(0)
                if len(eucl_list) > 30: eucl_list.pop(0)

            elapsed_ms = (time.perf_counter() - t0) * 1000
            fps_list.append(elapsed_ms)
            if len(fps_list) > 30: fps_list.pop(0)
            avg_ms = sum(fps_list) / len(fps_list)
            fps_val = 1000 / avg_ms if avg_ms > 0 else 0
            
            avg_yolo = sum(yolo_list) / len(yolo_list) if yolo_list else 0.0
            avg_fn = sum(facenet_list) / len(facenet_list) if facenet_list else 0.0
            avg_eucl = sum(eucl_list) / len(eucl_list) if eucl_list else 0.0

            # Print metrics to terminal (tidak tampil di UI)
            if int(time.time() * 10) % 10 == 0:  # Print about once per second without spamming too much
                print(f"[Metrics] FPS: {fps_val:.1f} | YOLO: {avg_yolo:.1f}ms | FaceNet: {avg_fn:.1f}ms | Euclidean: {avg_eucl:.2f}ms     ", end="\r")

            # Emit to GUI
            self.update_detections.emit(w_frame, h_frame, output_detections)

    def stop(self):
        self.running = False
        self.backend.release()
        self.wait()


# ---------------------------------------------------------------------------
# UI: Transparent Overlay
# ---------------------------------------------------------------------------

class OverlayWindow(QWidget):
    def __init__(self, target_hwnd):
        super().__init__()
        self.target_hwnd = target_hwnd
        self.detections = []
        self.frame_w = 1
        self.frame_h = 1
        
        # Transparent, Always on Top, Click-Through, Frameless
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Enable true click-through on Windows
        hwnd = int(self.winId())
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)

        # Timer untuk sync posisi overlay ke target window
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_geometry)
        self.sync_timer.start(16)  # ~60Hz tracking

    def update_data(self, fw, fh, dets):
        self.frame_w = fw
        self.frame_h = fh
        self.detections = dets
        self.update()  # Trigger paintEvent

    def sync_geometry(self):
        region = _get_client_rect_in_screen(self.target_hwnd)
        if region:
            left, top, right, bottom = region
            self.setGeometry(left, top, right - left, bottom - top)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dynamic Scaling
        w_overlay = self.width()
        h_overlay = self.height()
        scale_x = w_overlay / self.frame_w if self.frame_w > 0 else 1.0
        scale_y = h_overlay / self.frame_h if self.frame_h > 0 else 1.0

        for det in self.detections:
            x1, y1, x2, y2 = det["bbox"]
            actor = det["actor"]
            status = det["status"]

            # Scale bounding box ke ukuran window overlay
            sx1 = int(x1 * scale_x)
            sy1 = int(y1 * scale_y)
            sx2 = int(x2 * scale_x)
            sy2 = int(y2 * scale_y)

            color = QColor(0, 255, 0) if status == "known" else QColor(255, 0, 0)
            
            # Draw Box
            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawRect(sx1, sy1, sx2 - sx1, sy2 - sy1)

            # Draw Label (Nama Aktor saja)
            font = QFont("Segoe UI", 10, QFont.Bold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            
            text_rect = metrics.boundingRect(actor)
            text_rect.moveTo(sx1, sy1 - text_rect.height() - 5)
            text_rect.adjust(-5, -2, 5, 2)

            # Background Label
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(text_rect)

            # Text
            text_color = Qt.black if status == "known" else Qt.white
            painter.setPen(text_color)
            painter.drawText(text_rect, Qt.AlignCenter, actor)

        painter.end()


# ---------------------------------------------------------------------------
# UI: Fullscreen Warning Dialog
# ---------------------------------------------------------------------------

class FullscreenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Peringatan IndoLens")
        self.setFixedSize(350, 150)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        label = QLabel("Mode fullscreen terdeteksi.\nIndoLens hanya dapat digunakan pada mode window.\nSistem AI telah dihentikan.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Tutup")
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)


# ---------------------------------------------------------------------------
# UI: Controller Window
# ---------------------------------------------------------------------------

class ControllerWindow(QWidget):
    def __init__(self, all_embeddings):
        super().__init__()
        self.all_actor_embeddings = all_embeddings
        self.thread = None
        self.overlay = None
        self.is_running = False

        self.setWindowTitle("IndoLens Controller")
        self.setFixedSize(300, 180)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        # Window Selector
        self.combo = QComboBox()
        self.refresh_windows()
        layout.addWidget(QLabel("Pilih Target Window:"))
        layout.addWidget(self.combo)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_on = QPushButton("▶ ON")
        self.btn_off = QPushButton("⏹ OFF")
        self.btn_off.setEnabled(False)
        
        self.btn_on.clicked.connect(self.start_inference)
        self.btn_off.clicked.connect(self.stop_inference)
        
        btn_layout.addWidget(self.btn_on)
        btn_layout.addWidget(self.btn_off)
        layout.addLayout(btn_layout)

        # Status
        self.lbl_status = QLabel(f"Status: OFF\nDevice: {COMPUTE_DEVICE}")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        self.setLayout(layout)

    def refresh_windows(self):
        self.combo.clear()
        for hwnd, title in list_windows():
            self.combo.addItem(title[:40], hwnd)

    def start_inference(self):
        hwnd = self.combo.currentData()
        if not hwnd or not window_exists(hwnd):
            QMessageBox.warning(self, "Error", "Window target tidak ditemukan!")
            self.refresh_windows()
            return

        self.is_running = True
        self.btn_on.setEnabled(False)
        self.combo.setEnabled(False)
        self.btn_off.setEnabled(True)
        self.lbl_status.setText("Status: RUNNING")

        # Start Overlay
        self.overlay = OverlayWindow(hwnd)
        self.overlay.show()

        # Start AI Thread
        self.thread = InferenceThread(hwnd, self.all_actor_embeddings)
        self.thread.update_detections.connect(self.overlay.update_data)
        self.thread.fullscreen_detected.connect(self.handle_fullscreen)
        self.thread.window_closed.connect(self.stop_inference)
        self.thread.start()

    def stop_inference(self):
        self.is_running = False
        if self.thread:
            self.thread.stop()
            self.thread = None
        if self.overlay:
            self.overlay.close()
            self.overlay = None

        self.btn_on.setEnabled(True)
        self.combo.setEnabled(True)
        self.btn_off.setEnabled(False)
        self.lbl_status.setText(f"Status: OFF\nDevice: {COMPUTE_DEVICE}")

    def handle_fullscreen(self):
        # Revisi 1: Stop AI secara total, hancurkan overlay, dan lepaskan model dari GPU
        self.stop_inference()
        
        dialog = FullscreenDialog(self)
        dialog.exec_()


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  IndoLens Desktop – Tahap 5: Transparent Overlay")
    print("  Pipeline: Capture -> YOLO -> FaceNet -> Overlay")
    print("=" * 60)

    if not HAS_AI:
        print("[Error] Gagal meload modul AI penelitian.")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 1. Preload Models
    print("\n[AI] Loading YOLO & FaceNet models into memory/VRAM...")
    yolo_load_model()
    load_facenet_model()
    
    # 2. Preload Embedding Dataset Cache
    print("[AI] Loading Embedding Dataset Cache to RAM...")
    all_actor_embeddings = load_all_embeddings()
    loaded_actors = len(all_actor_embeddings.keys())
    print(f"[AI] Successfully loaded embedding dataset for {loaded_actors} actors.")

    # 3. Launch Controller UI
    controller = ControllerWindow(all_actor_embeddings)
    controller.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
