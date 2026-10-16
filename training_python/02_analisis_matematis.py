# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 02: ANALISIS MATEMATIS DATASET
 Shell 02 di Jupyter Notebook
 
 Fungsi:
 1. Menganalisis data empiris hasil ekstraksi wajah Stage 01.
 2. Distribusi dimensi gambar asli (lebar, tinggi, rasio aspek).
 3. Statistik dimensi face-crop (min, max, mean, median, standar deviasi).
 4. Statistik skor confidence deteksi YOLOv8-face.
 5. Evaluasi kualitas data: zero-face, multi-face, unreadable per aktor.
 6. Deteksi potensi gambar duplikat / hampir-duplikat menggunakan dHash (perceptual hashing 64-bit).
 7. Menyimpan laporan resmi ke analysis_report.json dan analysis_report.txt.
========================================================================================
"""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import cv2

_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
for _p in [_ROOT, _ROOT / "training_python", _ROOT / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    import tp_config as cfg
    from tp_manifest_utils import load_manifest
except ImportError:
    from training_python import tp_config as cfg
    from training_python.tp_manifest_utils import load_manifest


def calculate_dhash(image_path: Path, hash_size: int = 8) -> int:
    """
    Menghitung 64-bit difference hash (dHash) untuk mendeteksi kesamaan visual/duplikasi.
    Resize ke (hash_size + 1, hash_size) = (9, 8), ubah ke grayscale, bandingkan piksel adjacent.
    """
    try:
        img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return 0
        resized = cv2.resize(img, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        diff = resized[:, 1:] > resized[:, :-1]
        decimal_val = 0
        for bit in diff.flatten():
            decimal_val = (decimal_val << 1) | int(bit)
        return decimal_val
    except Exception:
        return 0


def hamming_distance(hash1: int, hash2: int) -> int:
    """Menghitung jarak Hamming antara dua hash 64-bit."""
    return bin(hash1 ^ hash2).count("1")


def run_stage_02():
    """Eksekusi Stage 02: Analisis Matematis Data Ekstraksi Wajah."""
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 02: ANALISIS MATEMATIS DATASET WAJAH INDOLENS")
    print("=" * 75)

    if not cfg.STAGE01_MANIFEST.exists():
        raise FileNotFoundError(
            f"Manifest Stage 01 tidak ditemukan di: {cfg.STAGE01_MANIFEST}\n"
            "Pastikan Stage 01 sudah dijalankan terlebih dahulu di Shell 01."
        )

    manifest_01 = load_manifest(cfg.STAGE01_MANIFEST)
    items = manifest_01.get("items", {})

    if not items:
        print("[!] Manifest Stage 01 kosong. Belum ada data untuk dianalisis.")
        return {}

    total_records = len(items)
    status_counts = {}
    actor_groups = {}
    orig_widths, orig_heights = [], []
    crop_widths, crop_heights, crop_aspects = [], [], []
    confidences = []
    hashes = {}  # image_id -> (dhash, actor_id, full_name, path)

    for img_id, data in items.items():
        status = data.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        actor_id = data.get("actor_id")
        full_name = data.get("full_name", f"Aktor #{actor_id}")
        if actor_id not in actor_groups:
            actor_groups[actor_id] = {
                "actor_id": actor_id,
                "full_name": full_name,
                "total": 0,
                "success": 0,
                "zero_face": 0,
                "multi_face": 0,
                "unreadable": 0,
                "error": 0,
            }
        actor_groups[actor_id]["total"] += 1
        actor_groups[actor_id][status] = actor_groups[actor_id].get(status, 0) + 1

        dims = data.get("dimensions")
        if dims and len(dims) == 2:
            orig_widths.append(dims[0])
            orig_heights.append(dims[1])

        if status == "success":
            c_dims = data.get("crop_dimensions")
            if c_dims and len(c_dims) == 2:
                cw, ch = c_dims[0], c_dims[1]
                crop_widths.append(cw)
                crop_heights.append(ch)
                if ch > 0:
                    crop_aspects.append(round(cw / ch, 4))

            conf = data.get("confidence")
            if conf is not None:
                confidences.append(float(conf))

            # Hitung dHash untuk deteksi gambar duplikat
            crop_path_str = data.get("crop_path")
            if crop_path_str and Path(crop_path_str).exists():
                h_val = calculate_dhash(Path(crop_path_str))
                hashes[img_id] = (h_val, actor_id, full_name, crop_path_str)

    # 1. Analisis Duplikat (Hamming distance dHash)
    near_duplicates = []
    hash_keys = list(hashes.keys())
    for i in range(len(hash_keys)):
        id_a = hash_keys[i]
        h_a, act_a, name_a, path_a = hashes[id_a]
        for j in range(i + 1, len(hash_keys)):
            id_b = hash_keys[j]
            h_b, act_b, name_b, path_b = hashes[id_b]
            dist = hamming_distance(h_a, h_b)
            if dist <= cfg.NEAR_DUPLICATE_HAMMING:
                near_duplicates.append({
                    "image_a": int(id_a),
                    "image_b": int(id_b),
                    "actor_a": name_a,
                    "actor_b": name_b,
                    "same_actor": (act_a == act_b),
                    "hamming_distance": dist,
                })

    # 2. Perhitungan Statistik Deskriptif
    def calc_stats(arr):
        if not arr:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "median": 0, "std": 0}
        npa = np.array(arr)
        return {
            "count": int(len(npa)),
            "min": round(float(np.min(npa)), 4),
            "max": round(float(np.max(npa)), 4),
            "mean": round(float(np.mean(npa)), 4),
            "median": round(float(np.median(npa)), 4),
            "std": round(float(np.std(npa)), 4),
        }

    report = {
        "generated_at": time.time(),
        "total_source_records": total_records,
        "status_distribution": status_counts,
        "per_actor_breakdown": list(actor_groups.values()),
        "original_image_resolution": {
            "width": calc_stats(orig_widths),
            "height": calc_stats(orig_heights),
        },
        "face_crop_resolution": {
            "width": calc_stats(crop_widths),
            "height": calc_stats(crop_heights),
            "aspect_ratio": calc_stats(crop_aspects),
        },
        "yolo_detection_confidence": calc_stats(confidences),
        "near_duplicate_pairs": near_duplicates,
        "near_duplicate_count": len(near_duplicates),
    }

    # 3. Simpan laporan JSON
    with open(cfg.STAGE02_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # 4. Buat dan simpan ringkasan teks untuk skripsi
    txt_lines = [
        "=" * 75,
        "  LAPORAN ANALISIS MATEMATIS DATASET INDOLENS (SKRIPSI)",
        "=" * 75,
        f"Total Data Terdaftar di MySQL     : {total_records}",
        f"  - Berhasil Diekstrak (1 Wajah)  : {status_counts.get('success', 0)} ({status_counts.get('success', 0)/total_records*100:.1f}%)",
        f"  - Nol Wajah Terdeteksi          : {status_counts.get('zero_face', 0)}",
        f"  - Multi-Face (Wajah Ambigu)     : {status_counts.get('multi_face', 0)}",
        f"  - Gambar Rusak / Tidak Terbaca  : {status_counts.get('unreadable', 0)}",
        f"  - Error Teknis                  : {status_counts.get('error', 0)}",
        "",
        "-" * 75,
        "1. STATISTIK RESOLUSI FACE-CROP WAJAH (Piksel):",
        f"  - Lebar  : Min={report['face_crop_resolution']['width']['min']} | Max={report['face_crop_resolution']['width']['max']} | Mean={report['face_crop_resolution']['width']['mean']} | Std={report['face_crop_resolution']['width']['std']}",
        f"  - Tinggi : Min={report['face_crop_resolution']['height']['min']} | Max={report['face_crop_resolution']['height']['max']} | Mean={report['face_crop_resolution']['height']['mean']} | Std={report['face_crop_resolution']['height']['std']}",
        f"  - Rasio W/H : Mean={report['face_crop_resolution']['aspect_ratio']['mean']} (Standar wajah ideal mendekati 1.0)",
        "",
        "-" * 75,
        "2. STATISTIK CONFIDENCE YOLOv8-FACE:",
        f"  - Mean Confidence : {report['yolo_detection_confidence']['mean']}",
        f"  - Min Confidence  : {report['yolo_detection_confidence']['min']}",
        f"  - Max Confidence  : {report['yolo_detection_confidence']['max']}",
        f"  - Standar Deviasi : {report['yolo_detection_confidence']['std']}",
        "",
        "-" * 75,
        "3. EVALUASI DUPLIKASI GAMBAR (dHash Hamming <= 5):",
        f"  - Pasangan terdeteksi sangat mirip/duplikat: {len(near_duplicates)}",
    ]
    for nd in near_duplicates[:10]:
        txt_lines.append(f"    * Image #{nd['image_a']} vs #{nd['image_b']} ({nd['actor_a']}) — Hamming Distance: {nd['hamming_distance']}")

    txt_lines.append("=" * 75)
    report_text = "\n".join(txt_lines)

    with open(cfg.STAGE02_REPORT_TXT, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n[OK] Laporan tersimpan di:\n    - {cfg.STAGE02_REPORT_JSON}\n    - {cfg.STAGE02_REPORT_TXT}")
    return report


if __name__ == "__main__":
    run_stage_02()
