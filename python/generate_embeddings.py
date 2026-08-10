"""
IndoLens – Generate Embeddings dari Dataset
============================================

Script ini menghasilkan file .npy embedding 128-D untuk setiap gambar dataset
menggunakan pipeline yang IDENTIK dengan runtime desktop:

    Image File
    → cv2.imread (BGR numpy)
    → YOLO Face Detection (crop wajah)
    → FaceNet generate_embedding (dari crop BGR)
    → Save .npy ke embeddings/<actor_name>/

PENTING: Pipeline harus sama persis dengan desktop/main.py (InferenceThread).
Embedding yang di-generate dari gambar penuh (tanpa YOLO crop) akan menghasilkan
embedding yang berbeda dari embedding runtime, sehingga Euclidean Distance menjadi
sangat besar dan recognition selalu gagal.

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python generate_embeddings.py
"""

import sys
import os
import time
from pathlib import Path

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["YOLO_CONFIDENCE"] = "0.45"
os.environ["MIN_FACE_CONFIDENCE"] = "0.45"

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import (
    DATASET_PATH, EMBEDDING_PATH, SUPPORTED_EXTENSION,
    FACENET_EMBEDDING_DIM
)


def main():
    print("=" * 65)
    print("  IndoLens – Generate Embeddings (Pipeline-Consistent)")
    print(f"  Dataset   : {DATASET_PATH}")
    print(f"  Output    : {EMBEDDING_PATH}")
    print("=" * 65)
    print()

    # ------------------------------------------------------------------
    # 1. Import modul AI
    # ------------------------------------------------------------------
    print("[1/4] Memuat modul AI...")
    try:
        import cv2
        import numpy as np
        from yolo.detector import load_model as yolo_load_model, predict_frame
        from facenet.embedding_generator import load_facenet_model, generate_embedding
        from facenet.embedding_generator import save_embedding
    except ImportError as e:
        print(f"[ERROR] Gagal mengimpor modul: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 2. Load model YOLO & FaceNet (sama seperti desktop startup)
    # ------------------------------------------------------------------
    print("[2/4] Memuat YOLO model...")
    try:
        yolo_load_model()
        print("[OK] YOLO model dimuat.")
    except Exception as e:
        print(f"[ERROR] Gagal memuat YOLO: {e}")
        sys.exit(1)

    print("[3/4] Memuat FaceNet model...")
    try:
        load_facenet_model()
        print("[OK] FaceNet model dimuat.")
    except Exception as e:
        print(f"[ERROR] Gagal memuat FaceNet: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # 3. Scan dataset
    # ------------------------------------------------------------------
    print("[4/4] Scan dataset aktor...")
    if not DATASET_PATH.exists():
        print(f"[ERROR] Dataset path tidak ditemukan: {DATASET_PATH}")
        sys.exit(1)

    actor_dirs = [
        d for d in sorted(DATASET_PATH.iterdir())
        if d.is_dir() and not d.name.startswith(".")
    ]

    if not actor_dirs:
        print("[ERROR] Tidak ada folder aktor dalam dataset.")
        sys.exit(1)

    print(f"[OK] Ditemukan {len(actor_dirs)} aktor.\n")

    # ------------------------------------------------------------------
    # 4. Generate embedding per aktor
    # ------------------------------------------------------------------
    total_saved = 0
    total_skipped = 0
    total_failed = 0

    for actor_dir in actor_dirs:
        actor_name = actor_dir.name
        print(f"{'─'*60}")
        print(f"Aktor: {actor_name}")

        # Kumpulkan semua file gambar
        image_files = []
        for ext in SUPPORTED_EXTENSION:
            image_files.extend(sorted(actor_dir.glob(f"*.{ext}")))
            image_files.extend(sorted(actor_dir.glob(f"*.{ext.upper()}")))

        # Hilangkan duplikat (jika glob case-insensitive overlap)
        seen = set()
        unique_images = []
        for p in image_files:
            if p.name.lower() not in seen:
                seen.add(p.name.lower())
                unique_images.append(p)
        image_files = unique_images

        if not image_files:
            print(f"  [WARNING] Tidak ada gambar ditemukan di {actor_dir}")
            continue

        print(f"  Gambar ditemukan : {len(image_files)}")

        # Buat folder output embedding
        out_dir = EMBEDDING_PATH / actor_name
        out_dir.mkdir(parents=True, exist_ok=True)

        actor_saved = 0
        actor_skipped = 0
        actor_failed = 0

        for img_path in image_files:
            out_npy = out_dir / (img_path.stem + ".npy")

            # ----------------------------------------------------------
            # Step A: Baca gambar sebagai BGR numpy (sama seperti runtime)
            # ----------------------------------------------------------
            frame = cv2.imread(str(img_path))
            if frame is None:
                print(f"  [SKIP] Tidak dapat membaca: {img_path.name}")
                actor_skipped += 1
                continue

            # ----------------------------------------------------------
            # Step B: Deteksi wajah dengan YOLO (sama seperti runtime)
            # ----------------------------------------------------------
            detections = predict_frame(frame)

            crop_img = None
            if detections:
                # Gunakan deteksi dengan confidence tertinggi
                best_det = max(detections, key=lambda d: d.get("confidence", 0))
                crop_candidate = best_det.get("crop")
                if crop_candidate is not None and crop_candidate.size > 0:
                    crop_img = crop_candidate

            if crop_img is None:
                # Fallback: jika YOLO tidak mendeteksi wajah, gunakan gambar penuh
                # (Ini lebih baik daripada skip, tapi tandai sebagai fallback)
                print(f"  [FALLBACK] YOLO tidak deteksi wajah di {img_path.name} — gunakan gambar penuh")
                crop_img = frame

            # ----------------------------------------------------------
            # Step C: Generate embedding dari crop (BGR numpy)
            # Persis sama dengan: generate_embedding(crop_img) di desktop/main.py
            # ----------------------------------------------------------
            try:
                emb = generate_embedding(crop_img)
            except Exception as e:
                print(f"  [ERROR] Gagal generate embedding {img_path.name}: {e}")
                actor_failed += 1
                continue

            if emb is None or len(emb) != FACENET_EMBEDDING_DIM:
                print(f"  [ERROR] Embedding tidak valid untuk {img_path.name} (dim={len(emb) if emb is not None else 'None'})")
                actor_failed += 1
                continue

            # ----------------------------------------------------------
            # Step D: Simpan embedding ke .npy
            # ----------------------------------------------------------
            try:
                save_embedding(emb, out_npy)
                print(f"  [SAVED] {img_path.name:<35} → {out_npy.name}  (dim={len(emb)})")
                actor_saved += 1
            except Exception as e:
                print(f"  [ERROR] Gagal menyimpan {out_npy.name}: {e}")
                actor_failed += 1

        print(f"  Ringkasan  : {actor_saved} tersimpan, {actor_skipped} dilewati, {actor_failed} gagal")
        total_saved += actor_saved
        total_skipped += actor_skipped
        total_failed += actor_failed

    # ------------------------------------------------------------------
    # 5. Ringkasan akhir
    # ------------------------------------------------------------------
    print()
    print("=" * 65)
    print("  SELESAI")
    print(f"  Total tersimpan : {total_saved}")
    print(f"  Total dilewati  : {total_skipped}")
    print(f"  Total gagal     : {total_failed}")
    print()
    print("  Selanjutnya: jalankan python audit_recognition.py")
    print("  untuk memverifikasi bahwa self-test recognition berhasil.")
    print("=" * 65)


if __name__ == "__main__":
    main()
