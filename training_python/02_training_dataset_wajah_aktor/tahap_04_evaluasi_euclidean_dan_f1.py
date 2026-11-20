"""Tahap 04 (Dataset Aktor): Kalibrasi batas ambang jarak Euclidean, Confusion Matrix, Accuracy, Precision, Recall, & F1-Score."""

import csv
import json
import sys
import time
from pathlib import Path
import numpy as np

# Menambahkan root proyek, folder training_python, dan folder python ke sys.path untuk eksekusi Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig
from facenet.embedding_generator import (
    muat_model_hasil_training_facenet,
    ekstrak_vektor_embedding_wajah,
)
from recognition.euclidean_distance import hitung_jarak_euclidean
from recognition.embedding_matcher import (
    muat_semua_database_embedding_aktor,
    cari_kecocokan_aktor_terdekat,
)
from recognition.threshold import format_nama_tampilan_aktor
from evaluation.confusion_matrix import (
    bangun_matriks_konfusi,
    ekspor_matriks_konfusi_ke_dict,
    simpan_visualisasi_matriks_konfusi,
)
from evaluation.metrics import hitung_seluruh_metrik_evaluasi


def hitung_distribusi_jarak_intra_dan_inter_kelas(
    kamus_embedding_referensi: dict[str, list[dict]],
    daftar_vektor_orang_random: list[np.ndarray],
) -> dict:
    """
    Menghitung statistik jarak Euclidean intra-class (pasangan wajah dari aktor yang sama)
    dan inter-class (pasangan wajah antar-aktor berbeda atau terhadap wajah orang random).
    """
    jarak_intra_kelas: list[float] = []
    jarak_inter_kelas: list[float] = []

    daftar_slug = sorted(kamus_embedding_referensi.keys())
    for idx_a, slug_a in enumerate(daftar_slug):
        koleksi_a = kamus_embedding_referensi[slug_a]
        for i in range(len(koleksi_a)):
            for j in range(i + 1, len(koleksi_a)):
                jarak_intra_kelas.append(
                    hitung_jarak_euclidean(koleksi_a[i]["embedding"], koleksi_a[j]["embedding"])
                )

        for slug_b in daftar_slug[idx_a + 1 :]:
            koleksi_b = kamus_embedding_referensi[slug_b]
            for item_a in koleksi_a:
                for item_b in koleksi_b:
                    jarak_inter_kelas.append(
                        hitung_jarak_euclidean(item_a["embedding"], item_b["embedding"])
                    )

        for item_a in koleksi_a:
            for vek_rand in daftar_vektor_orang_random:
                jarak_inter_kelas.append(hitung_jarak_euclidean(item_a["embedding"], vek_rand))

    def rangkum_array_jarak(daftar_nilai: list[float]) -> dict:
        if not daftar_nilai:
            return {"jumlah_pasangan": 0, "rata_rata": 0.0, "std": 0.0, "minimum": 0.0, "maksimum": 0.0}
        arr = np.asarray(daftar_nilai, dtype=np.float32)
        return {
            "jumlah_pasangan": len(daftar_nilai),
            "rata_rata": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "minimum": round(float(np.min(arr)), 4),
            "maksimum": round(float(np.max(arr)), 4),
        }

    return {
        "statistik_jarak_intra_kelas": rangkum_array_jarak(jarak_intra_kelas),
        "statistik_jarak_inter_kelas": rangkum_array_jarak(jarak_inter_kelas),
    }


def hitung_kesehatan_dimensi_embedding(kamus_embedding_referensi: dict[str, list[dict]]) -> dict:
    """
    Menganalisis sebaran dimensi efektif ruang vektor 512-D menggunakan SVD
    untuk memastikan embedding referensi tersebar luas tanpa dimensional collapse.
    """
    semua_vektor = [
        np.asarray(item["embedding"], dtype=np.float32)
        for daftar_item in kamus_embedding_referensi.values()
        for item in daftar_item
    ]
    if len(semua_vektor) < 4:
        return {"dimensi_efektif_95_persen": 0, "rasio_variansi_top3": 0.0}

    matriks = np.stack(semua_vektor, axis=0)
    matriks_pusat = matriks - np.mean(matriks, axis=0, keepdims=True)
    _, nilai_singular, _ = np.linalg.svd(matriks_pusat, full_matrices=False)
    total_variansi = float(np.sum(nilai_singular ** 2))
    if total_variansi <= 1e-12:
        return {"dimensi_efektif_95_persen": 0, "rasio_variansi_top3": 1.0}

    rasio_variansi = (nilai_singular ** 2) / total_variansi
    kumulatif = np.cumsum(rasio_variansi)
    return {
        "dimensi_efektif_95_persen": int(np.searchsorted(kumulatif, 0.95) + 1),
        "rasio_variansi_top3": round(float(np.sum(rasio_variansi[:3])), 4),
    }


def kumpulkan_sampel_uji_evaluasi(
    manifest_crop: dict,
    model_facenet_aktif,
) -> tuple[list[dict], list[np.ndarray]]:
    """
    Mengekstrak vektor embedding 512-D dari sampel asli wajah aktor (untuk evaluasi Leave-One-Image-Out)
    dan sampel wajah orang random (Unknown) agar rasio kelas uji seimbang dan bebas data leakage.
    """
    daftar_sampel_evaluasi: list[dict] = []
    daftar_vektor_random: list[np.ndarray] = []

    for slug_aktor, info_aktor in sorted(manifest_crop.get("aktor", {}).items()):
        nama_resmi = format_nama_tampilan_aktor(info_aktor.get("full_name") or slug_aktor)
        koleksi_uji = info_aktor.get("sampel_asli", [])

        for indeks_sampel, item_uji in enumerate(koleksi_uji, start=1):
            path_npy = Path(item_uji["path_tensor_npy"])
            if not path_npy.exists():
                continue
            tensor_norm = np.load(str(path_npy)).astype(np.float32)
            vektor_uji = ekstrak_vektor_embedding_wajah(
                tensor_norm,
                model_facenet_aktif=model_facenet_aktif,
                sudah_ternormalisasi=True,
            )
            id_gambar = str(item_uji.get("image_id") or indeks_sampel)
            daftar_sampel_evaluasi.append(
                {
                    "label_sebenarnya": nama_resmi,
                    "vektor_embedding": vektor_uji,
                    "id_gambar": id_gambar,
                    "nama_file_npy": f"{id_gambar}.npy",
                    "tipe_data": "aktor_terdaftar",
                }
            )

    for item_rand in manifest_crop.get("orang_random", []):
        path_npy_rand = Path(item_rand["path_tensor_npy"])
        if not path_npy_rand.exists():
            continue
        tensor_rand = np.load(str(path_npy_rand)).astype(np.float32)
        vektor_rand = ekstrak_vektor_embedding_wajah(
            tensor_rand,
            model_facenet_aktif=model_facenet_aktif,
            sudah_ternormalisasi=True,
        )
        daftar_vektor_random.append(vektor_rand)
        daftar_sampel_evaluasi.append(
            {
                "label_sebenarnya": "Tidak Dikenali",
                "vektor_embedding": vektor_rand,
                "id_gambar": str(item_rand.get("id_sampel", "random")),
                "nama_file_npy": None,
                "tipe_data": "orang_random_unknown",
            }
        )

    return daftar_sampel_evaluasi, daftar_vektor_random


def kalibrasi_threshold_dan_evaluasi_matrix_f1(
    path_bobot_facenet: Path = konfig.FILE_BOBOT_HASIL_TRAINING_FACENET,
    folder_embedding_produksi: Path = konfig.FOLDER_EMBEDDING_PRODUKSI,
) -> dict:
    """
    Memuat database embedding referensi (.npy) dari python/embeddings/ dan model FaceNet di GPU RTX 4060,
    menguji rentang batas ambang jarak Euclidean (0.45 s/d 1.15) untuk menemukan threshold dengan F1-Score tertinggi,
    serta menghasilkan tabel Confusion Matrix (TP, TN, FP, FN), Accuracy, Precision, Recall, dan F1-Score.
    """
    # Mengaktifkan mode output Jupyter unlimited sebelum mencetak kalibrasi threshold dan Confusion Matrix
    konfig.aktifkan_output_notebook_unlimited()
    konfig.pastikan_semua_folder_tersedia()
    path_manifest_crop = konfig.FOLDER_CROP_WAJAH_160X160 / "manifest_preprocessing_wajah.json"
    if not path_manifest_crop.exists():
        raise FileNotFoundError(
            f"Manifest preprocessing wajah belum ditemukan di: {path_manifest_crop}\n"
            "Jalankan Tahap 01 (ekstrak_dan_preprocess_wajah_dataset) terlebih dahulu."
        )

    _, _, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)
    model_facenet = muat_model_hasil_training_facenet(path_bobot_facenet)
    kamus_embedding_referensi = muat_semua_database_embedding_aktor(folder_embedding_produksi)

    if not kamus_embedding_referensi:
        raise RuntimeError(
            f"Database embedding referensi kosong di: {folder_embedding_produksi}\n"
            "Jalankan Tahap 03 (buat_database_embedding_referensi) terlebih dahulu."
        )

    manifest_crop = json.loads(path_manifest_crop.read_text(encoding="utf-8"))
    waktu_mulai = time.time()

    print("=" * 78)
    print("  TAHAP 04: EVALUASI EUCLIDEAN DISTANCE, CONFUSION MATRIX, & F1-SCORE")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']}")
    print(f"[*] Jumlah Aktor Referensi      : {len(kamus_embedding_referensi)} aktor")

    daftar_sampel_evaluasi, daftar_vektor_random = kumpulkan_sampel_uji_evaluasi(
        manifest_crop,
        model_facenet,
    )
    distribusi_jarak = hitung_distribusi_jarak_intra_dan_inter_kelas(
        kamus_embedding_referensi,
        daftar_vektor_random,
    )
    kesehatan_dimensi = hitung_kesehatan_dimensi_embedding(kamus_embedding_referensi)

    # Menguji rentang threshold lebih luas (0.20 s/d 1.15) dengan evaluasi Leave-One-Image-Out bebas leakage
    kandidat_threshold = [round(0.20 + (i * 0.05), 2) for i in range(20)]
    tabel_uji_threshold: list[dict] = []
    kandidat_terbaik_aman: dict | None = None
    kandidat_terbaik_seimbang: dict | None = None

    for ambang_uji in kandidat_threshold:
        label_asli_uji = []
        label_prediksi_uji = []

        for sampel in daftar_sampel_evaluasi:
            file_dikecualikan = {sampel["nama_file_npy"]} if sampel.get("nama_file_npy") else None
            hasil_cocok = cari_kecocokan_aktor_terdekat(
                sampel["vektor_embedding"],
                kamus_embedding_referensi,
                batas_ambang_jarak=ambang_uji,
                kecualikan_file_npy=file_dikecualikan,
            )
            label_asli_uji.append(sampel["label_sebenarnya"])
            label_prediksi_uji.append(hasil_cocok["actor"])

        metrik_uji = hitung_seluruh_metrik_evaluasi(
            label_asli_uji,
            label_prediksi_uji,
            label_unknown="Tidak Dikenali",
        )
        total_negatif_uji = metrik_uji["true_negatives"] + metrik_uji["false_positives"]
        specificity_unknown = (
            round(metrik_uji["true_negatives"] / total_negatif_uji, 4)
            if total_negatif_uji > 0
            else 1.0
        )
        skor_seimbang = round((0.50 * metrik_uji["f1_score"]) + (0.50 * specificity_unknown), 4)

        baris_threshold = {
            "batas_ambang_jarak": ambang_uji,
            **metrik_uji,
            "specificity_unknown": specificity_unknown,
            "skor_seimbang": skor_seimbang,
        }
        tabel_uji_threshold.append(baris_threshold)

        # Memprioritaskan threshold ketat (<= 0.55) dengan penolakan Unknown >= 97% agar kamera web bebas false positive
        if specificity_unknown >= 0.97 and ambang_uji <= 0.55:
            if kandidat_terbaik_aman is None or (
                baris_threshold["skor_seimbang"] > kandidat_terbaik_aman["skor_seimbang"] + 1e-4
            ) or (
                abs(baris_threshold["skor_seimbang"] - kandidat_terbaik_aman["skor_seimbang"]) <= 1e-4
                and baris_threshold["batas_ambang_jarak"] < kandidat_terbaik_aman["batas_ambang_jarak"]
            ):
                kandidat_terbaik_aman = baris_threshold

        if kandidat_terbaik_seimbang is None or (
            baris_threshold["skor_seimbang"] > kandidat_terbaik_seimbang["skor_seimbang"] + 1e-4
        ) or (
            abs(baris_threshold["skor_seimbang"] - kandidat_terbaik_seimbang["skor_seimbang"]) <= 1e-4
            and baris_threshold["batas_ambang_jarak"] < kandidat_terbaik_seimbang["batas_ambang_jarak"]
        ):
            kandidat_terbaik_seimbang = baris_threshold

    baris_terpilih = kandidat_terbaik_aman or kandidat_terbaik_seimbang
    threshold_optimal = float(baris_terpilih["batas_ambang_jarak"]) if baris_terpilih else konfig.BATAS_AMBANG_JARAK_AWAL

    # Menghitung prediksi akhir dan Confusion Matrix menggunakan threshold_optimal (Leave-One-Image-Out)
    daftar_label_asli_final = []
    daftar_label_prediksi_final = []
    for sampel in daftar_sampel_evaluasi:
        file_dikecualikan = {sampel["nama_file_npy"]} if sampel.get("nama_file_npy") else None
        hasil_final = cari_kecocokan_aktor_terdekat(
            sampel["vektor_embedding"],
            kamus_embedding_referensi,
            batas_ambang_jarak=threshold_optimal,
            kecualikan_file_npy=file_dikecualikan,
        )
        daftar_label_asli_final.append(sampel["label_sebenarnya"])
        daftar_label_prediksi_final.append(hasil_final["actor"])

    metrik_final = hitung_seluruh_metrik_evaluasi(
        daftar_label_asli_final,
        daftar_label_prediksi_final,
        label_unknown="Tidak Dikenali",
    )
    total_negatif_final = metrik_final["true_negatives"] + metrik_final["false_positives"]
    metrik_final["specificity_unknown"] = (
        round(metrik_final["true_negatives"] / total_negatif_final, 4)
        if total_negatif_final > 0
        else 1.0
    )
    matriks_konfusi, daftar_kelas_urut = bangun_matriks_konfusi(
        daftar_label_asli_final,
        daftar_label_prediksi_final,
    )
    dict_matriks_konfusi = ekspor_matriks_konfusi_ke_dict(matriks_konfusi, daftar_kelas_urut)

    path_gambar_cm = konfig.FOLDER_HASIL_EVALUASI_METRIK / "confusion_matrix_pengenalan_aktor.png"
    simpan_visualisasi_matriks_konfusi(matriks_konfusi, daftar_kelas_urut, path_gambar_cm)

    path_csv_threshold = konfig.FOLDER_HASIL_EVALUASI_METRIK / "tabel_perbandingan_threshold.csv"
    if tabel_uji_threshold:
        with open(path_csv_threshold, "w", newline="", encoding="utf-8") as file_csv:
            penulis_csv = csv.DictWriter(file_csv, fieldnames=list(tabel_uji_threshold[0].keys()))
            penulis_csv.writeheader()
            penulis_csv.writerows(tabel_uji_threshold)

    durasi_detik = round(time.time() - waktu_mulai, 2)
    laporan_evaluasi_lengkap = {
        "waktu_evaluasi": time.strftime("%Y-%m-%d %H:%M:%S"),
        "durasi_evaluasi_detik": durasi_detik,
        "perangkat_gpu": info_perangkat_gpu["nama_gpu"],
        "metode_evaluasi": "Leave-One-Image-Out (LOIO) + Centroid-TopK Matching",
        "batas_ambang_jarak_optimal": threshold_optimal,
        "kesehatan_dimensi_embedding": kesehatan_dimensi,
        "metrik_utama_skripsi": metrik_final,
        "distribusi_jarak_euclidean": distribusi_jarak,
        "confusion_matrix": dict_matriks_konfusi,
        "path_visualisasi_confusion_matrix": str(path_gambar_cm),
        "path_csv_perbandingan_threshold": str(path_csv_threshold),
        "tabel_uji_threshold": tabel_uji_threshold,
    }

    path_json_laporan = konfig.FOLDER_HASIL_EVALUASI_METRIK / "laporan_evaluasi_matrix_dan_f1.json"
    path_json_laporan.write_text(json.dumps(laporan_evaluasi_lengkap, indent=2), encoding="utf-8")

    print(f"[OK] Batas Ambang Jarak Optimal (Threshold) : {threshold_optimal}")
    print(f"[OK] Accuracy                               : {metrik_final['accuracy'] * 100:.2f}%")
    print(f"[OK] Precision                              : {metrik_final['precision'] * 100:.2f}%")
    print(f"[OK] Recall                                 : {metrik_final['recall'] * 100:.2f}%")
    print(f"[OK] F1-Score                               : {metrik_final['f1_score'] * 100:.2f}%")
    print(f"[OK] Penolakan Unknown (Specificity / TNR)  : {metrik_final['specificity_unknown'] * 100:.2f}%")
    print(f"[OK] Dimensi Efektif 95% (SVD)              : {kesehatan_dimensi['dimensi_efektif_95_persen']} dimensi (Top-3 var = {kesehatan_dimensi['rasio_variansi_top3'] * 100:.1f}%)")
    print(
        f"[OK] Komponen Confusion Matrix              : "
        f"TP={metrik_final['true_positives']}, TN={metrik_final['true_negatives']}, "
        f"FP={metrik_final['false_positives']}, FN={metrik_final['false_negatives']}"
    )
    print(f"[OK] Gambar Confusion Matrix disimpan ke    : {path_gambar_cm}")
    print(f"[OK] Laporan JSON evaluasi disimpan ke      : {path_json_laporan}")

    return laporan_evaluasi_lengkap


if __name__ == "__main__":
    kalibrasi_threshold_dan_evaluasi_matrix_f1()
