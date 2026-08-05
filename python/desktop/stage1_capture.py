"""
IndoLens Desktop – Tahap 1: Window Capture Validation
======================================================

Tujuan:
    Membuktikan bahwa DXCam (atau MSS sebagai fallback) berhasil
    menangkap frame video secara realtime dari window target yang
    dipilih pengguna, dan menampilkannya dalam window preview OpenCV.

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python desktop\\stage1_capture.py

Kontrol preview:
    Q  = keluar
    R  = refresh daftar window
"""

import sys
import ctypes
import ctypes.wintypes
import time
from typing import List, Tuple, Optional

import numpy as np
import cv2

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
# Capture backend
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


def _get_client_rect_in_screen(hwnd: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Kembalikan (left, top, right, bottom) dari area client window dalam koordinat layar.
    Menggunakan ClientToScreen agar tidak termasuk border/titlebar.
    """
    client_rect = _RECT()
    ok = ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client_rect))
    if not ok:
        return None

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    pt = POINT(0, 0)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(pt))

    left   = pt.x
    top    = pt.y
    right  = pt.x + client_rect.right
    bottom = pt.y + client_rect.bottom

    if right <= left or bottom <= top:
        return None

    return (left, top, right, bottom)


def list_windows() -> List[Tuple[int, str]]:
    """
    Kembalikan list (hwnd, title) dari semua window yang terlihat dan punya judul.
    Diurutkan secara alfabetis berdasarkan judul.
    """
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                          ctypes.wintypes.HWND,
                                          ctypes.wintypes.LPARAM)
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
        w = rect.right  - rect.left
        h = rect.bottom - rect.top
        if w <= 0 or h <= 0:
            return True
        results.append((hwnd, title))
        return True

    ctypes.windll.user32.EnumWindows(EnumWindowsProc(callback), 0)
    results.sort(key=lambda x: x[1].lower())
    return results


def window_exists(hwnd: int) -> bool:
    return bool(ctypes.windll.user32.IsWindow(hwnd))


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

class CaptureBackend:
    """
    Wrapper sederhana yang mencoba DXCam terlebih dahulu, lalu MSS sebagai fallback.
    Mengembalikan frame dalam format BGR (format OpenCV).
    """

    def __init__(self):
        self._mode = "none"
        self._dxcam = None
        self._mss   = None
        self._init()

    def _init(self):
        if HAS_DXCAM:
            try:
                self._dxcam = dxcam.create(output_color="BGR")
                self._mode  = "dxcam"
                print(f"[Capture] Backend: DXCam (GPU)")
                return
            except Exception as e:
                print(f"[Capture] DXCam gagal: {e}")

        if HAS_MSS:
            try:
                self._mss  = mss.mss()
                self._mode = "mss"
                print(f"[Capture] Backend: MSS (CPU fallback)")
                return
            except Exception as e:
                print(f"[Capture] MSS gagal: {e}")

        print("[Capture] TIDAK ADA backend yang tersedia!")

    def grab(self, left: int, top: int, right: int, bottom: int) -> Optional[np.ndarray]:
        """Ambil satu frame dari region layar. Kembalikan BGR numpy array."""
        if self._mode == "dxcam" and self._dxcam is not None:
            try:
                frame = self._dxcam.grab(region=(left, top, right, bottom))
                if frame is None:
                    return None
                # DXCam dengan output_color=BGR sudah langsung BGR
                return np.asarray(frame)
            except Exception as e:
                print(f"[Capture] DXCam error: {e}")
                return None

        elif self._mode == "mss" and self._mss is not None:
            try:
                monitor = {"left": left, "top": top,
                           "width": right - left, "height": bottom - top}
                shot = self._mss.grab(monitor)
                # MSS → BGRA → BGR
                return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)
            except Exception as e:
                print(f"[Capture] MSS error: {e}")
                return None

        return None

    def release(self):
        try:
            if self._dxcam:
                del self._dxcam
                self._dxcam = None
        except Exception:
            pass
        try:
            if self._mss:
                self._mss.close()
                self._mss = None
        except Exception:
            pass

    @property
    def mode(self) -> str:
        return self._mode


# ---------------------------------------------------------------------------
# Preview Loop
# ---------------------------------------------------------------------------

def run_preview(hwnd: int, window_title: str, backend: CaptureBackend):
    """
    Loop utama: tangkap frame dari window target dan tampilkan di preview OpenCV.

    Fitur:
    - Preview ikut resize/reposition otomatis saat window target digeser.
    - Overlay info: backend, FPS, ukuran frame, nama window.
    - Tekan Q untuk keluar.
    """
    PREVIEW_NAME = "IndoLens – Tahap 1: Window Capture"
    cv2.namedWindow(PREVIEW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(PREVIEW_NAME, 960, 540)

    fps_list   = []
    frame_num  = 0
    last_shape = (0, 0)

    print(f"\n[Preview] Target : {window_title} (hwnd={hwnd})")
    print(f"[Preview] Backend: {backend.mode.upper()}")
    print(f"[Preview] Tekan Q untuk keluar.\n")

    while True:
        t0 = time.perf_counter()

        # --- Cek window masih ada ---
        if not window_exists(hwnd):
            print("[Preview] Window target ditutup. Keluar.")
            break

        # --- Baca posisi client area terkini (auto-track) ---
        region = _get_client_rect_in_screen(hwnd)
        if region is None:
            # Window mungkin diminimize — skip frame ini
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
            continue

        left, top, right, bottom = region

        # --- Capture ---
        frame = backend.grab(left, top, right, bottom)
        if frame is None or frame.size == 0:
            if cv2.waitKey(10) & 0xFF == ord('q'):
                break
            continue

        h, w = frame.shape[:2]

        # --- FPS ---
        elapsed_ms = (time.perf_counter() - t0) * 1000
        fps_list.append(elapsed_ms)
        if len(fps_list) > 30:
            fps_list.pop(0)
        avg_ms  = sum(fps_list) / len(fps_list)
        fps_val = 1000 / avg_ms if avg_ms > 0 else 0

        # --- Overlay info di frame ---
        info_lines = [
            f"Tahap 1 - Window Capture Validation",
            f"Target : {window_title[:50]}",
            f"Backend: {backend.mode.upper()}",
            f"Size   : {w} x {h} px",
            f"FPS    : {fps_val:.1f}",
            f"Latency: {elapsed_ms:.1f} ms",
        ]

        for i, line in enumerate(info_lines):
            y = 22 + i * 22
            # Shadow
            cv2.putText(frame, line, (11, y + 1),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
            # Text
            color = (0, 255, 128) if i == 0 else (200, 230, 255)
            cv2.putText(frame, line, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

        cv2.imshow(PREVIEW_NAME, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("[Preview] Keluar.")
            break

        frame_num += 1

    cv2.destroyAllWindows()


# ---------------------------------------------------------------------------
# Window Selector (terminal)
# ---------------------------------------------------------------------------

def select_window() -> Optional[Tuple[int, str]]:
    """Tampilkan daftar window di terminal dan minta user memilih nomor."""
    while True:
        windows = list_windows()
        if not windows:
            print("[Error] Tidak ada window yang ditemukan.")
            return None

        print("\n" + "=" * 60)
        print("  IndoLens – Tahap 1: Window Capture")
        print("=" * 60)
        print(f"  {'No.':<5} {'Title'}")
        print(f"  {'-'*5} {'-'*50}")
        for i, (hwnd, title) in enumerate(windows):
            short = title[:50] + ("…" if len(title) > 50 else "")
            print(f"  {i:<5} {short}")
        print(f"\n  {'R':<5} Refresh daftar window")
        print(f"  {'Q':<5} Keluar")
        print("=" * 60)

        choice = input("  Pilih nomor window: ").strip().lower()

        if choice == 'q':
            return None
        if choice == 'r':
            continue

        try:
            idx = int(choice)
            if 0 <= idx < len(windows):
                hwnd, title = windows[idx]
                if not window_exists(hwnd):
                    print(f"[Error] Window sudah tidak ada. Silakan refresh.")
                    continue
                return hwnd, title
            else:
                print(f"[Error] Nomor tidak valid (0 – {len(windows)-1}).")
        except ValueError:
            print("[Error] Masukkan angka yang valid.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("\n" + "=" * 60)
    print("  IndoLens Desktop – Tahap 1: Window Capture Validation")
    print("  Pipeline: [Window Capture]")
    print("=" * 60)

    backend = CaptureBackend()
    if backend.mode == "none":
        print("[Error] Tidak ada capture backend. Install dxcam atau mss.")
        sys.exit(1)

    selection = select_window()
    if selection is None:
        print("Keluar.")
        sys.exit(0)

    hwnd, title = selection
    run_preview(hwnd, title, backend)

    backend.release()
    print("Selesai.")


if __name__ == "__main__":
    main()
