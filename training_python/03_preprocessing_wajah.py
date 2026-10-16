# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 03: PREPROCESSING WAJAH
 Shell 03 di Jupyter Notebook
 
 Fungsi:
 1. Membaca potongan wajah (face crop) valid dari Stage 01.
 2. Melakukan konversi format warna BGR ke RGB (standar input neural network FaceNet).
 3. Melakukan resizing ke resolusi standar 160x160 piksel (sesuai arsitektur Inception-ResNet-v1).
 4. Menerapkan normalisasi piksel VGGFace2 float32: (x - mean) / max(std, 1/sqrt(N)).
 5. Memvalidasi bentuk tensor (160, 160, 3) dan ketiadaan nilai NaN/Inf.
 6. Menyimpan tensor siap-inferensi ke artifacts/03_preprocessing_wajah/tensors/<actor_id>/<image_id>.npy.
 7. Menyimpan visual preview 160x160 ke artifacts/03_preprocessing_wajah/previews/<actor_id>/<image_id>.png
    untuk inspeksi visual di sel Jupyter.
 8. Menyimpan manifest bertahap (incremental checkpointing).
========================================================================================
"""

import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
for _p in [_ROOT, _ROOT / "training_python", _ROOT / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    import tp_config as cfg
    from tp_manifest_utils import load_manifest, save_manifest_atomic
except ImportError:
    from training_python import tp_config as cfg
    from training_python.tp_manifest_utils import load_manifest, save_manifest_atomic


def preprocess_single_crop(crop_bgr: np.ndarray):
    """
    Memproses satu gambar crop wajah BGR menjadi tensor siap-FaceNet.
    Mengikuti rumus standar di python/utils/image_preprocessor.py:
    1. BGR -> RGB
    2. Resize ke 160x160
    3. Normalisasi (arr - mean) / std_adj
    """
    if crop_bgr is None or crop_bgr.size == 0:
        raise ValueError("Crop kosong atau None")

    # 1. Konversi BGR -> RGB
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

    # 2. Resize ke 160x160 (INTER_AREA untuk downsampling tajam)
    resized_rgb = cv2.resize(crop_rgb, cfg.FACENET_INPUT_SIZE, interpolation=cv2.INTER_AREA)

    # 3. Normalisasi standar FaceNet VGGFace2
    arr = resized_rgb.astype(np.float32)
    mean = arr.mean()
    std = arr.std()
    std_adj = np.maximum(std, 1.0 / np.sqrt(max(arr.size, 1)))
    normalized = (arr - mean) / std_adj

    return resized_rgb, normalized.astype(np.float32)


def run_stage_03(force_reprocess: bool = False):
    """Eksekusi Stage 03: Preprocessing Wajah."""
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 03: PREPROCESSING WAJAH UNTUK FACENET (160x160 RGB NORMALIZED)")
    print("=" * 75)

    if not cfg.STAGE01_MANIFEST.exists():
        raise FileNotFoundError(
            f"Manifest Stage 01 tidak ditemukan di: {cfg.STAGE01_MANIFEST}\n"
            "Jalankan Stage 01 terlebih dahulu."
        )

    manifest_01 = load_manifest(cfg.STAGE01_MANIFEST)
    items_01 = manifest_01.get("items", {})

    manifest_03 = load_manifest(cfg.STAGE03_MANIFEST)
    items_03 = manifest_03.get("items", {})

    # Ambil hanya item yang berhasil di-crop di Stage 01
    valid_items = [
        (img_id, data)
        for img_id, data in items_01.items()
        if data.get("status") == "success" and data.get("crop_path")
    ]

    print(f"[*] Ditemukan {len(valid_items)} crop wajah valid dari Stage 01.")

    success_count = 0
    skipped_count = 0
    error_count = 0
    start_time = time.time()

    for idx, (img_id_str, data) in enumerate(valid_items, start=1):
        actor_id_str = str(data["actor_id"])
        full_name = data.get("full_name", f"Aktor #{actor_id_str}")
        crop_path = Path(data["crop_path"])

        # Cek apakah sudah pernah dipreprocess
        if not force_reprocess and img_id_str in items_03:
            prev_tensor = items_03[img_id_str].get("tensor_path")
            if prev_tensor and Path(prev_tensor).exists():
                skipped_count += 1
                continue

        print(f"[{idx}/{len(valid_items)}] Preprocessing Image #{img_id_str} | {full_name}")

        if not crop_path.exists():
            print(f"    [!] File crop tidak ditemukan di: {crop_path}")
            items_03[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "error",
                "error": f"Crop file missing: {crop_path}",
                "processed_at": time.time(),
            }
            error_count += 1
            save_manifest_atomic(cfg.STAGE03_MANIFEST, {"items": items_03, "updated_at": time.time()})
            continue

        try:
            crop_bgr = cv2.imread(str(crop_path))
            preview_rgb, tensor_norm = preprocess_single_crop(crop_bgr)

            # Validasi tensor shape & kelayakan numerik
            if tensor_norm.shape != (160, 160, 3):
                raise ValueError(f"Shape tensor tidak sesuai: {tensor_norm.shape}, diharapkan (160, 160, 3)")
            if np.isnan(tensor_norm).any() or np.isinf(tensor_norm).any():
                raise ValueError("Tensor mengandung nilai NaN atau Inf")

            # Simpan tensor (.npy)
            actor_tensor_dir = cfg.STAGE03_TENSORS_DIR / actor_id_str
            actor_tensor_dir.mkdir(parents=True, exist_ok=True)
            tensor_file = actor_tensor_dir / f"{img_id_str}.npy"
            np.save(str(tensor_file), tensor_norm)

            # Simpan preview gambar (.png RGB) untuk visual audit di Jupyter
            actor_preview_dir = cfg.STAGE03_PREVIEWS_DIR / actor_id_str
            actor_preview_dir.mkdir(parents=True, exist_ok=True)
            preview_file = actor_preview_dir / f"{img_id_str}.png"
            preview_bgr = cv2.cvtColor(preview_rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(preview_file), preview_bgr)

            items_03[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "success",
                "tensor_shape": list(tensor_norm.shape),
                "tensor_path": str(tensor_file),
                "preview_path": str(preview_file),
                "norm_mean": round(float(tensor_norm.mean()), 6),
                "norm_std": round(float(tensor_norm.std()), 6),
                "processed_at": time.time(),
            }
            success_count += 1
            print(f"    [OK] Sukses: Tensor (160,160,3) -> {tensor_file.name}")

        except Exception as e:
            print(f"    [!] Error preprocessing: {e}")
            items_03[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "error",
                "error": str(e),
                "processed_at": time.time(),
            }
            error_count += 1

        # Simpan incremental manifest
        save_manifest_atomic(cfg.STAGE03_MANIFEST, {"items": items_03, "updated_at": time.time()})

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 75)
    print("  STAGE 03 SELESAI")
    print(f"  Durasi Total        : {elapsed} detik")
    print(f"  Berhasil Diproses   : {success_count}")
    print(f"  Dilewati (Existing) : {skipped_count}")
    print(f"  Error               : {error_count}")
    print(f"  Folder Tensor       : {cfg.STAGE03_TENSORS_DIR}")
    print(f"  Folder Preview      : {cfg.STAGE03_PREVIEWS_DIR}")
    print(f"  Manifest Tersimpan  : {cfg.STAGE03_MANIFEST}")
    print("=" * 75)

    return {"success": success_count, "skipped": skipped_count, "error": error_count}


if __name__ == "__main__":
    run_stage_03()
