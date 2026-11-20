"""Konfigurasi terpusat path absolut, perangkat GPU RTX 4060, dan parameter training IndoLens."""

import os
import sys
from pathlib import Path
import torch

# Menentukan path absolut root proyek IndoLens agar selalu terbaca dari Jupyter Notebook lokal
FOLDER_ROOT_PROYEK = Path(os.environ.get("INDOLENS_ROOT", str(Path(__file__).resolve().parent.parent)))
FOLDER_MODUL_PYTHON = FOLDER_ROOT_PROYEK / "python"
FOLDER_MODUL_TRAINING = FOLDER_ROOT_PROYEK / "training_python"
FILE_ENV_LARAVEL = FOLDER_ROOT_PROYEK / ".env"

# Menentukan lokasi penyimpanan foto aktor yang diunggah melalui halaman web Camp Laravel
FOLDER_STORAGE_ACTOR_IMAGES_LARAVEL = FOLDER_ROOT_PROYEK / "storage" / "app" / "public" / "actor-images"

# Menentukan lokasi konfigurasi arsitektur YOLOv8 dan lokasi penyimpanan bobot hasil training
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
UKURAN_BATCH_TRAINING_YOLO = 8
JUMLAH_WORKER_DATALOADER_YOLO = 0

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
RASIO_MARGIN_CROP_WAJAH = 0.04

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


def _atur_mininterval_kelas_tqdm(kelas_tqdm, interval_progress_detik: float) -> bool:
    """
    Membatasi frekuensi pembaruan progress bar pada kelas TQDM target agar
    aliran pesan IOPub Jupyter tetap ringan tanpa membuang log ringkasan epoch.
    """
    if kelas_tqdm is None:
        return False

    kelas_tqdm._interval_minimal_notebook_unlimited = float(interval_progress_detik)
    if getattr(kelas_tqdm, "_sudah_diatur_notebook_unlimited", False):
        return True

    init_asli_tqdm = kelas_tqdm.__init__

    def init_tqdm_dengan_batas_interval(self, *args, **kwargs):
        # Mengambil batas interval terbaru dari atribut kelas lalu menerapkannya setelah inisialisasi
        batas_interval = float(getattr(kelas_tqdm, "_interval_minimal_notebook_unlimited", 1.5))
        if "mininterval" in kwargs and kwargs["mininterval"] is not None:
            kwargs["mininterval"] = max(float(kwargs["mininterval"]), batas_interval)
        init_asli_tqdm(self, *args, **kwargs)
        if hasattr(self, "mininterval"):
            self.mininterval = max(
                float(getattr(self, "mininterval", 0.1) or 0.1),
                batas_interval,
            )

    kelas_tqdm.__init__ = init_tqdm_dengan_batas_interval
    kelas_tqdm._sudah_diatur_notebook_unlimited = True
    return True


def aktifkan_output_notebook_unlimited(
    interval_progress_detik: float = 1.5,
    interval_flush_detik: float = 0.5,
) -> dict:
    """
    Mengatur aliran stdout/stderr Jupyter dan progress bar training agar sel
    dengan ribuan baris epoch tidak terkena IOPub message rate exceeded.
    """
    os.environ["TQDM_MININTERVAL"] = str(float(interval_progress_detik))

    berjalan_di_notebook = "ipykernel" in sys.modules
    jumlah_stream_diatur = 0
    for aliran_output in (sys.stdout, sys.stderr):
        if aliran_output is not None and hasattr(aliran_output, "flush_interval"):
            berjalan_di_notebook = True
            aliran_output.flush_interval = max(
                float(getattr(aliran_output, "flush_interval", 0.2) or 0.2),
                float(interval_flush_detik),
            )
            jumlah_stream_diatur += 1

    ultralytics_tqdm_diatur = False
    if berjalan_di_notebook or "ultralytics" in sys.modules or "ultralytics.utils" in sys.modules:
        try:
            import ultralytics.utils as utilitas_ultralytics

            ultralytics_tqdm_diatur = _atur_mininterval_kelas_tqdm(
                getattr(utilitas_ultralytics, "TQDM", None),
                interval_progress_detik,
            )
        except Exception:
            ultralytics_tqdm_diatur = False

    tqdm_standar_diatur = False
    if berjalan_di_notebook or "tqdm" in sys.modules or "tqdm.std" in sys.modules:
        try:
            import tqdm.std as modul_tqdm_standar

            tqdm_standar_diatur = _atur_mininterval_kelas_tqdm(
                getattr(modul_tqdm_standar, "tqdm", None),
                interval_progress_detik,
            )
        except Exception:
            tqdm_standar_diatur = False

    konfig_server_siap = False
    path_konfig_server_jupyter = Path.home() / ".jupyter" / "jupyter_server_config.py"
    baris_konfig_iopub_unlimited = (
        "c.ZMQChannelsWebsocketConnection.iopub_data_rate_limit = 0",
        "c.ZMQChannelsWebsocketConnection.iopub_msg_rate_limit = 0",
        "c.ZMQChannelsWebsocketConnection.limit_rate = False",
    )
    try:
        isi_konfig_saat_ini = (
            path_konfig_server_jupyter.read_text(encoding="utf-8")
            if path_konfig_server_jupyter.exists()
            else ""
        )
        baris_belum_tertulis = [
            baris for baris in baris_konfig_iopub_unlimited if baris not in isi_konfig_saat_ini
        ]
        if not baris_belum_tertulis:
            konfig_server_siap = True
        else:
            path_konfig_server_jupyter.parent.mkdir(parents=True, exist_ok=True)
            tambahan_konfig = (
                "\n# Konfigurasi output unlimited otomatis untuk logging epoch IndoLens\n"
                + "\n".join(baris_belum_tertulis)
                + "\n"
            )
            path_konfig_server_jupyter.write_text(
                isi_konfig_saat_ini + tambahan_konfig,
                encoding="utf-8",
            )
            konfig_server_siap = True
    except Exception:
        konfig_server_siap = False

    return {
        "berjalan_di_notebook": berjalan_di_notebook,
        "jumlah_stream_diatur": jumlah_stream_diatur,
        "interval_flush_detik": float(interval_flush_detik),
        "interval_progress_detik": float(interval_progress_detik),
        "ultralytics_tqdm_diatur": ultralytics_tqdm_diatur,
        "tqdm_standar_diatur": tqdm_standar_diatur,
        "konfig_server_jupyter_unlimited": konfig_server_siap,
    }


# Mengaktifkan pengaturan output notebook unlimited secara otomatis saat modul konfigurasi dimuat
aktifkan_output_notebook_unlimited()
