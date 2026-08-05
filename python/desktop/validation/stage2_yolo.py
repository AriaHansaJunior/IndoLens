"""
IndoLens Desktop – Tahap 2: YOLO Face Detection Validation
==========================================================

Tujuan:
    Memvalidasi bahwa model YOLO Face Detection mampu mendeteksi wajah 
    secara realtime pada frame hasil Window Capture.
    (Hanya mendeteksi wajah, belum ada FaceNet atau Identifikasi Aktor)

Catatan Penting:
    Preview OpenCV HANYA digunakan sementara untuk proses validasi.

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python desktop\\stage2_yolo.py
"""

import sys
import os
import ctypes
import ctypes.wintypes
import time
from typing import List, Tuple, Optional

import numpy as np
import cv2

# Tambahkan path root python agar bisa import dari modul yolo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import konfigurasi dan detector YOLO penelitian
try:
    from yolo.detector import detect_faces, load_model
    from config.config import YOLO_DEVICE
    import torch
    HAS_YOLO = True
    COMPUTE_DEVICE = "CUDA (GPU)" if torch.cuda.is_available() else "CPU"
except ImportError as e:
    HAS_YOLO = False
    print(f"[Error] Gagal mengimpor modul YOLO: {e}")


# ---------------------------------------------------------------------------
# Pastikan DPI-aware agar koordinat window selalu akurat
# ---------------------------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor DPI Aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Capture backend (DXCam / MSS)
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


# ---------------------------------------------------------------------------
# Windows API helpers
# ---------------------------------------------------------------------------

class _RECT(ctypes.Structure):
    _fields_ = [
        ("left",   ctypes.c_long),
        ("top",    ctypes.c_long),
        ("right",  ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

def _get_window_text(hwnd: int) -> str:
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value

def _get_largest_child_window(hwnd: int) -> int:
    """Mencari child window terbesar (biasanya viewport web / video player)."""
    largest_hwnd = hwnd
    max_area = 0

    def enum_child(child, _):
        nonlocal largest_hwnd, max_area
        if not ctypes.windll.user32.IsWindowVisible(child):
            return True
        rect = _RECT()
        ctypes.windll.user32.GetClientRect(child, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        area = w * h
        if area > max_area:
            max_area = area
            largest_hwnd = child
        return True

    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    ctypes.windll.user32.EnumChildWindows(hwnd, EnumChildProc(enum_child), 0)
    return largest_hwnd

def _get_client_rect_in_screen(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """Kembalikan (left, top, right, bottom) dari area video player."""
    target_hwnd = _get_largest_child_window(hwnd)
    client_rect = _RECT()
    ok = ctypes.windll.user32.GetClientRect(target_hwnd, ctypes.byref(client_rect))
    if not ok:
        return None

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(target_hwnd, ctypes.byref(pt))

    left   = pt.x
    top    = pt.y
    right  = pt.x + client_rect.right
    bottom = pt.y + client_rect.bottom

    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)

def list_windows() -> List[Tuple[int, str]]:
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    results = []
    SKIP = {"Program Manager", "Windows Shell Experience Host", ""}

    def callback(hwnd, _):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        title = _get_window_text(hwnd)
        if not title or title in SKIP:
            return True
        rect = _RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if (rect.right - rect.left) <= 0 or (rect.bottom - rect.top) <= 0:
            return True
        results.append((hwnd, title))
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
    results.sort(key=lambda x: x[1].lower())
    return results

def window_exists(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindow(hwnd))


class CaptureBackend:
    def __init__(self):
        self._mode = "none"
        self._dxcam = None
        self._mss   = None
        if HAS_DXCAM:
            try:
                self._dxcam = dxcam.create(output_color="BGR")
                self._mode  = "dxcam"
                return
            except Exception:
                pass
        if HAS_MSS:
            try:
                self._mss  = mss.mss()
                self._mode = "mss"
                return
            except Exception:
                pass

    def grab(self, left: int, top: int, right: int, bottom: int) -> Optional[np.ndarray]:
        if self._mode == "dxcam" and self._dxcam is not None:
            try:
                frame = self._dxcam.grab(region=(left, top, right, bottom))
                if frame is not None:
                    return np.asarray(frame)
            except Exception:
                pass
        elif self._mode == "mss" and self._mss is not None:
            try:
                monitor = {"left": left, "top": top, "width": right - left, "height": bottom - top}
                shot = self._mss.grab(monitor)
                return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
            except Exception:
                pass
        return None

    def release(self):
        if self._dxcam: del self._dxcam
        if self._mss: self._mss.close()

    @property
    def mode(self) -> str:
        return self._mode


# ---------------------------------------------------------------------------
# Pipeline & Preview Loop
# ---------------------------------------------------------------------------

def run_preview(hwnd: int, window_title: str, backend: CaptureBackend):
    PREVIEW_NAME = "IndoLens – Tahap 2: YOLO Face Detection"
    cv2.namedWindow(PREVIEW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PREVIEW_NAME, 960, 540)

    fps_list = []
    yolo_time_list = []
    
    # Pre-load model to avoid freeze on first frame
    print("[YOLO] Loading model into VRAM/RAM...")
    load_model()
    print("[YOLO] Model loaded.")

    print(f"\n[Preview] Target : {window_title} (hwnd={hwnd})")
    print(f"[Preview] Backend: {backend.mode.upper()}")
    print(f"[Preview] Compute: {COMPUTE_DEVICE}")
    print(f"[Preview] Tekan Q untuk keluar.\n")

    while True:
        t0 = time.perf_counter()

        # 1. Capture Frame (Window Tracking)
        if not window_exists(hwnd):
            break
        region = _get_client_rect_in_screen(hwnd)
        if region is None:
            if cv2.waitKey(30) & 0xFF == ord('q'): break
            continue

        left, top, right, bottom = region
        frame = backend.grab(left, top, right, bottom)
        if frame is None or frame.size == 0:
            if cv2.waitKey(10) & 0xFF == ord('q'): break
            continue

        h, w = frame.shape[:2]
        
        # 2. YOLO Face Detection
        t_yolo_start = time.perf_counter()
        
        # Call detect_faces directly to bypass cropping logic in predict_frame
        # since Stage 2 should only validate bounding boxes.
        results = detect_faces(frame)
        
        yolo_time_ms = (time.perf_counter() - t_yolo_start) * 1000
        yolo_time_list.append(yolo_time_ms)
        if len(yolo_time_list) > 30: yolo_time_list.pop(0)
        avg_yolo = sum(yolo_time_list) / len(yolo_time_list)

        faces_detected = 0

        # 3. Draw Bounding Boxes
        for result in results:
            boxes = result.boxes
            if boxes is None: continue
            
            for box in boxes:
                faces_detected += 1
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
                conf = float(box.conf[0].cpu().numpy().item())
                
                # Draw Box (Green)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw Label (Confidence only)
                label = f"Face {conf:.2f}"
                (txt_w, txt_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                
                cv2.rectangle(frame, (x1, y1 - txt_h - 10), (x1 + txt_w + 10, y1), (0, 255, 0), cv2.FILLED)
                cv2.putText(frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        # 4. Performance Metrics
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fps_list.append(elapsed_ms)
        if len(fps_list) > 30: fps_list.pop(0)
        avg_ms = sum(fps_list) / len(fps_list)
        fps_val = 1000 / avg_ms if avg_ms > 0 else 0

        info_lines = [
            f"Tahap 2 - YOLO Face Detection Validation",
            f"Target : {window_title[:45]}",
            f"Device : {COMPUTE_DEVICE}",
            f"Capture: {backend.mode.upper()}",
            f"FPS    : {fps_val:.1f} (Total: {avg_ms:.1f}ms)",
            f"YOLO   : {avg_yolo:.1f} ms",
            f"Faces  : {faces_detected}"
        ]

        for i, line in enumerate(info_lines):
            y = 22 + i * 22
            cv2.putText(frame, line, (11, y + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
            color = (0, 255, 128) if i == 0 else (200, 230, 255)
            cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        cv2.imshow(PREVIEW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


def select_window() -> Optional[Tuple[int, str]]:
    while True:
        windows = list_windows()
        if not windows:
            print("[Error] Tidak ada window aktif.")
            return None

        print("\n" + "=" * 60)
        print("  IndoLens – Tahap 2: YOLO Face Detection")
        print("=" * 60)
        for i, (hwnd, title) in enumerate(windows):
            print(f"  {i:<4} {title[:55]}")
        print(f"\n  R    Refresh | Q    Keluar")
        
        choice = input("\n  Pilih nomor window: ").strip().lower()
        if choice == 'q': return None
        if choice == 'r': continue
        
        try:
            idx = int(choice)
            if 0 <= idx < len(windows):
                return windows[idx]
            print("[Error] Nomor tidak valid.")
        except ValueError:
            print("[Error] Input tidak valid.")


def main():
    print("\n" + "=" * 60)
    print("  IndoLens Desktop – Tahap 2: YOLO Face Detection")
    print("  Pipeline: [Window Capture] -> [YOLO Bounding Box]")
    print("=" * 60)

    if not HAS_YOLO:
        print("[Error] Modul YOLO penelitian tidak ditemukan. Pastikan path benar.")
        sys.exit(1)

    backend = CaptureBackend()
    if backend.mode == "none":
        print("[Error] Tidak ada capture backend. Install dxcam atau mss.")
        sys.exit(1)

    selection = select_window()
    if selection:
        run_preview(selection[0], selection[1], backend)
    
    backend.release()

if __name__ == "__main__":
    main()
