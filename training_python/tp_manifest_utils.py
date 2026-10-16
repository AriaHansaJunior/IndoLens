# hanya untuk keperluan training python local, tidak dirun di web
"""
tp_manifest_utils.py — Helper utilitas untuk membaca dan menulis manifest secara atomik.

Menghindari korupsi data jika eksekusi di notebook diinterupsi oleh user (misalnya Stop Kernel).
Menyediakan penyimpanan bertahap (incremental checkpoint) per-gambar.
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Any, Dict


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Membaca file manifest JSON secara aman. Mengembalikan dict kosong jika belum ada."""
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Gagal membaca manifest {manifest_path.name}: {e}. Memulai dari kosong.")
        return {}


def save_manifest_atomic(manifest_path: Path, data: Dict[str, Any]) -> None:
    """Menyimpan manifest secara atomik: tulis ke file temporary di direktori yang sama, lalu rename."""
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_file = manifest_path.parent / f".tmp_{manifest_path.name}_{os.getpid()}"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(manifest_path)
    except Exception:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)
        raise
