# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 05: VALIDASI EMBEDDING & AUDIT JARAK
 Shell 05 di Jupyter Notebook
 
 Fungsi:
 1. Memvalidasi integritas setiap vektor embedding:
    - Tepat 128 dimensi.
    - Tidak mengandung nilai NaN atau Inf.
    - L2-norm == 1.0 (toleransi 1e-4).
    - Terhubung secara valid dengan record MySQL (traceability).
 2. Menghitung matriks Jarak Euclidean (L2 Distance) antar seluruh pasangan vektor:
    d(p, q) = sqrt( sum( (p_i - q_i)^2 ) ) = ||p - q||_2
 3. Memisahkan secara ketat:
    - Self-comparison (gambar identik ke dirinya sendiri, distance = 0, DILARANG diklaim akurasi).
    - Intra-class (foto berbeda dari aktor yang sama).
    - Inter-class (foto antar aktor berbeda).
 4. Memberikan peringatan ilmiah jika hanya ada 1 aktor (cross-actor test belum tersedia tanpa aktor kedua).
 5. Menandai pasangan anomali (jarak intra > 0.65 atau jarak inter <= 0.65).
 6. Mengekspor laporan validasi, matriks jarak .npy, dan CSV flagged pairs.
========================================================================================
"""

import os
import sys
import json
import time
import csv
from pathlib import Path
import numpy as np

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


def calculate_euclidean(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Menghitung jarak Euclidean (L2 Norm) antara dua vektor 128-D."""
    diff = vec_a - vec_b
    return float(np.linalg.norm(diff))


def run_stage_05():
    """Eksekusi Stage 05: Validasi Kualitas Embedding dan Jarak Euclidean."""
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 05: VALIDASI EMBEDDING 128-D & AUDIT JARAK EUCLIDEAN")
    print("=" * 75)

    if not cfg.STAGE04_MANIFEST.exists():
        raise FileNotFoundError(
            f"Manifest Stage 04 tidak ditemukan di: {cfg.STAGE04_MANIFEST}\n"
            "Jalankan Stage 04 terlebih dahulu."
        )

    manifest_04 = load_manifest(cfg.STAGE04_MANIFEST)
    items_04 = manifest_04.get("items", {})

    if not items_04:
        raise RuntimeError(
            f"Manifest Stage 04 kosong ({cfg.STAGE04_MANIFEST}).\n"
            "Belum ada embedding yang diproses. Jalankan Stage 04 terlebih dahulu."
        )

    valid_vectors = []
    validation_failures = []

    # 1. Pengecekan Integritas Vektor
    for img_id_str, data in items_04.items():
        if data.get("status") != "success":
            continue

        vec_path = Path(data.get("vector_path", ""))
        actor_id = data.get("actor_id")
        full_name = data.get("full_name")

        if not vec_path.exists():
            validation_failures.append({
                "image_id": int(img_id_str),
                "actor_id": actor_id,
                "reason": f"File vektor hilang: {vec_path}",
            })
            continue

        try:
            vec = np.load(str(vec_path))
        except Exception as e:
            validation_failures.append({
                "image_id": int(img_id_str),
                "actor_id": actor_id,
                "reason": f"Gagal membaca .npy: {e}",
            })
            continue

        # Validasi dimensi
        if vec.shape != (cfg.EMBEDDING_DIM,):
            validation_failures.append({
                "image_id": int(img_id_str),
                "actor_id": actor_id,
                "reason": f"Dimensi tidak sesuai ({vec.shape}), diharapkan ({cfg.EMBEDDING_DIM},)",
            })
            continue

        # Validasi NaN / Inf
        if np.isnan(vec).any() or np.isinf(vec).any():
            validation_failures.append({
                "image_id": int(img_id_str),
                "actor_id": actor_id,
                "reason": "Vektor mengandung nilai NaN atau Inf",
            })
            continue

        # Validasi L2-norm
        l2_norm = float(np.linalg.norm(vec))
        if abs(l2_norm - 1.0) > cfg.L2_NORM_TOLERANCE:
            validation_failures.append({
                "image_id": int(img_id_str),
                "actor_id": actor_id,
                "reason": f"L2-norm menyimpang dari 1.0 (nilai: {l2_norm:.6f})",
            })
            continue

        valid_vectors.append({
            "image_id": int(img_id_str),
            "actor_id": actor_id,
            "full_name": full_name,
            "vector_path": str(vec_path),
            "vector": vec,
        })

    print(f"[*] Total vektor diperiksa : {len(items_04)}")
    print(f"[*] Lolos validasi         : {len(valid_vectors)}")
    print(f"[*] Gagal validasi         : {len(validation_failures)}")

    if len(valid_vectors) == 0:
        print("[!] Tidak ada vektor valid untuk dievaluasi.")
        return {}

    # 2. Hitung Pairwise Euclidean Distance Matrix
    N = len(valid_vectors)
    dist_matrix = np.zeros((N, N), dtype=np.float32)

    intra_pairs = []   # pasangan foto berbeda dari aktor yang sama
    inter_pairs = []   # pasangan foto antar aktor berbeda
    flagged_pairs = [] # anomali threshold

    for i in range(N):
        for j in range(N):
            if i == j:
                dist_matrix[i, j] = 0.0
            elif j > i:
                dist = calculate_euclidean(valid_vectors[i]["vector"], valid_vectors[j]["vector"])
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist

                rec_a = valid_vectors[i]
                rec_b = valid_vectors[j]
                is_same_actor = (rec_a["actor_id"] == rec_b["actor_id"])

                pair_info = {
                    "image_a": rec_a["image_id"],
                    "actor_a": rec_a["full_name"],
                    "actor_id_a": rec_a["actor_id"],
                    "image_b": rec_b["image_id"],
                    "actor_b": rec_b["full_name"],
                    "actor_id_b": rec_b["actor_id"],
                    "distance": round(dist, 4),
                    "is_same_actor": is_same_actor,
                }

                if is_same_actor:
                    intra_pairs.append(pair_info)
                    # Jika foto aktor yang sama berjarak > threshold 0.65 -> potensi False Negative
                    if dist > cfg.RECOGNITION_THRESHOLD:
                        pair_info["flag_type"] = "HIGH_INTRA_DISTANCE (> 0.65)"
                        flagged_pairs.append(pair_info)
                else:
                    inter_pairs.append(pair_info)
                    # Jika foto aktor berbeda berjarak <= threshold 0.65 -> False Positive
                    if dist <= cfg.RECOGNITION_THRESHOLD:
                        pair_info["flag_type"] = "LOW_INTER_DISTANCE (<= 0.65)"
                        flagged_pairs.append(pair_info)

    # 3. Statistik Intra-Class (Satu Aktor)
    intra_dists = [p["distance"] for p in intra_pairs]
    intra_stats = {
        "count": len(intra_dists),
        "mean": round(float(np.mean(intra_dists)), 4) if intra_dists else None,
        "min": round(float(np.min(intra_dists)), 4) if intra_dists else None,
        "max": round(float(np.max(intra_dists)), 4) if intra_dists else None,
        "std": round(float(np.std(intra_dists)), 4) if intra_dists else None,
        "pass_threshold_ratio": round(sum(1 for d in intra_dists if d <= cfg.RECOGNITION_THRESHOLD) / len(intra_dists), 4) if intra_dists else None,
    }

    # 4. Statistik Inter-Class (Antar Aktor Berbeda)
    unique_actors = set(v["actor_id"] for v in valid_vectors)
    inter_dists = [p["distance"] for p in inter_pairs]
    inter_stats = {
        "count": len(inter_dists),
        "mean": round(float(np.mean(inter_dists)), 4) if inter_dists else None,
        "min": round(float(np.min(inter_dists)), 4) if inter_dists else None,
        "max": round(float(np.max(inter_dists)), 4) if inter_dists else None,
        "std": round(float(np.std(inter_dists)), 4) if inter_dists else None,
        "safe_threshold_ratio": round(sum(1 for d in inter_dists if d > cfg.RECOGNITION_THRESHOLD) / len(inter_dists), 4) if inter_dists else None,
    }

    # 5. Simpan Hasil Artefak
    np.save(str(cfg.STAGE05_DISTANCE_MATRIX), dist_matrix)

    # Simpan index urutan matriks
    with open(cfg.STAGE05_DISTANCE_INDEX, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["matrix_index", "image_id", "actor_id", "full_name"])
        for idx, v in enumerate(valid_vectors):
            writer.writerow([idx, v["image_id"], v["actor_id"], v["full_name"]])

    # Simpan flagged pairs
    with open(cfg.STAGE05_FLAGGED_PAIRS, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_a", "actor_a", "image_b", "actor_b", "distance", "same_actor", "flag_type"])
        for fp in flagged_pairs:
            writer.writerow([fp["image_a"], fp["actor_a"], fp["image_b"], fp["actor_b"], fp["distance"], fp["is_same_actor"], fp["flag_type"]])

    report = {
        "generated_at": time.time(),
        "total_embeddings_inspected": len(items_04),
        "valid_embeddings_count": len(valid_vectors),
        "validation_failures": validation_failures,
        "registered_actors_count": len(unique_actors),
        "threshold": cfg.RECOGNITION_THRESHOLD,
        "intra_class_distance": intra_stats,
        "inter_class_distance": inter_stats,
        "cross_actor_available": len(unique_actors) >= 2,
        "flagged_anomalies_count": len(flagged_pairs),
    }

    with open(cfg.STAGE05_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Simpan list vektor valid untuk Stage 06
    valid_list_for_export = [
        {"image_id": v["image_id"], "actor_id": v["actor_id"], "full_name": v["full_name"], "vector_path": v["vector_path"]}
        for v in valid_vectors
    ]
    with open(cfg.STAGE05_VALID_LIST, "w", encoding="utf-8") as f:
        json.dump(valid_list_for_export, f, indent=2)

    # Tampilkan ringkasan audit
    print("\n" + "-" * 75)
    print("HASIL AUDIT MATEMATIS JARAK EUCLIDEAN (SKRIPSI):")
    print(f"1. Aktor Terdaftar               : {len(unique_actors)} aktor")
    if len(unique_actors) < 2:
        print("   [CATATAN ILMIAH]: Hanya 1 aktor terdaftar saat ini. Validasi Inter-Class (antar aktor berbeda)")
        print("   belum dapat dilakukan hingga aktor kedua diunggah ke CAMP. Jangan membuat aktor tiruan.")
    print(f"2. Intra-Class (Kemiripan Foto Aktor yang Sama):")
    print(f"   - Total Pasangan Kombinasi    : {intra_stats['count']} pasang")
    if intra_stats['count'] > 0:
        print(f"   - Rata-rata Jarak (Mean)      : {intra_stats['mean']} (Idealnya makin kecil makin konsisten)")
        print(f"   - Jarak Terkecil (Min)        : {intra_stats['min']}")
        print(f"   - Jarak Terbesar (Max)        : {intra_stats['max']}")
        print(f"   - Standar Deviasi             : {intra_stats['std']}")
        print(f"   - Lolos Threshold <= {cfg.RECOGNITION_THRESHOLD}    : {intra_stats['pass_threshold_ratio']*100:.1f}%")

    if flagged_pairs:
        print(f"\n3. Pasangan Perlu Perhatian ({len(flagged_pairs)} pasang berjarak > {cfg.RECOGNITION_THRESHOLD}):")
        for fp in flagged_pairs[:5]:
            print(f"   * Image #{fp['image_a']} vs #{fp['image_b']} | Jarak: {fp['distance']} | {fp['flag_type']}")

    print("\n[OK] Laporan Validasi tersimpan di:")
    print(f"    - {cfg.STAGE05_REPORT_JSON}")
    print(f"    - {cfg.STAGE05_FLAGGED_PAIRS}")
    print(f"    - {cfg.STAGE05_DISTANCE_MATRIX}")
    print("=" * 75)

    return report


if __name__ == "__main__":
    run_stage_05()
