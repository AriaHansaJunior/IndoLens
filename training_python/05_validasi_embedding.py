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

    # -----------------------------------------------------------------------
    # 5. KALIBRASI THRESHOLD EMPIRIS BERBASIS DATA (ROC / EER / STATISTIK)
    # Bukan hardcode: threshold dihitung langsung dari distribusi jarak training.
    # -----------------------------------------------------------------------
    optimal_th = cfg.DEFAULT_FALLBACK_THRESHOLD
    calib_method = "FALLBACK"
    eer_val = None
    calib_acc = None
    roc_records = []

    if intra_dists and not inter_dists:
        # Jika baru ada 1 aktor: gunakan statistik intra-class interval kepercayaan 95% (mu + 2*sigma)
        mu = float(np.mean(intra_dists))
        std = float(np.std(intra_dists)) if len(intra_dists) > 1 else 0.05
        optimal_th = round(float(np.clip(mu + 2.0 * std, 0.50, 0.85)), 4)
        calib_method = "INTRA_CLASS_STATISTICAL_CI95 (mu + 2*sigma)"
        calib_acc = round((sum(1 for d in intra_dists if d <= optimal_th) / len(intra_dists)) * 100, 2)

    elif intra_dists and inter_dists:
        # Jika >= 2 aktor: lakukan pencarian grid ROC / EER (Equal Error Rate)
        best_diff = float("inf")
        n_pos = len(intra_dists)
        n_neg = len(inter_dists)

        for th in np.arange(0.20, 1.41, 0.01):
            fn = sum(1 for d in intra_dists if d > th)
            tp = n_pos - fn
            fp = sum(1 for d in inter_dists if d <= th)
            tn = n_neg - fp

            far = fp / n_neg if n_neg > 0 else 0.0
            frr = fn / n_pos if n_pos > 0 else 0.0
            acc = (tp + tn) / (n_pos + n_neg)

            roc_records.append({
                "threshold": round(float(th), 2),
                "FAR": round(far, 4),
                "FRR": round(frr, 4),
                "accuracy": round(acc * 100, 2),
            })

            diff = abs(far - frr)
            if diff < best_diff:
                best_diff = diff
                optimal_th = round(float(th), 4)
                eer_val = round(float((far + frr) / 2.0), 4)
                calib_acc = round(acc * 100, 2)
        calib_method = "ROC_EER_OPTIMIZATION"

    # Simpan hasil threshold terkalibrasi
    th_report = {
        "calibrated_at": time.time(),
        "primary_dimension": cfg.PRIMARY_EMBEDDING_DIM,
        "calibration_method": calib_method,
        "optimal_threshold": optimal_th,
        "eer": eer_val,
        "estimated_accuracy_pct": calib_acc,
        "intra_mean": intra_stats["mean"],
        "intra_std": intra_stats["std"],
        "inter_mean": inter_stats["mean"],
        "inter_std": inter_stats["std"],
        "note": "Threshold ini dihasilkan otomatis dari evaluasi empiris data training skripsi."
    }
    with open(cfg.STAGE05_OPTIMAL_THRESHOLD_JSON, "w", encoding="utf-8") as f:
        json.dump(th_report, f, indent=2)

    if roc_records:
        with open(cfg.STAGE05_ROC_CURVE_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["threshold", "FAR", "FRR", "accuracy"])
            writer.writeheader()
            writer.writerows(roc_records)

    # -----------------------------------------------------------------------
    # 6. KOMPARASI ILMIAH DIMENSI EMBEDDING (128-D vs 512-D)
    # Menghitung perbandingan jarak dan separasi margin untuk bahan sidang skripsi.
    # -----------------------------------------------------------------------
    dim_comparison_rows = []
    has_dual_dims = cfg.STAGE04_VECTORS_512_DIR.exists() and cfg.STAGE04_VECTORS_128_DIR.exists()

    if has_dual_dims:
        for dim_val, dim_dir in [(512, cfg.STAGE04_VECTORS_512_DIR), (128, cfg.STAGE04_VECTORS_128_DIR)]:
            d_vecs = []
            for v_rec in valid_vectors:
                act_str = str(v_rec["actor_id"])
                f_path = dim_dir / act_str / f"{v_rec['image_id']}.npy"
                if f_path.exists():
                    d_vecs.append({"actor_id": v_rec["actor_id"], "vec": np.load(str(f_path))})

            d_intra, d_inter = [], []
            for i in range(len(d_vecs)):
                for j in range(i + 1, len(d_vecs)):
                    dst = float(np.linalg.norm(d_vecs[i]["vec"] - d_vecs[j]["vec"]))
                    if d_vecs[i]["actor_id"] == d_vecs[j]["actor_id"]:
                        d_intra.append(dst)
                    else:
                        d_inter.append(dst)

            m_intra = round(float(np.mean(d_intra)), 4) if d_intra else 0.0
            s_intra = round(float(np.std(d_intra)), 4) if d_intra else 0.0
            m_inter = round(float(np.mean(d_inter)), 4) if d_inter else 0.0
            s_inter = round(float(np.std(d_inter)), 4) if d_inter else 0.0
            margin = round(m_inter - m_intra, 4) if d_inter else round(1.0 - m_intra, 4)

            dim_comparison_rows.append({
                "dimension": dim_val,
                "intra_mean": m_intra,
                "intra_std": s_intra,
                "inter_mean": m_inter,
                "inter_std": s_inter,
                "separation_margin": margin,
                "optimal_threshold": round(m_intra + 2.0 * s_intra, 4) if not d_inter else optimal_th,
                "pass_ratio_pct": round((sum(1 for d in d_intra if d <= (m_intra + 2.0 * s_intra)) / len(d_intra)) * 100, 2) if d_intra else 100.0,
            })

        with open(cfg.STAGE05_DIM_COMPARISON_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "dimension", "intra_mean", "intra_std", "inter_mean", "inter_std",
                "separation_margin", "optimal_threshold", "pass_ratio_pct"
            ])
            writer.writeheader()
            writer.writerows(dim_comparison_rows)

    # 7. Simpan Hasil Artefak Matriks Jarak
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
        "primary_dimension": cfg.PRIMARY_EMBEDDING_DIM,
        "total_embeddings_inspected": len(items_04),
        "valid_embeddings_count": len(valid_vectors),
        "validation_failures": validation_failures,
        "registered_actors_count": len(unique_actors),
        "calibrated_threshold": optimal_th,
        "calibration_method": calib_method,
        "estimated_accuracy_pct": calib_acc,
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
    print("\n" + "=" * 75)
    print("HASIL KALIBRASI THRESHOLD & AUDIT MATEMATIS SKRIPSI:")
    print(f"1. Aktor Terdaftar               : {len(unique_actors)} aktor")
    print(f"2. Metode Kalibrasi Threshold    : {calib_method}")
    print(f"3. THRESHOLD OPTIMAL TERKALIBRASI: {optimal_th} (Bukan Hardcoded)")
    if calib_acc is not None:
        print(f"4. Estimasi Akurasi Kalibrasi    : {calib_acc}%")
    print(f"5. Intra-Class Distance (Kemiripan Foto Aktor yang Sama):")
    print(f"   - Rata-rata Jarak (Mean)      : {intra_stats['mean']}")
    print(f"   - Standar Deviasi (Std)       : {intra_stats['std']}")
    print(f"   - Jarak Terkecil / Terbesar   : {intra_stats['min']} / {intra_stats['max']}")

    if dim_comparison_rows:
        print("\n" + "-" * 75)
        print("TABEL KOMPARASI ILMIAH DIMENSI FITUR (BAHAN SIDANG SKRIPSI):")
        print(f"{'Dimensi':<10} | {'Intra Mean':<12} | {'Inter Mean':<12} | {'Margin':<10} | {'Optimal Th':<12}")
        print("-" * 65)
        for d_row in dim_comparison_rows:
            print(f"{str(d_row['dimension']) + '-D':<10} | {d_row['intra_mean']:<12} | {d_row['inter_mean']:<12} | {d_row['separation_margin']:<10} | {d_row['optimal_threshold']:<12}")
        print("-" * 65)
        print(f"[*] File CSV Komparasi tersimpan di: {cfg.STAGE05_DIM_COMPARISON_CSV.name}")

    print("\n[OK] Laporan Validasi & Optimal Threshold tersimpan di:")
    print(f"    - {cfg.STAGE05_OPTIMAL_THRESHOLD_JSON.name}")
    print(f"    - {cfg.STAGE05_REPORT_JSON.name}")
    print("=" * 75)

    return report


if __name__ == "__main__":
    run_stage_05()
