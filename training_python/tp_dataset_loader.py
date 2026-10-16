# hanya untuk keperluan training python local, tidak dirun di web
"""
tp_dataset_loader.py — Resolusi path gambar dari database ke Laravel storage secara aman.

Fitur:
1. Menghubungkan relasi MySQL actors.id -> actor_images.actor_id.
2. Memetakan path relatif (misal: actor-images/1-bayu-skak/bayu-skak-01.jpg) ke absolute path di storage/app/public.
3. Mencegah path traversal (reject path yang keluar dari STORAGE_PUBLIC_ROOT).
4. Memeriksa keberadaan file dan kemampuan membaca file gambar (OpenCV / PIL).
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image
try:
    from tp_config import STORAGE_PUBLIC_ROOT, SUPPORTED_EXTENSIONS
except ImportError:
    from .tp_config import STORAGE_PUBLIC_ROOT, SUPPORTED_EXTENSIONS


def resolve_image_path(relative_path: str) -> Tuple[Optional[Path], Optional[str]]:
    """
    Menyelesaikan path relatif dari database ke absolute path dalam STORAGE_PUBLIC_ROOT.
    Mengembalikan (resolved_path, error_message).
    Jika lolos validasi keamanan path, mengembalikan (Path, None).
    """
    if not relative_path or not isinstance(relative_path, str):
        return None, "Path gambar kosong atau tidak valid"

    # Normalisasi separator
    clean_rel = relative_path.replace("\\", "/").strip("/")

    # Cegah traversal
    if ".." in clean_rel.split("/"):
        return None, f"Terdeteksi path traversal ilegal pada: {relative_path}"

    target_path = (STORAGE_PUBLIC_ROOT / clean_rel).resolve()
    storage_root_resolved = STORAGE_PUBLIC_ROOT.resolve()

    try:
        # Pastikan target_path berada di dalam storage_root_resolved
        target_path.relative_to(storage_root_resolved)
    except ValueError:
        return None, f"Path berada di luar storage root yang diizinkan: {target_path}"

    if not target_path.exists():
        return None, f"File gambar tidak ditemukan di disk: {target_path}"

    if not target_path.is_file():
        return None, f"Path bukan berupa file biasa: {target_path}"

    if target_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return None, f"Ekstensi file tidak didukung ({target_path.suffix}): {target_path.name}"

    return target_path, None


def load_image_bgr(image_path: Path) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """
    Membaca file gambar ke format numpy array BGR (standar OpenCV yang diharapkan YOLO).
    Mendukung fallback PIL untuk format yang tidak terbaca langsung oleh cv2.imread.
    Mengembalikan (image_bgr, error_message).
    """
    p_str = str(image_path)
    try:
        img_bgr = cv2.imread(p_str)
        if img_bgr is not None and img_bgr.size > 0:
            return img_bgr, None
    except Exception as e:
        pass

    # Fallback via PIL
    try:
        pil_img = Image.open(p_str)
        pil_img.load()
        rgb = np.array(pil_img.convert("RGB"))
        img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if img_bgr is not None and img_bgr.size > 0:
            return img_bgr, None
    except Exception as e:
        return None, f"Gagal membaca gambar via OpenCV dan PIL: {e}"

    return None, f"Format gambar rusak atau kosong (cv2.imread return None): {image_path.name}"
