# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 01: EKSTRAKSI WAJAH (YOLO FACE DETECTION)
 Shell 01 di Jupyter Notebook
 Model: YOLOv8 Face (weights: storage/app/ai/weights/yolov8n-face.pt)
 
 Fungsi:
 1. Membaca metadata resmi dari database MySQL (actors, actor_images).
 2. Memuat gambar asli dari storage/app/public secara aman (anti path-traversal).
 3. Memproses gambar satu per satu (hemat RAM/VRAM).
 4. Mendeteksi bounding box wajah menggunakan YOLOv8.
 5. Menyimpan potongan wajah asli (face crop) ke artifacts/01_ekstraksi_wajah/crops/<actor_id>/<image_id>.png.
 6. Menangani kasus zero-face, multi-face (disimpan ke folder rejected untuk audit), dan error baca.
 7. Menyimpan manifest bertahap (incremental checkpointing) agar dapat di-resume jika terhenti.
========================================================================================
"""

import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Tambahkan direktori root, training_python, & python ke sys.path jika belum ada (agar kompatibel saat di-copy ke Jupyter)
_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
for _p in [_ROOT, _ROOT / "training_python", _ROOT / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    import tp_config as cfg
    from tp_database import fetch_actor_image_records
    from tp_dataset_loader import resolve_image_path, load_image_bgr
    from tp_manifest_utils import load_manifest, save_manifest_atomic
except ImportError:
    from training_python import tp_config as cfg
    from training_python.tp_database import fetch_actor_image_records
    from training_python.tp_dataset_loader import resolve_image_path, load_image_bgr
    from training_python.tp_manifest_utils import load_manifest, save_manifest_atomic

# Load YOLO model
from ultralytics import YOLO


def init_yolo():
    """Inisialisasi model YOLOv8 Face dari bobot resmi yang ada di storage/app/ai/weights/."""
    cfg.validate_paths(require_yolo=True)
    print(f"[*] Memuat model YOLO Face dari: {cfg.YOLO_WEIGHTS}")
    model = YOLO(str(cfg.YOLO_WEIGHTS))
    return model


def run_stage_01(force_reprocess: bool = False, limit: int = None):
    """
    Eksekusi Stage 01: Ekstraksi Wajah dari gambar database Laravel.
    
    :param force_reprocess: Jika True, proses ulang gambar yang sudah ada di manifest.
    :param limit: Batasi jumlah gambar yang diproses (None = proses semua).
    """
    cfg.ensure_artifact_dirs()
    model = init_yolo()

    print("\n[Stage 01] Mengambil daftar gambar aktor resmi (MySQL Read-Only)...")
    try:
        records = fetch_actor_image_records()
    except Exception as db_err:
        raise RuntimeError(
            f"Koneksi MySQL gagal: {db_err}\n"
            "Pastikan MySQL di Laragon aktif dan database 'indolens' dapat diakses.\n"
            "Pipeline TIDAK AKAN beralih ke sumber alternatif (silent fallback dilarang)."
        ) from db_err

    if not records:
        raise RuntimeError(
            "Koneksi MySQL berhasil, namun tidak ditemukan record gambar aktor di database (`actor_images`).\n"
            "Pastikan tabel `actors` dan `actor_images` telah memiliki data sebelum menjalankan pipeline.\n"
            "Pipeline berhenti tanpa fallback alternatif."
        )

    print(f"[*] Berhasil memuat {len(records)} record gambar aktor resmi dari MySQL.")

    if limit is not None and limit > 0:
        records = records[:limit]
        print(f"[*] Limit aktif: hanya memproses {len(records)} record pertama.")

    manifest = load_manifest(cfg.STAGE01_MANIFEST)
    items = manifest.get("items", {})

    stats = {
        "total_queued": len(records),
        "skipped_existing": 0,
        "success": 0,
        "zero_face": 0,
        "multi_face": 0,
        "unreadable": 0,
        "error": 0,
    }

    start_time = time.time()
    print("\n" + "=" * 75)
    print("  MEMULAI DETEKSI & CROP WAJAH SATU PER SATU (YOLOv8-FACE)")
    print("=" * 75)

    for idx, rec in enumerate(records, start=1):
        image_id_str = str(rec["image_id"])
        actor_id_str = str(rec["actor_id"])
        full_name = rec["full_name"]
        rel_path = rec["relative_image_path"]

        # Cek apakah sudah pernah diproses dan file crop ada
        if not force_reprocess and image_id_str in items:
            prev_status = items[image_id_str].get("status")
            crop_path_str = items[image_id_str].get("crop_path")
            if prev_status == "success" and crop_path_str and Path(crop_path_str).exists():
                stats["skipped_existing"] += 1
                continue

        print(f"\n[{idx}/{len(records)}] Gambar ID #{image_id_str} | Aktor: {full_name} (#{actor_id_str})")
        print(f"    Path: {rel_path}")

        # 1. Resolusi path fisik via Laravel storage (anti path-traversal)
        abs_img_path, path_err = resolve_image_path(rel_path)

        if path_err or abs_img_path is None:
            print(f"    [!] Error Path: {path_err}")
            items[image_id_str] = {
                "image_id": rec["image_id"],
                "actor_id": rec["actor_id"],
                "full_name": full_name,
                "relative_path": rel_path,
                "status": "unreadable",
                "error": path_err,
                "processed_at": time.time(),
            }
            stats["unreadable"] += 1
            save_manifest_atomic(cfg.STAGE01_MANIFEST, {"items": items, "updated_at": time.time()})
            continue

        # 2. Baca gambar ke format BGR
        img_bgr, read_err = load_image_bgr(abs_img_path)
        if read_err or img_bgr is None:
            print(f"    [!] Error Baca: {read_err}")
            items[image_id_str] = {
                "image_id": rec["image_id"],
                "actor_id": rec["actor_id"],
                "full_name": full_name,
                "relative_path": rel_path,
                "absolute_path": str(abs_img_path),
                "status": "unreadable",
                "error": read_err,
                "processed_at": time.time(),
            }
            stats["unreadable"] += 1
            save_manifest_atomic(cfg.STAGE01_MANIFEST, {"items": items, "updated_at": time.time()})
            continue

        orig_h, orig_w = img_bgr.shape[:2]

        # 3. Jalankan deteksi wajah YOLO
        try:
            # conf=0.45 standar yang dipakai yolo_service IndoLens
            results = model.predict(img_bgr, conf=0.45, verbose=False)
            boxes = results[0].boxes
        except Exception as e:
            print(f"    [!] Error YOLO Inference: {e}")
            items[image_id_str] = {
                "image_id": rec["image_id"],
                "actor_id": rec["actor_id"],
                "full_name": full_name,
                "relative_path": rel_path,
                "absolute_path": str(abs_img_path),
                "status": "error",
                "error": str(e),
                "processed_at": time.time(),
            }
            stats["error"] += 1
            save_manifest_atomic(cfg.STAGE01_MANIFEST, {"items": items, "updated_at": time.time()})
            continue

        num_faces = len(boxes) if boxes is not None else 0

        # Kasus A: Nol wajah terdeteksi
        if num_faces == 0:
            print(f"    [!] Nol wajah terdeteksi pada gambar ini (YOLO conf >= 0.45).")
            items[image_id_str] = {
                "image_id": rec["image_id"],
                "actor_id": rec["actor_id"],
                "full_name": full_name,
                "relative_path": rel_path,
                "absolute_path": str(abs_img_path),
                "dimensions": [orig_w, orig_h],
                "status": "zero_face",
                "faces_detected": 0,
                "processed_at": time.time(),
            }
            stats["zero_face"] += 1

        # Kasus B: Lebih dari 1 wajah terdeteksi (Multi-Face Ambiguity)
        elif num_faces > 1:
            print(f"    [!] Multi-face terdeteksi: ditemukan {num_faces} wajah. Wajah ambigu ditolak agar tidak salah identitas.")
            rejected_dir = cfg.STAGE01_REJECTED_DIR / actor_id_str
            rejected_dir.mkdir(parents=True, exist_ok=True)

            detected_boxes = []
            for face_idx, box in enumerate(boxes):
                xyxy = [int(round(v)) for v in box.xyxy[0].cpu().numpy().tolist()]
                conf = float(box.conf[0].cpu().numpy().item())
                detected_boxes.append({"bbox": xyxy, "conf": round(conf, 4)})

                # Simpan preview potongan wajah yang ditolak untuk audit
                x1, y1, x2, y2 = max(0, xyxy[0]), max(0, xyxy[1]), min(orig_w, xyxy[2]), min(orig_h, xyxy[3])
                crop_rej = img_bgr[y1:y2, x1:x2]
                if crop_rej.size > 0:
                    rej_file = rejected_dir / f"{image_id_str}_face_{face_idx+1}.png"
                    cv2.imwrite(str(rej_file), crop_rej)

            items[image_id_str] = {
                "image_id": rec["image_id"],
                "actor_id": rec["actor_id"],
                "full_name": full_name,
                "relative_path": rel_path,
                "absolute_path": str(abs_img_path),
                "dimensions": [orig_w, orig_h],
                "status": "multi_face",
                "faces_detected": num_faces,
                "detected_boxes": detected_boxes,
                "rejected_audit_dir": str(rejected_dir),
                "processed_at": time.time(),
            }
            stats["multi_face"] += 1

        # Kasus C: Tepat 1 wajah terdeteksi (Sukses)
        else:
            box = boxes[0]
            xyxy = [int(round(v)) for v in box.xyxy[0].cpu().numpy().tolist()]
            conf = float(box.conf[0].cpu().numpy().item())

            x1, y1, x2, y2 = max(0, xyxy[0]), max(0, xyxy[1]), min(orig_w, xyxy[2]), min(orig_h, xyxy[3])
            crop = img_bgr[y1:y2, x1:x2]

            if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                print(f"    [!] Crop wajah terlalu kecil/invalid ({crop.shape}).")
                items[image_id_str] = {
                    "image_id": rec["image_id"],
                    "actor_id": rec["actor_id"],
                    "full_name": full_name,
                    "relative_path": rel_path,
                    "status": "error",
                    "error": f"Crop invalid atau ukuran terlalu kecil: {crop.shape}",
                    "processed_at": time.time(),
                }
                stats["error"] += 1
            else:
                actor_crop_dir = cfg.STAGE01_CROPS_DIR / actor_id_str
                actor_crop_dir.mkdir(parents=True, exist_ok=True)
                crop_path = actor_crop_dir / f"{image_id_str}.png"
                cv2.imwrite(str(crop_path), crop)

                crop_h, crop_w = crop.shape[:2]
                print(f"    [OK] Sukses Crop: {crop_w}x{crop_h} px (conf: {conf:.4f}) -> {crop_path.name}")

                items[image_id_str] = {
                    "image_id": rec["image_id"],
                    "actor_id": rec["actor_id"],
                    "full_name": full_name,
                    "relative_path": rel_path,
                    "absolute_path": str(abs_img_path),
                    "dimensions": [orig_w, orig_h],
                    "status": "success",
                    "faces_detected": 1,
                    "bbox": [x1, y1, x2, y2],
                    "confidence": round(conf, 4),
                    "crop_dimensions": [crop_w, crop_h],
                    "crop_path": str(crop_path),
                    "processed_at": time.time(),
                }
                stats["success"] += 1

        # Simpan checkpoint manifest setiap gambar untuk keamanan interupsi
        save_manifest_atomic(cfg.STAGE01_MANIFEST, {"items": items, "updated_at": time.time()})

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 75)
    print("  STAGE 01 SELESAI")
    print(f"  Durasi Total      : {elapsed} detik")
    print(f"  Total Diproses    : {len(records)}")
    print(f"  Dilewati (Existing): {stats['skipped_existing']}")
    print(f"  Berhasil Di-crop  : {stats['success']}")
    print(f"  Zero-face         : {stats['zero_face']}")
    print(f"  Multi-face        : {stats['multi_face']}")
    print(f"  Tidak Terbaca     : {stats['unreadable']}")
    print(f"  Error             : {stats['error']}")
    print(f"  Manifest Tersimpan: {cfg.STAGE01_MANIFEST}")
    print("=" * 75)

    return stats


if __name__ == "__main__":
    run_stage_01()
