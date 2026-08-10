"""
IndoLens – Audit & Diagnosis Recognition Pipeline
==================================================

Script ini menjalankan audit menyeluruh sesuai Implementation Plan:
  Tahap 1: Audit Dataset
  Tahap 2: Audit Embedding
  Tahap 3: Uji Recognition dari Dataset Sendiri
  Tahap 4: Uji Sensitivitas Threshold

Cara menjalankan:
    cd c:\\laragon\\www\\IndoLens\\python
    python audit_recognition.py

Output: Laporan langsung ke terminal + audit_report.txt
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

# ------------------------------------------------------------------
# Konfigurasi
# ------------------------------------------------------------------
from config.dataset import (
    DATASET_PATH, EMBEDDING_PATH, SUPPORTED_EXTENSION,
    FACENET_EMBEDDING_DIM, FACE_DISTANCE_THRESHOLD as DATASET_THRESHOLD
)
from config.config import FACE_DISTANCE_THRESHOLD as CONFIG_THRESHOLD

# Threshold yang diuji pada Tahap 4
THRESHOLD_CANDIDATES = [0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00, 1.10, 1.20]

lines = []  # Buffer laporan

def log(msg=""):
    print(msg)
    lines.append(msg)

def separator(char="=", n=65):
    log(char * n)


# ==================================================================
# TAHAP 1 — AUDIT DATASET WAJAH AKTOR
# ==================================================================
def audit_dataset():
    separator()
    log("TAHAP 1 — AUDIT DATASET WAJAH AKTOR")
    separator()

    if not DATASET_PATH.exists():
        log(f"[ERROR] Direktori dataset tidak ditemukan: {DATASET_PATH}")
        return {}

    actor_dirs = [d for d in sorted(DATASET_PATH.iterdir()) if d.is_dir() and not d.name.startswith(".")]

    if not actor_dirs:
        log("[WARNING] Tidak ada folder aktor dalam dataset!")
        return {}

    log(f"Lokasi dataset : {DATASET_PATH}")
    log(f"Jumlah aktor   : {len(actor_dirs)}")
    log("")

    dataset_summary = {}

    for actor_dir in actor_dirs:
        actor_name = actor_dir.name
        images = []
        for ext in SUPPORTED_EXTENSION:
            images.extend(list(actor_dir.glob(f"*.{ext}")))
            images.extend(list(actor_dir.glob(f"*.{ext.upper()}")))

        sizes = []
        for img_path in images:
            try:
                import cv2
                img = cv2.imread(str(img_path))
                if img is not None:
                    h, w = img.shape[:2]
                    sizes.append((w, h))
            except Exception:
                pass

        log(f"  Aktor       : {actor_name}")
        log(f"  Gambar      : {len(images)} file")

        if sizes:
            min_w = min(s[0] for s in sizes)
            max_w = max(s[0] for s in sizes)
            min_h = min(s[1] for s in sizes)
            max_h = max(s[1] for s in sizes)
            log(f"  Resolusi    : {min_w}x{min_h}  hingga  {max_w}x{max_h} px")
        else:
            log("  Resolusi    : Tidak dapat dibaca")

        file_sizes_kb = [img_path.stat().st_size / 1024 for img_path in images]
        if file_sizes_kb:
            log(f"  Ukuran file : {min(file_sizes_kb):.1f} KB  hingga  {max(file_sizes_kb):.1f} KB")

        if len(images) < 5:
            log("  [WARNING] Jumlah gambar sangat sedikit (< 5). Disarankan minimal 10–30 gambar per aktor.")
        elif len(images) < 10:
            log("  [WARNING] Jumlah gambar sedikit (< 10). Disarankan 20–30 gambar dengan variasi pose.")
        else:
            log("  [OK] Jumlah gambar mencukupi.")

        log("")
        dataset_summary[actor_name] = {"images": images, "count": len(images)}

    return dataset_summary


# ==================================================================
# TAHAP 2 — AUDIT EMBEDDING DATASET
# ==================================================================
def audit_embeddings():
    separator()
    log("TAHAP 2 — AUDIT EMBEDDING DATASET")
    separator()

    if not EMBEDDING_PATH.exists():
        log(f"[ERROR] Direktori embedding tidak ditemukan: {EMBEDDING_PATH}")
        return {}

    actor_dirs = [d for d in sorted(EMBEDDING_PATH.iterdir()) if d.is_dir() and not d.name.startswith(".")]

    if not actor_dirs:
        log("[WARNING] Tidak ada folder embedding ditemukan!")
        log("[INFO] Jalankan generate_embeddings.py terlebih dahulu untuk generate embedding.")
        return {}

    log(f"Lokasi embedding : {EMBEDDING_PATH}")
    log(f"Jumlah aktor     : {len(actor_dirs)}")
    log("")

    import numpy as np
    embedding_summary = {}

    for actor_dir in actor_dirs:
        actor_name = actor_dir.name
        npy_files = sorted(actor_dir.glob("*.npy"))
        log(f"  Aktor           : {actor_name}")
        log(f"  File embedding  : {len(npy_files)} .npy")

        valid = 0
        invalid = 0
        non_128d = 0
        loaded_embeddings = []

        for npy_file in npy_files:
            try:
                emb = np.load(str(npy_file))
                if emb is None or emb.size == 0:
                    invalid += 1
                    log(f"    [RUSAK] {npy_file.name} — kosong")
                elif len(emb.flatten()) != FACENET_EMBEDDING_DIM:
                    non_128d += 1
                    log(f"    [DIMENSI SALAH] {npy_file.name} — {len(emb.flatten())}D (expected {FACENET_EMBEDDING_DIM}D)")
                else:
                    valid += 1
                    loaded_embeddings.append({"file": npy_file.name, "embedding": emb.flatten()})
            except Exception as e:
                invalid += 1
                log(f"    [ERROR] {npy_file.name} — {e}")

        log(f"  Valid 128-D     : {valid}")
        if invalid > 0:
            log(f"  Rusak/Kosong    : {invalid}")
        if non_128d > 0:
            log(f"  Dimensi Salah   : {non_128d}")

        if valid == 0:
            log("  [ERROR] Tidak ada embedding valid! Perlu generate ulang.")
        elif valid < 5:
            log("  [WARNING] Embedding sedikit. Disarankan lebih dari 10 embedding per aktor.")
        else:
            log("  [OK] Embedding valid tersedia.")

        log("")
        embedding_summary[actor_name] = {
            "count": valid,
            "embeddings": loaded_embeddings
        }

    return embedding_summary


# ==================================================================
# TAHAP 3 — UJI RECOGNITION MENGGUNAKAN DATASET SENDIRI
# ==================================================================
def test_recognition_on_dataset(dataset_summary, embedding_summary):
    separator()
    log("TAHAP 3 — UJI RECOGNITION MENGGUNAKAN DATASET SENDIRI")
    separator()

    if not embedding_summary:
        log("[SKIP] Tidak ada embedding yang tersedia untuk pengujian.")
        return []

    # Lazy import agar tidak crash jika GPU/model bermasalah
    try:
        from yolo.detector import load_model as yolo_load_model, predict_frame
        from facenet.embedding_generator import load_facenet_model, generate_embedding
        from recognition.embedding_matcher import find_best_match
    except ImportError as e:
        log(f"[ERROR] Gagal import modul AI: {e}")
        return []

    log("Memuat YOLO model...")
    try:
        yolo_load_model()
        log("[OK] YOLO model dimuat.")
    except Exception as e:
        log(f"[ERROR] Gagal memuat YOLO: {e}")
        return []

    log("Memuat FaceNet model...")
    try:
        load_facenet_model()
        log("[OK] FaceNet model dimuat.")
    except Exception as e:
        log(f"[ERROR] Gagal memuat FaceNet: {e}")
        return []

    log("")
    log(f"Threshold aktif  : {CONFIG_THRESHOLD}")
    log("")

    results = []
    import cv2
    import numpy as np

    for actor_name, actor_data in dataset_summary.items():
        images = actor_data.get("images", [])
        if not images:
            log(f"  [{actor_name}] Tidak ada gambar untuk diuji.")
            continue

        log(f"  Menguji aktor: {actor_name} ({len(images)} gambar)")

        recognized_correct = 0
        recognized_wrong = 0
        not_recognized = 0
        distances_correct = []
        test_results_per_image = []

        for img_path in images:
            try:
                frame = cv2.imread(str(img_path))
                if frame is None:
                    continue

                # Deteksi wajah via YOLO
                detections = predict_frame(frame)

                if not detections:
                    # Fallback: gunakan seluruh gambar sebagai crop wajah
                    log(f"    [No YOLO Detection] {img_path.name} — Mencoba embedding langsung dari gambar penuh")
                    try:
                        emb = generate_embedding(frame)
                    except Exception as emb_err:
                        log(f"    [ERROR embedding] {img_path.name}: {emb_err}")
                        not_recognized += 1
                        test_results_per_image.append({
                            "image": img_path.name,
                            "yolo_detected": False,
                            "actor_predicted": "YOLO_FAIL",
                            "distance": 999.0,
                            "correct": False
                        })
                        continue
                else:
                    # Ambil deteksi dengan confidence tertinggi
                    best_det = max(detections, key=lambda d: d.get("confidence", 0))
                    crop_img = best_det.get("crop")
                    if crop_img is None or crop_img.size == 0:
                        not_recognized += 1
                        continue
                    try:
                        emb = generate_embedding(crop_img)
                    except Exception as emb_err:
                        log(f"    [ERROR embedding] {img_path.name}: {emb_err}")
                        not_recognized += 1
                        continue

                if emb is None or len(emb) != FACENET_EMBEDDING_DIM:
                    log(f"    [ERROR] Embedding tidak valid untuk {img_path.name}")
                    not_recognized += 1
                    continue

                result = find_best_match(emb, {k: v["embeddings"] for k, v in embedding_summary.items()}, threshold=CONFIG_THRESHOLD)

                predicted_actor = result.get("actor", "Tidak Dikenali")
                distance = result.get("distance", 999.0)
                status = result.get("status", "unknown")

                # Nama aktor dari folder → title case
                expected_formatted = actor_name.replace("_", " ").title()
                is_correct = (status == "known" and predicted_actor.lower() == expected_formatted.lower())

                if is_correct:
                    recognized_correct += 1
                    distances_correct.append(distance)
                elif status == "known":
                    recognized_wrong += 1
                else:
                    not_recognized += 1

                test_results_per_image.append({
                    "image": img_path.name,
                    "yolo_detected": bool(detections),
                    "actor_predicted": predicted_actor,
                    "distance": distance,
                    "correct": is_correct
                })

            except Exception as e:
                log(f"    [ERROR] {img_path.name}: {e}")
                not_recognized += 1

        total_tested = recognized_correct + recognized_wrong + not_recognized
        accuracy = (recognized_correct / total_tested * 100) if total_tested > 0 else 0
        avg_dist_correct = (sum(distances_correct) / len(distances_correct)) if distances_correct else None

        log(f"    Total diuji         : {total_tested}")
        log(f"    Benar dikenali      : {recognized_correct}")
        log(f"    Salah dikenali      : {recognized_wrong}")
        log(f"    Tidak dikenali      : {not_recognized}")
        log(f"    Akurasi self-test   : {accuracy:.1f}%")
        if avg_dist_correct is not None:
            log(f"    Rata-rata distance  : {avg_dist_correct:.4f} (saat benar)")

        # Detail per gambar
        log(f"    Detail per gambar:")
        for item in test_results_per_image:
            yolo_tag = "✓YOLO" if item["yolo_detected"] else "✗YOLO"
            status_tag = "✓" if item["correct"] else "✗"
            log(f"      {status_tag} {yolo_tag} | {item['image']:<30} | Predicted: {item['actor_predicted']:<30} | Dist: {item['distance']:.4f}")

        log("")

        results.append({
            "actor": actor_name,
            "total": total_tested,
            "correct": recognized_correct,
            "wrong": recognized_wrong,
            "not_recognized": not_recognized,
            "accuracy": accuracy,
            "avg_dist_correct": avg_dist_correct,
            "detail": test_results_per_image
        })

    return results


# ==================================================================
# TAHAP 4 — UJI SENSITIVITAS THRESHOLD
# ==================================================================
def test_threshold_sensitivity(recognition_results):
    separator()
    log("TAHAP 4 — UJI SENSITIVITAS THRESHOLD")
    separator()

    if not recognition_results:
        log("[SKIP] Tidak ada hasil recognition untuk dianalisis.")
        return

    log(f"Threshold aktif saat ini : {CONFIG_THRESHOLD}")
    log(f"Threshold di dataset.py  : {DATASET_THRESHOLD}")
    log("")

    # Kumpulkan semua distance yang tercatat
    all_correct_distances = []
    all_incorrect_distances = []

    for actor_result in recognition_results:
        for item in actor_result.get("detail", []):
            dist = item["distance"]
            if dist >= 999.0:
                continue
            if item["correct"]:
                all_correct_distances.append(dist)
            else:
                all_incorrect_distances.append(dist)

    if all_correct_distances:
        import numpy as np
        log(f"Distance saat BENAR dikenali:")
        log(f"  Min    : {min(all_correct_distances):.4f}")
        log(f"  Max    : {max(all_correct_distances):.4f}")
        log(f"  Rata2  : {sum(all_correct_distances)/len(all_correct_distances):.4f}")
        log(f"  Median : {float(np.median(all_correct_distances)):.4f}")
        log("")

    if all_incorrect_distances:
        import numpy as np
        log(f"Distance saat SALAH / tidak dikenali:")
        log(f"  Min    : {min(all_incorrect_distances):.4f}")
        log(f"  Max    : {max(all_incorrect_distances):.4f}")
        log(f"  Rata2  : {sum(all_incorrect_distances)/len(all_incorrect_distances):.4f}")
        log(f"  Median : {float(np.median(all_incorrect_distances)):.4f}")
        log("")

    # Simulasi berbagai threshold
    all_distances_with_label = (
        [(d, True) for d in all_correct_distances] +
        [(d, False) for d in all_incorrect_distances]
    )

    if not all_distances_with_label:
        log("[WARNING] Tidak ada data distance untuk simulasi threshold.")
        return

    log(f"{'Threshold':<12} {'Recognized':<12} {'Not Recog.':<12} {'Correct':<10} {'Wrong':<10} {'Accuracy'}")
    log("-" * 72)

    best_threshold = None
    best_accuracy = -1

    for threshold in THRESHOLD_CANDIDATES:
        recognized = [d for d, label in all_distances_with_label if d <= threshold]
        not_recognized_count = len(all_distances_with_label) - len(recognized)
        correct = sum(1 for d, label in all_distances_with_label if d <= threshold and label)
        wrong = sum(1 for d, label in all_distances_with_label if d <= threshold and not label)
        total = len(all_distances_with_label)
        accuracy = (correct / total * 100) if total > 0 else 0

        marker = " <-- AKTIF" if abs(threshold - CONFIG_THRESHOLD) < 0.001 else ""
        log(f"  {threshold:<10.2f} {len(recognized):<12} {not_recognized_count:<12} {correct:<10} {wrong:<10} {accuracy:.1f}%{marker}")

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    log("")
    log(f"Rekomendasi threshold terbaik berdasarkan data saat ini: {best_threshold} (akurasi: {best_accuracy:.1f}%)")
    log("")
    log("[CATATAN] Threshold yang tepat bergantung pada variasi wajah di video aktual.")
    log("          Nilai ini hanya berdasarkan data dataset sendiri (self-test).")


# ==================================================================
# RINGKASAN DIAGNOSIS
# ==================================================================
def print_summary(dataset_summary, embedding_summary, recognition_results):
    separator("=")
    log("RINGKASAN DIAGNOSIS")
    separator("=")

    log(f"  Dataset path    : {DATASET_PATH}")
    log(f"  Embedding path  : {EMBEDDING_PATH}")
    log(f"  Threshold aktif : {CONFIG_THRESHOLD}")
    log("")

    log("  Status per Aktor:")
    all_actors = set(list(dataset_summary.keys()) + list(embedding_summary.keys()))
    for actor in sorted(all_actors):
        ds_count = dataset_summary.get(actor, {}).get("count", 0)
        emb_count = embedding_summary.get(actor, {}).get("count", 0)
        rec = next((r for r in recognition_results if r["actor"] == actor), None)
        accuracy = f"{rec['accuracy']:.1f}%" if rec else "N/A"
        log(f"    [{actor}]")
        log(f"      Dataset   : {ds_count} gambar")
        log(f"      Embedding : {emb_count} embedding")
        log(f"      Self-test : {accuracy}")

    log("")

    # Diagnosis kemungkinan penyebab masalah
    issues = []
    for actor, emb_data in embedding_summary.items():
        if emb_data["count"] == 0:
            issues.append(f"[CRITICAL] Aktor '{actor}' tidak memiliki embedding valid — generate ulang embedding.")

    for actor, ds_data in dataset_summary.items():
        if ds_data["count"] < 5:
            issues.append(f"[WARNING] Dataset aktor '{actor}' sangat sedikit ({ds_data['count']} gambar) — tambahkan lebih banyak gambar.")

    for rec in recognition_results:
        if rec["accuracy"] < 50:
            issues.append(f"[WARNING] Self-test akurasi rendah ({rec['accuracy']:.1f}%) untuk '{rec['actor']}' — ada masalah pada pipeline atau threshold.")
        elif rec["accuracy"] < 80:
            issues.append(f"[INFO] Self-test akurasi sedang ({rec['accuracy']:.1f}%) untuk '{rec['actor']}' — pertimbangkan perbaikan dataset atau threshold.")

    if not issues:
        log("  Tidak ada masalah kritis ditemukan.")
    else:
        log("  Temuan:")
        for issue in issues:
            log(f"    {issue}")

    log("")
    log("Langkah selanjutnya:")
    log("  1. Jika embedding kosong → jalankan: python generate_embeddings.py")
    log("  2. Jika akurasi self-test < 80% → periksa threshold dan preprocessing")
    log("  3. Jika akurasi self-test OK tapi video gagal → tambahkan variasi dataset")
    log("  4. Setelah dataset diperbarui → generate ulang embedding")


# ==================================================================
# MAIN
# ==================================================================
def main():
    log("=" * 65)
    log("  IndoLens — Audit & Diagnosis Recognition Pipeline")
    log("  Tanggal: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    log("=" * 65)
    log("")

    dataset_summary = audit_dataset()
    embedding_summary = audit_embeddings()

    recognition_results = []
    if embedding_summary:
        recognition_results = test_recognition_on_dataset(dataset_summary, embedding_summary)
        test_threshold_sensitivity(recognition_results)
    else:
        separator()
        log("TAHAP 3 & 4 — DILEWATI (Tidak ada embedding tersedia)")
        log("Silakan jalankan: python generate_embeddings.py")
        separator()

    print_summary(dataset_summary, embedding_summary, recognition_results)

    # Simpan laporan ke file
    report_path = BASE_DIR / "audit_report.txt"
    with open(str(report_path), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n[LAPORAN] Disimpan ke: {report_path}")


if __name__ == "__main__":
    main()
