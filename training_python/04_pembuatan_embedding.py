# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 04: PEMBUATAN EMBEDDING 128-D
 Shell 04 di Jupyter Notebook
 Model: FaceNet Inception-ResNet-v1 (Pretrained: VGGFace2)
 
 Fungsi:
 1. Mendeteksi akselerasi GPU NVIDIA (CUDA) / RTX 4070 dan melaporkan device aktif secara jujur.
 2. Memuat bobot resmi FaceNet InceptionResnetV1(pretrained='vggface2') dalam mode evaluasi (eval).
 3. Membaca tensor ternormalisasi dari Stage 03.
 4. Melakukan inferensi ekstraksi fitur neural network per-gambar (hemat VRAM).
 5. Memotong ke 128 dimensi dan melakukan normalisasi L2-Norm (unit length = 1.0)
    sesuai metodologi dan kompatibilitas 100% dengan yolo_service IndoLens runtime.
 6. Menyimpan vektor embedding (.npy float32) ke:
    artifacts/04_pembuatan_embedding/vectors/<actor_id>/<image_id>.npy
 7. Menyimpan checkpoint manifest bertahap (dapat di-resume kapan saja jika kernel stop).
========================================================================================
"""

import os
import sys
import time
from pathlib import Path
import numpy as np
import torch

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

from facenet_pytorch import InceptionResnetV1


def get_inference_device():
    """
    Deteksi perangkat keras komputasi PyTorch (CUDA GPU vs CPU).
    Mengembalikan (torch.device, device_name_string).
    """
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        dev_name = f"CUDA GPU: {torch.cuda.get_device_name(0)} (VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.1f} GB)"
    else:
        dev = torch.device("cpu")
        dev_name = "CPU (CUDA tidak terdeteksi pada kernel ini)"
    return dev, dev_name


def load_model(device: torch.device):
    """Memuat model FaceNet Inception-ResNet-v1 pretrained vggface2 ke device yang dipilih."""
    print(f"[*] Menginisialisasi FaceNet InceptionResnetV1 (pretrained='vggface2')...")
    model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
    print(f"[OK] FaceNet siap di: {device}")
    return model


def compute_dual_embeddings(model, tensor_hwc_normalized: np.ndarray, device: torch.device):
    """
    Menghitung vektor embedding 512-D (Native Inception-ResNet-v1 VGGFace2)
    sekaligus 128-D (Proyeksi 128 Dimensi) berstandar L2-Norm.
    
    Kedua dimensi disimpan agar peneliti dapat melakukan audit komparasi ilmiah:
    - 512-D: Representasi penuh, akurasi & kapasitas diskriminatif tertinggi.
    - 128-D: Versi terkompresi untuk efisiensi komputasi & memori.
    """
    tensor_chw = torch.from_numpy(tensor_hwc_normalized).permute(2, 0, 1).float().unsqueeze(0).to(device)

    with torch.no_grad():
        raw_output = model(tensor_chw).detach().cpu().numpy().flatten()

    # 1. 512-D Full Native Vector
    norm_512 = np.linalg.norm(raw_output)
    emb_512 = (raw_output / norm_512 if norm_512 > 0 else raw_output).astype(np.float32)

    # 2. 128-D Projected Vector
    raw_128 = raw_output[:128] if len(raw_output) >= 128 else np.pad(raw_output, (0, 128 - len(raw_output)))
    norm_128 = np.linalg.norm(raw_128)
    emb_128 = (raw_128 / norm_128 if norm_128 > 0 else raw_128).astype(np.float32)

    return emb_512, emb_128


def run_stage_04(force_reprocess: bool = False):
    """Eksekusi Stage 04: Pembuatan Embedding FaceNet 128-D."""
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 04: PEMBUATAN EMBEDDING 128-D (FACENET INCEPTION-RESNET-V1)")
    print("=" * 75)

    device, device_name = get_inference_device()
    print(f"[*] Perangkat Inferensi: {device_name}")

    model = load_model(device)

    if not cfg.STAGE03_MANIFEST.exists():
        raise FileNotFoundError(
            f"Manifest Stage 03 tidak ditemukan di: {cfg.STAGE03_MANIFEST}\n"
            "Jalankan Stage 03 terlebih dahulu."
        )

    manifest_03 = load_manifest(cfg.STAGE03_MANIFEST)
    items_03 = manifest_03.get("items", {})

    manifest_04 = load_manifest(cfg.STAGE04_MANIFEST)
    items_04 = manifest_04.get("items", {})

    valid_tensors = [
        (img_id, data)
        for img_id, data in items_03.items()
        if data.get("status") == "success" and data.get("tensor_path")
    ]

    print(f"[*] Ditemukan {len(valid_tensors)} tensor wajah valid dari Stage 03.")

    success_count = 0
    skipped_count = 0
    error_count = 0
    start_time = time.time()

    for idx, (img_id_str, data) in enumerate(valid_tensors, start=1):
        actor_id_str = str(data["actor_id"])
        full_name = data.get("full_name", f"Aktor #{actor_id_str}")
        tensor_path = Path(data["tensor_path"])

        # Cek apakah sudah pernah di-generate
        if not force_reprocess and img_id_str in items_04:
            prev_vector = items_04[img_id_str].get("vector_path")
            if prev_vector and Path(prev_vector).exists():
                skipped_count += 1
                continue

        print(f"[{idx}/{len(valid_tensors)}] Extracting Embedding Image #{img_id_str} | {full_name}")

        if not tensor_path.exists():
            print(f"    [!] File tensor tidak ditemukan di: {tensor_path}")
            items_04[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "error",
                "error": f"Tensor missing: {tensor_path}",
                "processed_at": time.time(),
            }
            error_count += 1
            save_manifest_atomic(cfg.STAGE04_MANIFEST, {"items": items_04, "device": device_name, "updated_at": time.time()})
            continue

        try:
            tensor_norm = np.load(str(tensor_path))
            t_infer_start = time.perf_counter()
            emb_512, emb_128 = compute_dual_embeddings(model, tensor_norm, device)
            infer_ms = round((time.perf_counter() - t_infer_start) * 1000, 2)

            l2_512 = float(np.linalg.norm(emb_512))
            l2_128 = float(np.linalg.norm(emb_128))

            if abs(l2_512 - 1.0) > cfg.L2_NORM_TOLERANCE or abs(l2_128 - 1.0) > cfg.L2_NORM_TOLERANCE:
                raise ValueError(f"L2-norm tidak valid: 512D={l2_512:.6f}, 128D={l2_128:.6f}")

            # 1. Simpan Vektor 512-D
            dir_512 = cfg.STAGE04_VECTORS_512_DIR / actor_id_str
            dir_512.mkdir(parents=True, exist_ok=True)
            vec_512_file = dir_512 / f"{img_id_str}.npy"
            np.save(str(vec_512_file), emb_512)

            # 2. Simpan Vektor 128-D
            dir_128 = cfg.STAGE04_VECTORS_128_DIR / actor_id_str
            dir_128.mkdir(parents=True, exist_ok=True)
            vec_128_file = dir_128 / f"{img_id_str}.npy"
            np.save(str(vec_128_file), emb_128)

            # 3. Simpan Primary Vector (sesuai cfg.PRIMARY_EMBEDDING_DIM)
            primary_emb = emb_512 if cfg.PRIMARY_EMBEDDING_DIM == 512 else emb_128
            actor_vec_dir = cfg.STAGE04_VECTORS_DIR / actor_id_str
            actor_vec_dir.mkdir(parents=True, exist_ok=True)
            primary_file = actor_vec_dir / f"{img_id_str}.npy"
            np.save(str(primary_file), primary_emb)

            items_04[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "success",
                "primary_dimension": cfg.PRIMARY_EMBEDDING_DIM,
                "vector_path": str(primary_file),
                "vector_512_path": str(vec_512_file),
                "vector_128_path": str(vec_128_file),
                "l2_norm_512": round(l2_512, 6),
                "l2_norm_128": round(l2_128, 6),
                "inference_ms": infer_ms,
                "processed_at": time.time(),
            }
            success_count += 1
            print(f"    [OK] Sukses Ekstraksi (512-D & 128-D, {infer_ms} ms) -> {primary_file.name}")

        except Exception as e:
            print(f"    [!] Error ekstraksi: {e}")
            items_04[img_id_str] = {
                "image_id": int(img_id_str),
                "actor_id": int(actor_id_str),
                "full_name": full_name,
                "status": "error",
                "error": str(e),
                "processed_at": time.time(),
            }
            error_count += 1

        # Checkpoint simpan berkala
        save_manifest_atomic(cfg.STAGE04_MANIFEST, {"items": items_04, "device": device_name, "updated_at": time.time()})

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 75)
    print("  STAGE 04 SELESAI")
    print(f"  Perangkat Digunakan : {device_name}")
    print(f"  Durasi Total        : {elapsed} detik")
    print(f"  Berhasil Dibuat     : {success_count} vektor 128-D")
    print(f"  Dilewati (Existing) : {skipped_count}")
    print(f"  Error               : {error_count}")
    print(f"  Folder Vektor       : {cfg.STAGE04_VECTORS_DIR}")
    print(f"  Manifest Tersimpan  : {cfg.STAGE04_MANIFEST}")
    print("=" * 75)

    return {"success": success_count, "skipped": skipped_count, "error": error_count, "device": device_name}


if __name__ == "__main__":
    run_stage_04()
