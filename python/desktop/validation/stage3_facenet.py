"""
IndoLens Desktop – Tahap 3: FaceNet Integration Validation
==========================================================

Tujuan:
    Memvalidasi bahwa FaceNet mampu menghasilkan 128-D embedding dari
    crop wajah hasil deteksi YOLO secara realtime tanpa mengubah metodologi.
    (Belum ada pencocokan aktor / Euclidean Distance).

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python desktop\\stage3_facenet.py
"""

import sys
import os
import ctypes
import ctypes.wintypes
import time
from typing import List, Tuple, Optional

import numpy as np
import cv2

# Tambahkan path root python agar bisa import dari modul yolo & facenet
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modul penelitian
try:
    from yolo.detector import load_model as yolo_load_model, predict_frame
    from facenet.embedding_generator import load_facenet_model, generate_embedding
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

def run_preview(hwnd: int, window_title: str, backend: CaptureBackend):
    PREVIEW_NAME = "IndoLens – Tahap 3: FaceNet Integration"
    cv2.namedWindow(PREVIEW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PREVIEW_NAME, 960, 540)

    fps_list, yolo_time_list, facenet_time_list = [], [], []
    
    # Pre-load models to avoid freeze on first frame
    print("[AI] Loading YOLO & FaceNet models into memory/VRAM...")
    yolo_load_model()
    load_facenet_model()
    print("[AI] Models loaded successfully.")

    print(f"\n[Preview] Target : {window_title[:50]} (hwnd={hwnd})")
    print(f"[Preview] Capture: {backend.mode.upper()}")
    print(f"[Preview] Compute: {COMPUTE_DEVICE}")
    print(f"[Preview] Tekan Q untuk keluar.\n")

    while True:
        t0 = time.perf_counter()

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
        # predict_frame akan menjalankan yolo dan melakukan crop (face extraction)
        t_yolo = time.perf_counter()
        detections = predict_frame(frame)
        yolo_ms = (time.perf_counter() - t_yolo) * 1000
        
        yolo_time_list.append(yolo_ms)
        if len(yolo_time_list) > 30: yolo_time_list.pop(0)
        avg_yolo = sum(yolo_time_list) / len(yolo_time_list)

        # 3. FaceNet Embedding Generation
        t_fn = time.perf_counter()
        faces_processed = 0
        
        for idx, det in enumerate(detections):
            crop_img = det.get("crop")
            if crop_img is not None and crop_img.size > 0:
                t_emb_start = time.perf_counter()
                emb = generate_embedding(crop_img)
                t_emb_ms = (time.perf_counter() - t_emb_start) * 1000
                faces_processed += 1
                
                det["embedding_generated"] = True if (emb is not None and len(emb) == 128) else False
                
                # Log detail embedding ke terminal (Revisi 1: detail 128-D di console, bukan di UI)
                if det["embedding_generated"]:
                    print(f"[FaceNet Log] Face #{idx+1} | Embedding Shape: {emb.shape} | Extraction Time: {t_emb_ms:.1f} ms", end="\r")
        
        fn_ms = (time.perf_counter() - t_fn) * 1000
        if faces_processed > 0:
            facenet_time_list.append(fn_ms)
            if len(facenet_time_list) > 30: facenet_time_list.pop(0)
        avg_facenet = sum(facenet_time_list) / len(facenet_time_list) if facenet_time_list else 0.0

        # 4. Draw Bounding Boxes & Validation Status
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]
            has_emb = det.get("embedding_generated", False)
            
            # Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Label clean sesuai Revisi 1: "Embedding OK" / "Embedding FAIL"
            label = "Embedding OK" if has_emb else "Embedding FAIL"
            full_label = f"{label} ({conf:.2f})"
            
            (txt_w, txt_h), _ = cv2.getTextSize(full_label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - txt_h - 10), (x1 + txt_w + 10, y1), (0, 255, 0), cv2.FILLED)
            cv2.putText(frame, full_label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        # 5. Performance Metrics Overlay
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fps_list.append(elapsed_ms)
        if len(fps_list) > 30: fps_list.pop(0)
        avg_ms = sum(fps_list) / len(fps_list)
        fps_val = 1000 / avg_ms if avg_ms > 0 else 0

        info_lines = [
            f"Tahap 3 - FaceNet Integration Validation",
            f"Device : {COMPUTE_DEVICE}",
            f"FPS    : {fps_val:.1f} (Latency: {avg_ms:.1f}ms)",
            f"YOLO   : {avg_yolo:.1f} ms",
            f"FaceNet: {avg_facenet:.1f} ms",
            f"Faces  : {faces_processed}"
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
        print("  IndoLens – Tahap 3: FaceNet Integration")
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
    print("  IndoLens Desktop – Tahap 3: FaceNet")
    print("  Pipeline: Capture -> YOLO Crop -> FaceNet Embedding")
    print("=" * 60)

    if not HAS_AI:
        print("[Error] Gagal meload modul AI penelitian.")
        sys.exit(1)

    backend = CaptureBackend()
    if backend.mode == "none":
        print("[Error] Tidak ada capture backend. Install dxcam/mss.")
        sys.exit(1)

    selection = select_window()
    if selection:
        run_preview(selection[0], selection[1], backend)
    
    backend.release()


if __name__ == "__main__":
    main()
