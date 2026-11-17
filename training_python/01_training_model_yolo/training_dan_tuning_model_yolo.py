"""Tahap 02: Pelatihan model YOLOv8 deteksi wajah dari Epoch 0 (tanpa pre-trained) menggunakan GPU RTX 4060."""

import csv
import json
import shutil
import sys
import time
from pathlib import Path

# Menambahkan root proyek dan folder training_python ke sys.path agar aman dijalankan dari Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

from ultralytics import YOLO
import konfigurasi_training as konfig


def muat_arsitektur_yolov8_polos(
    path_arsitektur_yaml: Path = konfig.FILE_ARSITEKTUR_YOLOV8_YAML,
) -> YOLO:
    """
    Memuat definisi struktur jaringan saraf YOLOv8 dari file .yaml polosan (bobot acak / belum dilatih)
    serta menolak file berekstensi .pt atau .pth agar bebas dari model pre-trained.
    """
    path_yaml = Path(path_arsitektur_yaml)
    if path_yaml.suffix.lower() not in {".yaml", ".yml"}:
        raise ValueError(
            f"Pelanggaran aturan Zero Pre-Trained: file arsitektur wajib berformat .yaml, bukan {path_yaml.name}"
        )

    if not path_yaml.exists():
        raise FileNotFoundError(f"File arsitektur YOLOv8 tidak ditemukan di: {path_yaml}")

    # Menginisialisasi struktur layer YOLOv8 dengan bobot awal acak dari file YAML
    model_yolo_polos = YOLO(str(path_yaml))
    return model_yolo_polos


def ekstrak_ringkasan_metrik_training_yolo(folder_hasil_run: Path) -> dict:
    """
    Membaca file results.csv yang dihasilkan oleh proses iterasi epoch YOLOv8 untuk merangkum
    nilai loss (box_loss, cls_loss, dfl_loss) dan metrik akurasi (precision, recall, mAP50, mAP50-95).
    """
    file_csv_hasil = folder_hasil_run / "results.csv"
    ringkasan_metrik = {
        "jumlah_epoch_selesai": 0,
        "epoch_terbaik": 0,
        "map50_terbaik": 0.0,
        "map50_95_terbaik": 0.0,
        "precision_akhir": 0.0,
        "recall_akhir": 0.0,
        "train_box_loss_akhir": 0.0,
        "val_box_loss_akhir": 0.0,
    }

    if not file_csv_hasil.exists():
        return ringkasan_metrik

    with open(file_csv_hasil, "r", encoding="utf-8") as file_csv:
        pembaca_csv = list(csv.DictReader(file_csv))

    if not pembaca_csv:
        return ringkasan_metrik

    def ambil_angka(baris_dict: dict, kunci_target: str) -> float:
        for kunci_asli, nilai_str in baris_dict.items():
            if kunci_asli and kunci_asli.strip() == kunci_target:
                try:
                    return float(nilai_str.strip())
                except (ValueError, TypeError):
                    return 0.0
        return 0.0

    ringkasan_metrik["jumlah_epoch_selesai"] = len(pembaca_csv)
    baris_terakhir = pembaca_csv[-1]
    ringkasan_metrik["precision_akhir"] = round(ambil_angka(baris_terakhir, "metrics/precision(B)"), 4)
    ringkasan_metrik["recall_akhir"] = round(ambil_angka(baris_terakhir, "metrics/recall(B)"), 4)
    ringkasan_metrik["train_box_loss_akhir"] = round(ambil_angka(baris_terakhir, "train/box_loss"), 4)
    ringkasan_metrik["val_box_loss_akhir"] = round(ambil_angka(baris_terakhir, "val/box_loss"), 4)

    for indeks_baris, baris_epoch in enumerate(pembaca_csv, start=1):
        nilai_map50 = ambil_angka(baris_epoch, "metrics/mAP50(B)")
        nilai_map50_95 = ambil_angka(baris_epoch, "metrics/mAP50-95(B)")
        if nilai_map50 >= ringkasan_metrik["map50_terbaik"]:
            ringkasan_metrik["map50_terbaik"] = round(nilai_map50, 4)
            ringkasan_metrik["map50_95_terbaik"] = round(nilai_map50_95, 4)
            ringkasan_metrik["epoch_terbaik"] = int(ambil_angka(baris_epoch, "epoch")) or indeks_baris

    return ringkasan_metrik


def latih_model_yolov8_dari_nol(
    path_data_yaml: Path = konfig.FILE_KONFIGURASI_DATA_YOLO_YAML,
    path_arsitektur_yaml: Path = konfig.FILE_ARSITEKTUR_YOLOV8_YAML,
    jumlah_epoch: int = konfig.JUMLAH_EPOCH_TRAINING_YOLO,
    batas_patience: int = konfig.BATAS_PATIENCE_EARLY_STOPPING_YOLO,
    ukuran_gambar: int = konfig.UKURAN_GAMBAR_INPUT_YOLO,
    ukuran_batch: int = konfig.UKURAN_BATCH_TRAINING_YOLO,
    nama_optimizer: str = konfig.NAMA_OPTIMIZER_YOLO,
    gunakan_cosine_lr: bool = konfig.GUNAKAN_COSINE_LR_SCHEDULER_YOLO,
    laju_belajar_awal: float = konfig.LAJU_BELAJAR_AWAL_YOLO,
    laju_belajar_akhir: float = konfig.LAJU_BELAJAR_AKHIR_YOLO,
    bobot_loss_box: float = konfig.BOBOT_LOSS_KOTAK_BBOX_YOLO,
    bobot_loss_cls: float = konfig.BOBOT_LOSS_KLASIFIKASI_KELAS_YOLO,
    bobot_loss_dfl: float = konfig.BOBOT_LOSS_DFL_TEPI_KOTAK_YOLO,
    nama_folder_eksperimen: str = "run_yolov8_wajah_mandiri",
    salin_ke_bobot_utama: bool = True,
) -> dict:
    """
    Mengambil konfigurasi dataset dari data_yolo_wajah.yaml (hasil Tahap 01) dan melatih arsitektur YOLOv8 polosan
    dari Epoch 0 menggunakan GPU NVIDIA GeForce RTX 4060 (pretrained=False, amp=False) beserta parameter tuning
    optimizer, cosine learning rate, bobot loss (box, cls, dfl), dan augmentasi deteksi objek.
    Menyimpan bobot terbaik ke storage/app/ai/weights/hasil_training_yolov8_wajah.pt untuk dipakai oleh
    modul deteksi wajah pada Tahap 03 dan layanan kamera real-time pada python/yolo_service.py.
    """
    konfig.pastikan_semua_folder_tersedia()

    if not Path(path_data_yaml).exists():
        raise FileNotFoundError(
            f"File konfigurasi dataset YOLO belum ditemukan di: {path_data_yaml}\n"
            "Jalankan Tahap 01 (siapkan_dan_split_dataset_yolo) terlebih dahulu."
        )

    indeks_gpu_cuda, _, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)

    print("=" * 78)
    print("  TAHAP 02: PELATIHAN & TUNING YOLOV8 DETEKSI WAJAH DARI EPOCH 0 (NO PRE-TRAINED)")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']} ({info_perangkat_gpu['vram_gb']} GB VRAM)")
    print(f"[*] Indeks Perangkat            : CUDA:{indeks_gpu_cuda} ({info_perangkat_gpu['catatan_task_manager']})")
    print(f"[*] File Arsitektur Polosan     : {path_arsitektur_yaml}")
    print(f"[*] File Dataset YOLO           : {path_data_yaml}")
    print(f"[*] Target Epoch & Patience     : Maks {jumlah_epoch} Epoch (Early Stopping Patience = {batas_patience})")
    print(f"[*] Ukuran Gambar & Batch       : {ukuran_gambar}x{ukuran_gambar} piksel | Batch Size = {ukuran_batch}")
    print(f"[*] Optimizer & LR              : {nama_optimizer} | lr0 = {laju_belajar_awal} | Cosine LR = {gunakan_cosine_lr}")
    print(f"[*] Bobot Loss (Box/Cls/DFL)    : box={bobot_loss_box}, cls={bobot_loss_cls}, dfl={bobot_loss_dfl}")

    waktu_mulai_training = time.time()
    model_yolo_polos = muat_arsitektur_yolov8_polos(path_arsitektur_yaml)

    # Menjalankan iterasi epoch dari nol dengan seluruh parameter tuning YOLOv8 secara eksplisit
    model_yolo_polos.train(
        data=str(path_data_yaml),
        epochs=jumlah_epoch,
        patience=batas_patience,
        imgsz=ukuran_gambar,
        batch=ukuran_batch,
        device=indeks_gpu_cuda,
        workers=konfig.JUMLAH_WORKER_DATALOADER_YOLO,
        pretrained=False,
        amp=False,
        optimizer=nama_optimizer,
        cos_lr=gunakan_cosine_lr,
        lr0=laju_belajar_awal,
        lrf=laju_belajar_akhir,
        momentum=konfig.MOMENTUM_OPTIMIZER_YOLO,
        weight_decay=konfig.WEIGHT_DECAY_YOLO,
        warmup_epochs=konfig.EPOCH_PEMANASAN_YOLO,
        warmup_momentum=konfig.MOMENTUM_PEMANASAN_YOLO,
        warmup_bias_lr=konfig.BIAS_LR_PEMANASAN_YOLO,
        box=bobot_loss_box,
        cls=bobot_loss_cls,
        dfl=bobot_loss_dfl,
        hsv_h=konfig.VARIASI_HUE_WARNA_YOLO,
        hsv_s=konfig.VARIASI_SATURASI_WARNA_YOLO,
        hsv_v=konfig.VARIASI_KECERAHAN_VALUE_YOLO,
        degrees=konfig.DERAJAT_ROTASI_KEPALA_YOLO,
        translate=konfig.GESER_TRANSLASI_GAMBAR_YOLO,
        scale=konfig.SKALA_JARAK_WAJAH_YOLO,
        fliplr=konfig.PELUANG_FLIP_HORIZONTAL_YOLO,
        flipud=konfig.PELUANG_FLIP_VERTIKAL_YOLO,
        mosaic=konfig.PELUANG_AUGMENTASI_MOSAIC_YOLO,
        close_mosaic=konfig.MATIKAN_MOSAIC_N_EPOCH_TERAKHIR_YOLO,
        iou=konfig.BATAS_IOU_NMS_YOLO,
        conf=konfig.BATAS_CONFIDENCE_DETEKSI_YOLO,
        project=str(konfig.FOLDER_HASIL_RUN_YOLO),
        name=nama_folder_eksperimen,
        exist_ok=True,
        plots=True,
        save=True,
        verbose=True,
    )

    folder_output_run = konfig.FOLDER_HASIL_RUN_YOLO / nama_folder_eksperimen
    file_bobot_best = folder_output_run / "weights" / "best.pt"
    file_bobot_last = folder_output_run / "weights" / "last.pt"

    sumber_bobot_terpilih = file_bobot_best if file_bobot_best.exists() else file_bobot_last
    if not sumber_bobot_terpilih.exists():
        raise RuntimeError(
            f"Pelatihan YOLOv8 selesai tetapi file bobot tidak ditemukan di: {folder_output_run / 'weights'}"
        )

    if salin_ke_bobot_utama:
        # Menyalin bobot hasil training mandiri ke lokasi penyimpanan utama untuk dipakai Tahap 03 dan runtime web
        konfig.FILE_BOBOT_HASIL_TRAINING_YOLO.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sumber_bobot_terpilih, konfig.FILE_BOBOT_HASIL_TRAINING_YOLO)

    durasi_training_detik = round(time.time() - waktu_mulai_training, 2)
    ringkasan_metrik = ekstrak_ringkasan_metrik_training_yolo(folder_output_run)

    data_hasil_training_yolo = {
        "nama_eksperimen": nama_folder_eksperimen,
        "status_training": "berhasil",
        "pretrained_digunakan": False,
        "info_perangkat_gpu": info_perangkat_gpu,
        "path_arsitektur_yaml": str(path_arsitektur_yaml),
        "path_bobot_eksperimen": str(sumber_bobot_terpilih),
        "path_bobot_hasil_training_yolo": str(konfig.FILE_BOBOT_HASIL_TRAINING_YOLO),
        "folder_artefak_run_yolo": str(folder_output_run),
        "durasi_training_detik": durasi_training_detik,
        "parameter_tuning_yolo": {
            "jumlah_epoch_maksimal": jumlah_epoch,
            "batas_patience_early_stopping": batas_patience,
            "ukuran_gambar_input": ukuran_gambar,
            "ukuran_batch": ukuran_batch,
            "nama_optimizer": nama_optimizer,
            "gunakan_cosine_lr": gunakan_cosine_lr,
            "laju_belajar_awal": laju_belajar_awal,
            "laju_belajar_akhir": laju_belajar_akhir,
            "bobot_loss_box": bobot_loss_box,
            "bobot_loss_cls": bobot_loss_cls,
            "bobot_loss_dfl": bobot_loss_dfl,
            "derajat_rotasi": konfig.DERAJAT_ROTASI_KEPALA_YOLO,
            "skala_zoom": konfig.SKALA_JARAK_WAJAH_YOLO,
            "flip_horizontal": konfig.PELUANG_FLIP_HORIZONTAL_YOLO,
            "mosaic": konfig.PELUANG_AUGMENTASI_MOSAIC_YOLO,
        },
        "metrik_hasil_training": ringkasan_metrik,
    }

    path_laporan_json = konfig.FOLDER_HASIL_RUN_YOLO / f"ringkasan_{nama_folder_eksperimen}.json"
    path_laporan_json.write_text(json.dumps(data_hasil_training_yolo, indent=2), encoding="utf-8")

    if salin_ke_bobot_utama:
        path_utama_json = konfig.FOLDER_HASIL_RUN_YOLO / "ringkasan_hasil_training_yolo.json"
        path_utama_json.write_text(json.dumps(data_hasil_training_yolo, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("  PELATIHAN MANDIRI YOLOV8 SELESAI")
    print("=" * 78)
    print(f"[OK] Bobot terbaik disimpan ke : {konfig.FILE_BOBOT_HASIL_TRAINING_YOLO}")
    print(f"[OK] Epoch terbaik / selesai   : Epoch {ringkasan_metrik['epoch_terbaik']} dari {ringkasan_metrik['jumlah_epoch_selesai']}")
    print(f"[OK] Skor mAP50 terbaik        : {ringkasan_metrik['map50_terbaik']}")
    print(f"[OK] Skor mAP50-95 terbaik     : {ringkasan_metrik['map50_95_terbaik']}")
    print(f"[OK] Durasi pelatihan          : {durasi_training_detik} detik")

    return data_hasil_training_yolo


def jalankan_tuning_hyperparameter_yolo(
    daftar_kandidat_skenario: list[dict] = None,
    jumlah_epoch_per_skenario: int = 30,
    batas_patience: int = 10,
) -> dict:
    """
    Menjalankan eksperimen perbandingan beberapa kombinasi hyperparameter YOLOv8 (misal AdamW vs SGD, lr0, bobot loss),
    memilih skenario dengan skor mAP50-95 tertinggi, dan menyalin bobot terbaiknya ke hasil_training_yolov8_wajah.pt.
    """
    kandidat_uji = daftar_kandidat_skenario or konfig.DAFTAR_KANDIDAT_TUNING_YOLO
    daftar_hasil_skenario = []
    skenario_terbaik = None
    skor_map_tertinggi = -1.0

    for indeks_skenario, parameter_kandidat in enumerate(kandidat_uji, start=1):
        nama_skenario = parameter_kandidat.get("nama_skenario", f"skenario_tuning_{indeks_skenario}")
        print(f"\n>>> Menjalankan Kandidat Tuning #{indeks_skenario}: {nama_skenario} <<<")

        hasil_run = latih_model_yolov8_dari_nol(
            jumlah_epoch=jumlah_epoch_per_skenario,
            batas_patience=batas_patience,
            nama_optimizer=parameter_kandidat.get("optimizer", konfig.NAMA_OPTIMIZER_YOLO),
            gunakan_cosine_lr=parameter_kandidat.get("cos_lr", konfig.GUNAKAN_COSINE_LR_SCHEDULER_YOLO),
            laju_belajar_awal=parameter_kandidat.get("lr0", konfig.LAJU_BELAJAR_AWAL_YOLO),
            bobot_loss_box=parameter_kandidat.get("box", konfig.BOBOT_LOSS_KOTAK_BBOX_YOLO),
            bobot_loss_cls=parameter_kandidat.get("cls", konfig.BOBOT_LOSS_KLASIFIKASI_KELAS_YOLO),
            nama_folder_eksperimen=nama_skenario,
            salin_ke_bobot_utama=False,
        )
        daftar_hasil_skenario.append(hasil_run)

        skor_map_kandidat = hasil_run["metrik_hasil_training"]["map50_95_terbaik"]
        if skor_map_kandidat > skor_map_tertinggi:
            skor_map_tertinggi = skor_map_kandidat
            skenario_terbaik = hasil_run

    if skenario_terbaik is not None:
        shutil.copy2(skenario_terbaik["path_bobot_eksperimen"], konfig.FILE_BOBOT_HASIL_TRAINING_YOLO)

    laporan_tuning_yolo = {
        "jumlah_skenario_diuji": len(daftar_hasil_skenario),
        "skenario_terbaik": skenario_terbaik["nama_eksperimen"] if skenario_terbaik else None,
        "skor_map50_95_terbaik": skor_map_tertinggi,
        "path_bobot_terpilih": str(konfig.FILE_BOBOT_HASIL_TRAINING_YOLO),
        "daftar_hasil_skenario": daftar_hasil_skenario,
    }

    path_laporan_tuning = konfig.FOLDER_HASIL_RUN_YOLO / "laporan_tuning_hyperparameter_yolo.json"
    path_laporan_tuning.write_text(json.dumps(laporan_tuning_yolo, indent=2), encoding="utf-8")
    return laporan_tuning_yolo


def evaluasi_model_yolo_pada_split_test(
    path_bobot_yolo: Path = konfig.FILE_BOBOT_HASIL_TRAINING_YOLO,
    path_data_yaml: Path = konfig.FILE_KONFIGURASI_DATA_YOLO_YAML,
) -> dict:
    """
    Memuat file hasil_training_yolov8_wajah.pt dan menguji performanya pada split test
    untuk menghasilkan metrik evaluasi deteksi objek (Precision, Recall, mAP50, mAP50-95).
    """
    if not Path(path_bobot_yolo).exists():
        raise FileNotFoundError(
            f"Bobot hasil training YOLOv8 belum tersedia di: {path_bobot_yolo}\n"
            "Jalankan latih_model_yolov8_dari_nol() pada Tahap 02 terlebih dahulu."
        )

    indeks_gpu_cuda, _, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)
    model_yolo_terlatih = YOLO(str(path_bobot_yolo))

    hasil_validasi_test = model_yolo_terlatih.val(
        data=str(path_data_yaml),
        split="test",
        imgsz=konfig.UKURAN_GAMBAR_INPUT_YOLO,
        batch=konfig.UKURAN_BATCH_TRAINING_YOLO,
        device=indeks_gpu_cuda,
        verbose=True,
    )

    kamus_metrik = getattr(hasil_validasi_test, "results_dict", {}) or {}
    data_evaluasi_test_yolo = {
        "path_bobot_diuji": str(path_bobot_yolo),
        "perangkat_gpu": info_perangkat_gpu["nama_gpu"],
        "precision_test": round(float(kamus_metrik.get("metrics/precision(B)", 0.0)), 4),
        "recall_test": round(float(kamus_metrik.get("metrics/recall(B)", 0.0)), 4),
        "map50_test": round(float(kamus_metrik.get("metrics/mAP50(B)", 0.0)), 4),
        "map50_95_test": round(float(kamus_metrik.get("metrics/mAP50-95(B)", 0.0)), 4),
    }

    return data_evaluasi_test_yolo


if __name__ == "__main__":
    latih_model_yolov8_dari_nol()
