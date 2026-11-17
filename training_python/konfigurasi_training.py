"""Konfigurasi terpusat path absolut, perangkat GPU RTX 4060, dan parameter training mandiri IndoLens."""

import os
from pathlib import Path
import torch

# Menentukan path absolut root proyek IndoLens agar selalu terbaca dari Jupyter Notebook lokal
FOLDER_ROOT_PROYEK = Path(os.environ.get("INDOLENS_ROOT", str(Path(__file__).resolve().parent.parent)))
FOLDER_MODUL_PYTHON = FOLDER_ROOT_PROYEK / "python"
FOLDER_MODUL_TRAINING = FOLDER_ROOT_PROYEK / "training_python"
FILE_ENV_LARAVEL = FOLDER_ROOT_PROYEK / ".env"

# Menentukan lokasi penyimpanan foto aktor yang diunggah melalui halaman web Camp Laravel
FOLDER_STORAGE_ACTOR_IMAGES_LARAVEL = FOLDER_ROOT_PROYEK / "storage" / "app" / "public" / "actor-images"

# Menentukan lokasi konfigurasi arsitektur YOLOv8 polosan dan lokasi penyimpanan bobot hasil training mandiri
FOLDER_BOBOT_MODEL_AI = FOLDER_ROOT_PROYEK / "storage" / "app" / "ai" / "weights"
FILE_ARSITEKTUR_YOLOV8_YAML = FOLDER_MODUL_PYTHON / "config" / "arsitektur_yolov8_wajah.yaml"
FILE_BOBOT_HASIL_TRAINING_YOLO = FOLDER_BOBOT_MODEL_AI / "hasil_training_yolov8_wajah.pt"
FILE_BOBOT_HASIL_TRAINING_FACENET = FOLDER_BOBOT_MODEL_AI / "hasil_training_facenet_aktor.pth"

# Menentukan lokasi struktur folder dataset deteksi wajah YOLOv8 (Tahap 01 & Tahap 02)
FOLDER_DATASET_UTAMA = FOLDER_MODUL_PYTHON / "datasets"
FOLDER_DATASET_YOLO_WAJAH = FOLDER_DATASET_UTAMA / "dataset_yolo_wajah"
FOLDER_RAW_WAJAH_MANUSIA = FOLDER_DATASET_YOLO_WAJAH / "raw_wajah_manusia"
FOLDER_RAW_NEGATIF_BUKAN_WAJAH = FOLDER_DATASET_YOLO_WAJAH / "raw_negatif_bukan_wajah"
FOLDER_SPLIT_YOLO = FOLDER_DATASET_YOLO_WAJAH / "split_yolo"
FILE_KONFIGURASI_DATA_YOLO_YAML = FOLDER_SPLIT_YOLO / "data_yolo_wajah.yaml"

# Menentukan lokasi struktur folder dataset pengenalan aktor FaceNet dan Triplet Loss (Tahap 03 s/d Tahap 06)
FOLDER_DATASET_FACENET_AKTOR = FOLDER_DATASET_UTAMA / "dataset_facenet_aktor"
FOLDER_WAJAH_AKTOR_TARGET = FOLDER_DATASET_FACENET_AKTOR / "wajah_aktor_target"
FOLDER_WAJAH_ORANG_RANDOM = FOLDER_DATASET_FACENET_AKTOR / "wajah_orang_random"
FOLDER_CROP_WAJAH_160X160 = FOLDER_DATASET_FACENET_AKTOR / "crop_wajah_160x160"

# Menentukan lokasi artefak log training dan lokasi penyimpanan embedding produksi untuk runtime web
FOLDER_ARTEFAK_TRAINING = FOLDER_MODUL_TRAINING / "artefak_hasil_training"
FOLDER_HASIL_RUN_YOLO = FOLDER_ARTEFAK_TRAINING / "01_hasil_training_yolo_wajah"
FOLDER_HASIL_PREPROCESSING_WAJAH = FOLDER_ARTEFAK_TRAINING / "02_hasil_preprocessing_wajah"
FOLDER_HASIL_TRAINING_FACENET = FOLDER_ARTEFAK_TRAINING / "03_hasil_training_facenet_triplet"
FOLDER_HASIL_EVALUASI_METRIK = FOLDER_ARTEFAK_TRAINING / "04_hasil_evaluasi_dan_matrix_score"

FOLDER_EMBEDDING_PRODUKSI = FOLDER_MODUL_PYTHON / "embeddings"
FILE_MANIFEST_EMBEDDING_PRODUKSI = FOLDER_EMBEDDING_PRODUKSI / "manifest.json"

# Mendefinisikan ekstensi file gambar yang didukung di seluruh tahapan dataset
DAFTAR_EKSTENSI_GAMBAR_VALID = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp"}

# Mengatur proporsi pembagian dataset YOLOv8 menjadi data latih (train), validasi (val), dan uji (test)
RASIO_SPLIT_TRAIN_YOLO = 0.80
RASIO_SPLIT_VAL_YOLO = 0.10
RASIO_SPLIT_TEST_YOLO = 0.10
NILAI_SEED_ACAK = 42

# Mengatur hyperparameter pelatihan dan tuning YOLOv8 dari Epoch 0 secara proporsional dengan Early Stopping (patience)
JUMLAH_EPOCH_TRAINING_YOLO = 80
BATAS_PATIENCE_EARLY_STOPPING_YOLO = 15
UKURAN_GAMBAR_INPUT_YOLO = 640
UKURAN_BATCH_TRAINING_YOLO = 16
JUMLAH_WORKER_DATALOADER_YOLO = 2

# Mengatur parameter Optimizer dan Cosine Learning Rate Scheduler untuk konvergensi bobot YOLOv8
NAMA_OPTIMIZER_YOLO = "AdamW"
GUNAKAN_COSINE_LR_SCHEDULER_YOLO = True
LAJU_BELAJAR_AWAL_YOLO = 0.001
LAJU_BELAJAR_AKHIR_YOLO = 0.01
MOMENTUM_OPTIMIZER_YOLO = 0.937
WEIGHT_DECAY_YOLO = 0.0005
EPOCH_PEMANASAN_YOLO = 3.0
MOMENTUM_PEMANASAN_YOLO = 0.80
BIAS_LR_PEMANASAN_YOLO = 0.10

# Mengatur bobot komponen fungsi Loss YOLOv8 (Box IoU Loss, Classification Loss, dan Distribution Focal Loss)
BOBOT_LOSS_KOTAK_BBOX_YOLO = 7.5
BOBOT_LOSS_KLASIFIKASI_KELAS_YOLO = 0.5
BOBOT_LOSS_DFL_TEPI_KOTAK_YOLO = 1.5

# Mengatur parameter tuning augmentasi geometris dan pencahayaan selama training YOLOv8
VARIASI_HUE_WARNA_YOLO = 0.015
VARIASI_SATURASI_WARNA_YOLO = 0.70
VARIASI_KECERAHAN_VALUE_YOLO = 0.40
DERAJAT_ROTASI_KEPALA_YOLO = 10.0
GESER_TRANSLASI_GAMBAR_YOLO = 0.10
SKALA_JARAK_WAJAH_YOLO = 0.50
PELUANG_FLIP_HORIZONTAL_YOLO = 0.50
PELUANG_FLIP_VERTIKAL_YOLO = 0.0
PELUANG_AUGMENTASI_MOSAIC_YOLO = 1.0
MATIKAN_MOSAIC_N_EPOCH_TERAKHIR_YOLO = 10

# Mengatur ambang batas inferensi deteksi kotak wajah YOLOv8 dan Non-Maximum Suppression (NMS)
BATAS_CONFIDENCE_DETEKSI_YOLO = 0.45
BATAS_IOU_NMS_YOLO = 0.45

# Menyediakan daftar kandidat skenario untuk eksperimen tuning hyperparameter YOLOv8 di Jupyter Notebook
DAFTAR_KANDIDAT_TUNING_YOLO = [
    {
        "nama_skenario": "skenario_1_adamw_cosine_lr_001",
        "optimizer": "AdamW",
        "lr0": 0.001,
        "cos_lr": True,
        "box": 7.5,
        "cls": 0.5,
    },
    {
        "nama_skenario": "skenario_2_sgd_cosine_lr_01",
        "optimizer": "SGD",
        "lr0": 0.01,
        "cos_lr": True,
        "box": 7.5,
        "cls": 0.5,
    },
]

# Menetapkan resolusi input wajah FaceNet sebesar 160x160 piksel berdasarkan 3 alasan teknis:
# 1. Rasio geometri kotak pembatas wajah manusia (dahi ke dagu, telinga kiri ke kanan) mendekati persegi 1:1.
# 2. Pada arsitektur CNN FaceNet dengan 5 tahap penyusutan spasial (stride 2 / pooling):
#    160x160 -> 80x80 -> 40x40 -> 20x20 -> 10x10 -> 5x5.
#    Peta fitur akhir berukuran 5x5 menyimpan posisi spasial mata kiri, mata kanan, hidung, dan mulut secara optimal
#    sebelum dirangkum oleh Global Average Pooling ke vektor 512-D.
# 3. Menjaga keseimbangan antara ketajaman fitur biometrik wajah (tidak pecah seperti 64x64)
#    dan kecepatan inferensi kamera real-time (tidak membebani memori GPU seperti 224x224 atau 512x512).
UKURAN_RESOLUSI_WAJAH_FACENET = (160, 160)
RASIO_MARGIN_CROP_WAJAH = 0.12

# Mengatur hyperparameter pelatihan FaceNet & Triplet Loss dari Epoch 0 beserta Early Stopping
DIMENSI_VEKTOR_EMBEDDING_FACENET = 512
BATAS_MARGIN_TRIPLET_LOSS = 0.50
JUMLAH_EPOCH_TRAINING_FACENET = 60
BATAS_PATIENCE_EARLY_STOPPING_FACENET = 12
UKURAN_BATCH_TRIPLET_FACENET = 16
LAJU_BELAJAR_AWAL_FACENET = 0.0005
WEIGHT_DECAY_FACENET = 0.0001
BATAS_AMBANG_JARAK_AWAL = 0.85
LABEL_WAJAH_TIDAK_DIKENALI = "Unknown"


def pastikan_semua_folder_tersedia():
    """Membuat seluruh folder dataset, bobot, dan artefak training jika belum tersedia di penyimpanan lokal."""
    daftar_folder = [
        FOLDER_BOBOT_MODEL_AI,
        FOLDER_RAW_WAJAH_MANUSIA,
        FOLDER_RAW_NEGATIF_BUKAN_WAJAH,
        FOLDER_SPLIT_YOLO,
        FOLDER_WAJAH_AKTOR_TARGET,
        FOLDER_WAJAH_ORANG_RANDOM,
        FOLDER_CROP_WAJAH_160X160,
        FOLDER_HASIL_RUN_YOLO,
        FOLDER_HASIL_PREPROCESSING_WAJAH,
        FOLDER_HASIL_TRAINING_FACENET,
        FOLDER_HASIL_EVALUASI_METRIK,
        FOLDER_EMBEDDING_PRODUKSI,
    ]
    for folder_target in daftar_folder:
        folder_target.mkdir(parents=True, exist_ok=True)


def pilih_perangkat_gpu_rtx_wajib(wajib_cuda: bool = True):
    """
    Memindai dan mengunci penggunaan GPU NVIDIA GeForce RTX 4060 Laptop GPU untuk proses training.
    Pada Windows Task Manager, RTX 4060 tampil sebagai GPU 1 karena GPU 0 adalah Intel UHD Graphics (non-CUDA).
    Pada PyTorch CUDA, sistem hanya menghitung GPU NVIDIA sehingga RTX 4060 terindeks sebagai cuda:0 (indeks 0).
    Fungsi ini memverifikasi nama perangkat secara langsung agar komputasi tidak jatuh ke CPU atau iGPU.
    """
    if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
        if wajib_cuda:
            raise RuntimeError(
                "GPU NVIDIA CUDA tidak terdeteksi oleh PyTorch. "
                "Pastikan driver NVIDIA GeForce RTX 4060 aktif dan PyTorch versi CUDA terpasang."
            )
        return "cpu", torch.device("cpu"), {"nama_gpu": "CPU", "vram_gb": 0.0, "indeks_cuda": None}

    indeks_gpu_terpilih = 0
    for indeks_uji in range(torch.cuda.device_count()):
        nama_perangkat_uji = torch.cuda.get_device_name(indeks_uji)
        if "RTX" in nama_perangkat_uji.upper() or "NVIDIA" in nama_perangkat_uji.upper():
            indeks_gpu_terpilih = indeks_uji
            break

    torch.cuda.set_device(indeks_gpu_terpilih)
    properti_gpu = torch.cuda.get_device_properties(indeks_gpu_terpilih)
    nama_gpu_resmi = torch.cuda.get_device_name(indeks_gpu_terpilih)
    kapasitas_vram_gb = round(properti_gpu.total_memory / (1024 ** 3), 2)

    objek_device_pytorch = torch.device(f"cuda:{indeks_gpu_terpilih}")
    info_perangkat_gpu = {
        "indeks_cuda": indeks_gpu_terpilih,
        "device_pytorch": str(objek_device_pytorch),
        "nama_gpu": nama_gpu_resmi,
        "vram_gb": kapasitas_vram_gb,
        "catatan_task_manager": "Tampil sebagai GPU 1 di Windows Task Manager (GPU 0 adalah Intel UHD Graphics)",
    }

    return indeks_gpu_terpilih, objek_device_pytorch, info_perangkat_gpu
