# hanya untuk keperluan training python local, tidak dirun di web
"""
========================================================================================
 INDOLENS JUPYTER TRAINING PIPELINE — STAGE 07: EVALUASI AKHIR DATASET & SKRIPSI
 Shell 07 di Jupyter Notebook
 
 Fungsi:
 1. Menghimpun seluruh artefak dan manifest dari Stage 01 hingga 06.
 2. Menghasilkan ringkasan komprehensif metrik skripsi:
    - Total record gambar sumber di MySQL.
    - Jumlah gambar terbaca vs rusak.
    - Rasio deteksi wajah YOLOv8 (Single Face vs Zero Face vs Multi Face).
    - Jumlah crop wajah valid dan vektor embedding 128-D valid.
    - Distribusi per aktor terdaftar.
    - Statistik jarak Euclidean Intra-Class (Mean, Min, Max, Std, % lolos threshold 0.65).
    - Statistik jarak Euclidean Inter-Class (jika tersedia >= 2 aktor).
    - Perangkat inferensi aktif (CUDA GPU vs CPU).
 3. Evaluasi Probe Set Independen (Opsional):
    Jika terdapat folder training_python/probe_set/<nama_aktor>/<foto.jpg>, sistem akan
    mengujinya terhadap reference data IndoLens dan menghitung Confusion Matrix (TP, FP, TN, FN).
    Jika belum ada probe set, sistem secara jujur mencatatnya tanpa memalsukan akurasi.
 4. Menyimpan laporan resmi ke evaluation_report.json dan evaluation_report.txt.
========================================================================================
"""

import os
import sys
import json
import time
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


def run_stage_07():
    """Eksekusi Stage 07: Evaluasi Akhir Dataset dan Metrik Skripsi."""
    cfg.ensure_artifact_dirs()

    print("\n" + "=" * 75)
    print("  STAGE 07: EVALUASI AKHIR PIPELINE DATASET & METRIK SKRIPSI")
    print("=" * 75)

    # 1. Muat Seluruh Manifest
    manifest_01 = load_manifest(cfg.STAGE01_MANIFEST)
    report_02 = load_manifest(cfg.STAGE02_REPORT_JSON)
    manifest_03 = load_manifest(cfg.STAGE03_MANIFEST)
    manifest_04 = load_manifest(cfg.STAGE04_MANIFEST)
    report_05 = load_manifest(cfg.STAGE05_REPORT_JSON)
    report_06 = load_manifest(cfg.STAGE06_REPORT_JSON)

    items_01 = manifest_01.get("items", {})
    items_03 = manifest_03.get("items", {})
    items_04 = manifest_04.get("items", {})

    total_source = len(items_01)
    if total_source == 0:
        print("[!] Belum ada data manifest yang ditemukan. Jalankan Stage 01–06 terlebih dahulu.")
        return {}

    # 2. Rekapitulasi Metrik Alur Pipeline
    count_unreadable = sum(1 for d in items_01.values() if d.get("status") == "unreadable")
    count_readable = total_source - count_unreadable
    count_zero_face = sum(1 for d in items_01.values() if d.get("status") == "zero_face")
    count_multi_face = sum(1 for d in items_01.values() if d.get("status") == "multi_face")
    count_crops_success = sum(1 for d in items_01.values() if d.get("status") == "success")

    count_tensors_success = sum(1 for d in items_03.values() if d.get("status") == "success")
    count_embeddings_success = sum(1 for d in items_04.values() if d.get("status") == "success")

    valid_embeddings_count = report_05.get("valid_embeddings_count", 0)
    registered_actors_count = report_05.get("registered_actors_count", 0)
    device_used = manifest_04.get("device", "N/A")

    intra_stats = report_05.get("intra_class_distance", {})
    inter_stats = report_05.get("inter_class_distance", {})

    # 3. Evaluasi Probe Set (Jika Ada)
    probe_results = {
        "probe_set_available": False,
        "total_probes": 0,
        "correct_predictions": 0,
        "accuracy": None,
        "note": "Tidak ada probe set di training_python/probe_set. Akurasi pengujian independen tidak dipalsukan."
    }

    if cfg.PROBE_SET_DIR.exists() and cfg.PROBE_SET_DIR.is_dir():
        probe_files = []
        for ext in cfg.SUPPORTED_EXTENSIONS:
            probe_files.extend(list(cfg.PROBE_SET_DIR.glob(f"*/*{ext}")))

        if probe_files:
            print(f"[*] Ditemukan {len(probe_files)} gambar pada probe set independen. Menjalankan evaluasi...")
            # Modul recognition IndoLens
            from python.recognition.embedding_matcher import load_all_embeddings, find_best_match
            from python.facenet.embedding_generator import generate_embedding
            from python.yolo.detector import predict_frame
            import cv2

            all_refs = load_all_embeddings(base_path=cfg.PRODUCTION_EMBEDDINGS_DIR)
            correct = 0
            total_tested = 0
            probe_records = []

            for pf in probe_files:
                ground_truth = pf.parent.name
                img_bgr = cv2.imread(str(pf))
                if img_bgr is None:
                    continue

                dets = predict_frame(img_bgr)
                if not dets:
                    pred_name = "No Face"
                    dist = 999.0
                else:
                    best_crop = max(dets, key=lambda d: d.get("confidence", 0)).get("crop")
                    emb = generate_embedding(best_crop)
                    rec = find_best_match(emb, all_refs, threshold=cfg.RECOGNITION_THRESHOLD)
                    pred_name = rec["actor"]
                    dist = rec["distance"]

                # Cek kesesuaian ground truth (case-insensitive & slug-friendly)
                is_correct = (ground_truth.lower().replace("_", " ") in pred_name.lower()) or (pred_name.lower().replace(" ", "_") == ground_truth.lower())
                if is_correct:
                    correct += 1
                total_tested += 1

                probe_records.append({
                    "file": pf.name,
                    "ground_truth": ground_truth,
                    "prediction": pred_name,
                    "distance": dist,
                    "is_correct": is_correct,
                })

            probe_results = {
                "probe_set_available": True,
                "total_probes": total_tested,
                "correct_predictions": correct,
                "accuracy": round((correct / total_tested) * 100, 2) if total_tested > 0 else 0.0,
                "records": probe_records,
            }

    # 4. Susun Laporan Komprehensif
    eval_report = {
        "evaluation_timestamp": time.time(),
        "methodology": {
            "detector": "YOLOv8-Face (conf=0.45)",
            "feature_extractor": "FaceNet InceptionResnetV1 (vggface2)",
            "embedding_dimension": cfg.EMBEDDING_DIM,
            "metric": "Euclidean Distance (L2 Norm)",
            "threshold": cfg.RECOGNITION_THRESHOLD,
        },
        "pipeline_pipeline_summary": {
            "total_mysql_records": total_source,
            "readable_images": count_readable,
            "unreadable_images": count_unreadable,
            "zero_face_images": count_zero_face,
            "multi_face_images": count_multi_face,
            "valid_crops_generated": count_crops_success,
            "valid_tensors_preprocessed": count_tensors_success,
            "valid_embeddings_generated": count_embeddings_success,
            "verified_active_embeddings": valid_embeddings_count,
            "registered_actors_count": registered_actors_count,
            "execution_device": device_used,
        },
        "mathematical_audit": {
            "intra_class_distance": intra_stats,
            "inter_class_distance": inter_stats,
        },
        "independent_probe_evaluation": probe_results,
    }

    # 5. Simpan JSON
    with open(cfg.STAGE07_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    # 6. Simpan Laporan Teks Skripsi
    if not probe_results["probe_set_available"]:
        probe_eval_note = probe_results["note"]
    else:
        probe_eval_note = f"Akurasi: {probe_results.get('accuracy')}% dari {probe_results.get('total_probes')} sampel uji."

    lines = [
        "=" * 75,
        "  LAPORAN EVALUASI AKHIR PIPELINE TRAINING INDOLENS (SKRIPSI)",
        "=" * 75,
        f"Metode Deteksi Wajah   : {eval_report['methodology']['detector']}",
        f"Model Ekstraksi Fitur  : {eval_report['methodology']['feature_extractor']}",
        f"Dimensi Vektor Acuan   : {eval_report['methodology']['embedding_dimension']}-D (L2-Normalized)",
        f"Metrik Jarak & Nilai   : {eval_report['methodology']['metric']} | Threshold <= {eval_report['methodology']['threshold']}",
        f"Perangkat Komputasi    : {device_used}",
        "",
        "-" * 75,
        "1. METRIK DATA PIPELINE (REAL COMPUTATION):",
        f"  - Total Record MySQL          : {total_source}",
        f"  - Gambar Terbaca              : {count_readable}",
        f"  - Gambar Rusak / Hilang       : {count_unreadable}",
        f"  - Zero Face (Wajah Luput)     : {count_zero_face}",
        f"  - Multi Face (Wajah Ambigu)   : {count_multi_face}",
        f"  - Wajah Berhasil Di-crop      : {count_crops_success}",
        f"  - Vektor 128-D Valid Terbina  : {valid_embeddings_count}",
        f"  - Aktor Terdaftar             : {registered_actors_count} aktor",
        "",
        "-" * 75,
        "2. AUDIT MATEMATIS JARAK EUCLIDEAN:",
        f"  - Intra-Class (Satu Aktor)    : {intra_stats.get('count', 0)} pasang pengujian",
        f"    * Mean Distance             : {intra_stats.get('mean')}",
        f"    * Min Distance              : {intra_stats.get('min')}",
        f"    * Max Distance              : {intra_stats.get('max')}",
        f"    * Standar Deviasi           : {intra_stats.get('std')}",
        f"    * % Lolos Threshold (<= 0.65): {intra_stats.get('pass_threshold_ratio', 0)*100 if intra_stats.get('pass_threshold_ratio') else 0:.1f}%",
        f"  - Inter-Class (Antar Aktor)   : {inter_stats.get('count', 0)} pasang pengujian",
        f"    * Catatan: {'Tersedia' if inter_stats.get('count', 0) > 0 else 'Hanya 1 aktor di database; tidak memalsukan data cross-actor.'}",
        "",
        "-" * 75,
        "3. PENGUJIAN PROBE SET INDEPENDEN:",
        f"  - Status Probe Set            : {'Tersedia' if probe_results['probe_set_available'] else 'Belum disediakan (Opsional)'}",
        f"  - Catatan Evaluasi            : {probe_eval_note}",
        "=" * 75,
    ]
    report_text = "\n".join(lines)

    with open(cfg.STAGE07_REPORT_TXT, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(report_text)
    print(f"\n[OK] Laporan evaluasi tersimpan di:")
    print(f"    - {cfg.STAGE07_REPORT_JSON}")
    print(f"    - {cfg.STAGE07_REPORT_TXT}")

    return eval_report


if __name__ == "__main__":
    run_stage_07()
