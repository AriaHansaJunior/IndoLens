"""
IndoLens Desktop – Tahap 4: Euclidean Distance Recognition Validation
=====================================================================

Tujuan:
    Memvalidasi bahwa sistem mampu mengidentifikasi identitas aktor 
    menggunakan Euclidean Distance terhadap dataset embedding yang 
    telah dibuat, tanpa mengubah metodologi penelitian.

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python desktop\\stage4_recognition.py
"""

import sys
import os
import ctypes
import ctypes.wintypes
import time
from typing import List, Tuple, Optional

import numpy as np
import cv2

# Tambahkan path root python agar bisa import dari modul yolo, facenet, dan recognition
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modul penelitian
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
# Pastikan DPI-aware agar koordinat window selalu akurat
# ---------------------------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
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
    
    @property
    def mode(self) -> str: return self._mode


# ---------------------------------------------------------------------------
# Pipeline & Preview Loop
# ---------------------------------------------------------------------------

def run_preview(hwnd: int, window_title: str, backend: CaptureBackend, all_actor_embeddings: dict):
    PREVIEW_NAME = "IndoLens – Tahap 4: Euclidean Distance Recognition"
    cv2.namedWindow(PREVIEW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PREVIEW_NAME, 960, 540)

    fps_list, yolo_time_list, facenet_time_list, eucl_time_list = [], [], [], []
    
    print(f"\n[Preview] Target : {window_title[:50]} (hwnd={hwnd})")
    print(f"[Preview] Capture: {backend.mode.upper()}")
    print(f"[Preview] Compute: {COMPUTE_DEVICE}")
    print(f"[Preview] Threshold: {FACE_DISTANCE_THRESHOLD}")
    print(f"[Preview] Tekan Q untuk keluar.\n")

    while True:
        t0 = time.perf_counter()
        
        total_known = 0
        total_unknown = 0
        faces_processed = 0

        # 1. Capture Frame
        if not window_exists(hwnd): break
        region = _get_client_rect_in_screen(hwnd)
        if region is None:
            if cv2.waitKey(30) & 0xFF == ord('q'): break
            continue

        frame = backend.grab(*region)
        if frame is None or frame.size == 0:
            if cv2.waitKey(10) & 0xFF == ord('q'): break
            continue
        
        # 2. YOLO Face Detection & Crop
        t_yolo = time.perf_counter()
        detections = predict_frame(frame)
        yolo_ms = (time.perf_counter() - t_yolo) * 1000
        
        yolo_time_list.append(yolo_ms)
        if len(yolo_time_list) > 30: yolo_time_list.pop(0)
        avg_yolo = sum(yolo_time_list) / len(yolo_time_list)

        # 3. FaceNet Embedding & 4. Euclidean Distance Comparison
        t_fn = time.perf_counter()
        t_eucl_total = 0.0
        
        for idx, det in enumerate(detections):
            crop_img = det.get("crop")
            
            # Default fallback jika gagal diproses
            det["recognition"] = {"actor": "Tidak Dikenali", "distance": 999.0, "status": "unknown"}
            
            if crop_img is not None and crop_img.size > 0:
                faces_processed += 1
                
                # Ekstraksi Embedding
                emb = generate_embedding(crop_img)
                
                # Hitung Euclidean Distance & Thresholding (hanya jika berhasil membuat embedding)
                if emb is not None and len(emb) == 128:
                    t_eucl = time.perf_counter()
                    
                    # Reuse modul embedding_matcher & threshold asli
                    rec_result = find_best_match(emb, all_actor_embeddings, threshold=FACE_DISTANCE_THRESHOLD)
                    
                    t_eucl_ms = (time.perf_counter() - t_eucl) * 1000
                    t_eucl_total += t_eucl_ms
                    det["recognition"] = rec_result
                    
                    # Log detail ke terminal (Revisi 1: Detail distance di terminal, bukan di UI)
                    print(f"[Euclidean Log] Face #{idx+1} | Actor: {rec_result['actor']} | Distance: {rec_result['distance']:.4f} | Threshold: {FACE_DISTANCE_THRESHOLD} | Status: {rec_result['status']}", end="\r")
                
                status = det["recognition"]["status"]
                if status == "known":
                    total_known += 1
                else:
                    total_unknown += 1
        
        fn_ms = (time.perf_counter() - t_fn) * 1000 - t_eucl_total  # Waktu murni FaceNet (tanpa Euclidean)
        if faces_processed > 0:
            facenet_time_list.append(fn_ms)
            if len(facenet_time_list) > 30: facenet_time_list.pop(0)
            
            eucl_time_list.append(t_eucl_total)
            if len(eucl_time_list) > 30: eucl_time_list.pop(0)
            
        avg_facenet = sum(facenet_time_list) / len(facenet_time_list) if facenet_time_list else 0.0
        avg_eucl = sum(eucl_time_list) / len(eucl_time_list) if eucl_time_list else 0.0

        # 5. Draw Bounding Boxes & Identity Status
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            rec = det["recognition"]
            
            # Box color: Hijau = Known, Merah = Unknown
            color = (0, 255, 0) if rec["status"] == "known" else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Label clean sesuai Revisi 1: Hanya Nama Aktor atau "Tidak Dikenali" (tanpa nilai distance di UI)
            label = rec['actor']
            
            (txt_w, txt_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - txt_h - 10), (x1 + txt_w + 10, y1), color, cv2.FILLED)
            
            text_color = (0, 0, 0) if rec["status"] == "known" else (255, 255, 255)
            cv2.putText(frame, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1, cv2.LINE_AA)

        # 6. Performance & Counters Metrics Overlay
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fps_list.append(elapsed_ms)
        if len(fps_list) > 30: fps_list.pop(0)
        avg_ms = sum(fps_list) / len(fps_list)
        fps_val = 1000 / avg_ms if avg_ms > 0 else 0

        info_lines = [
            f"Tahap 4 - Euclidean Distance Recognition Validation",
            f"Device : {COMPUTE_DEVICE}",
            f"FPS    : {fps_val:.1f} (Total Latency: {avg_ms:.1f}ms)",
            f"YOLO   : {avg_yolo:.1f} ms",
            f"FaceNet: {avg_facenet:.1f} ms",
            f"Euclid : {avg_eucl:.2f} ms",
            f"Faces  : {faces_processed} | Known: {total_known} | Unknown: {total_unknown}"
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
        print("  IndoLens – Tahap 4: Euclidean Distance Recognition")
        print("=" * 60)
        for i, (hwnd, title) in enumerate(windows):
            print(f"  {i:<4} {title[:55]}")
        choice = input("\n  Pilih window (atau Q untuk keluar): ").strip().lower()
        if choice == 'q': return None
        if choice == 'r': continue
        try:
            idx = int(choice)
            if 0 <= idx < len(windows): return windows[idx]
            print("[Error] Nomor tidak valid.")
        except ValueError:
            print("[Error] Input tidak valid.")


def main():
    print("\n" + "=" * 60)
    print("  IndoLens Desktop – Tahap 4: Euclidean Distance Recognition")
    print("  Pipeline: Capture -> YOLO -> FaceNet -> Euclidean Distance")
    print("=" * 60)

    if not HAS_AI:
        print("[Error] Gagal meload modul AI penelitian.")
        sys.exit(1)

    backend = CaptureBackend()
    if backend.mode == "none":
        print("[Error] Tidak ada capture backend. Install dxcam/mss.")
        sys.exit(1)

    # 1. Preload Models
    print("\n[AI] Loading YOLO & FaceNet models into memory/VRAM...")
    yolo_load_model()
    load_facenet_model()
    print("[AI] Models loaded successfully.")

    # 2. Preload Embedding Dataset (Revisi 2: Menggunakan istilah Embedding Dataset / Cache)
    print("\n[AI] Loading Embedding Dataset to RAM...")
    all_actor_embeddings = load_all_embeddings()
    loaded_actors = len(all_actor_embeddings.keys())
    print(f"[AI] Successfully loaded embedding dataset for {loaded_actors} actors.")
    
    if loaded_actors == 0:
        print("[Peringatan] Dataset embedding KOSONG! Semua wajah akan menjadi 'Tidak Dikenali'.")

    # 3. Select Target Window
    selection = select_window()
    if selection:
        run_preview(selection[0], selection[1], backend, all_actor_embeddings)
    
    backend.release()


if __name__ == "__main__":
    main()
