# hanya untuk keperluan training python local, tidak dirun di web
"""
tp_config.py — Konfigurasi bersama pipeline training IndoLens (Jupyter Notebook).

Semua path diturunkan dari PROJECT_ROOT yang dapat dikonfigurasi lewat environment
variable INDOLENS_ROOT (default: C:\\laragon\\www\\IndoLens). Modul ini TIDAK bergantung
pada __file__ agar aman dipakai dari sel Jupyter.

Override opsional (environment variable, diset SEBELUM import modul ini):
    INDOLENS_ROOT                        -> root project Laravel IndoLens
    INDOLENS_ARTIFACTS_DIR               -> folder artefak training (default: training_python/artifacts)
    INDOLENS_PRODUCTION_EMBEDDINGS_DIR   -> folder reference embedding runtime (default: python/embeddings)
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Root & path utama
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
TRAINING_DIR = PROJECT_ROOT / "training_python"
RUNTIME_PY_DIR = PROJECT_ROOT / "python"                     # kode runtime YOLO/FaceNet yang sudah ada
LARAVEL_ENV_FILE = PROJECT_ROOT / ".env"

# Root disk 'public' Laravel. Kolom actor_images.image relatif terhadap folder ini.
STORAGE_PUBLIC_ROOT = PROJECT_ROOT / "storage" / "app" / "public"

# Bobot YOLOv8-face yang dipakai runtime (python/config/config.py -> YOLO_MODEL_PATH)
YOLO_WEIGHTS = PROJECT_ROOT / "storage" / "app" / "ai" / "weights" / "yolov8n-face.pt"

# Reference data runtime (dibaca yolo_service.py lewat recognition.embedding_matcher)
PRODUCTION_EMBEDDINGS_DIR = Path(
    os.environ.get("INDOLENS_PRODUCTION_EMBEDDINGS_DIR", str(RUNTIME_PY_DIR / "embeddings"))
)
PRODUCTION_MANIFEST = PRODUCTION_EMBEDDINGS_DIR / "manifest.json"

# Artefak training (crop, tensor, embedding, laporan). BUKAN folder public web.
ARTIFACTS_DIR = Path(os.environ.get("INDOLENS_ARTIFACTS_DIR", str(TRAINING_DIR / "artifacts")))

STAGE01_DIR = ARTIFACTS_DIR / "01_ekstraksi_wajah"
STAGE01_CROPS_DIR = STAGE01_DIR / "crops"            # crops/<actor_id>/<image_id>.png
STAGE01_REJECTED_DIR = STAGE01_DIR / "rejected"      # rejected/<actor_id>/<image_id>_face<k>.png (multi-face)
STAGE01_MANIFEST = STAGE01_DIR / "extraction_manifest.json"

STAGE02_DIR = ARTIFACTS_DIR / "02_analisis_matematis"
STAGE02_REPORT_JSON = STAGE02_DIR / "analysis_report.json"
STAGE02_REPORT_TXT = STAGE02_DIR / "analysis_report.txt"

STAGE03_DIR = ARTIFACTS_DIR / "03_preprocessing_wajah"
STAGE03_TENSORS_DIR = STAGE03_DIR / "tensors"        # tensors/<actor_id>/<image_id>.npy  (160x160x3 float32)
STAGE03_PREVIEWS_DIR = STAGE03_DIR / "previews"      # previews/<actor_id>/<image_id>.png (160x160 RGB uint8)
STAGE03_MANIFEST = STAGE03_DIR / "preprocess_manifest.json"

STAGE04_DIR = ARTIFACTS_DIR / "04_pembuatan_embedding"
STAGE04_VECTORS_DIR = STAGE04_DIR / "vectors"        # vectors/<actor_id>/<image_id>.npy  (128,) float32
STAGE04_MANIFEST = STAGE04_DIR / "embedding_manifest.json"

STAGE05_DIR = ARTIFACTS_DIR / "05_validasi_embedding"
STAGE05_REPORT_JSON = STAGE05_DIR / "validation_report.json"
STAGE05_VALID_LIST = STAGE05_DIR / "valid_embeddings.json"
STAGE05_DISTANCE_MATRIX = STAGE05_DIR / "distance_matrix.npy"
STAGE05_DISTANCE_INDEX = STAGE05_DIR / "distance_index.csv"
STAGE05_FLAGGED_PAIRS = STAGE05_DIR / "flagged_pairs.csv"
STAGE05_PER_EMBEDDING = STAGE05_DIR / "per_embedding_stats.csv"

STAGE06_DIR = ARTIFACTS_DIR / "06_integrasi_reference_data"
STAGE06_STAGING_DIR = STAGE06_DIR / "staging"
STAGE06_BACKUP_DIR = STAGE06_DIR / "backups"
STAGE06_REPORT_JSON = STAGE06_DIR / "integration_report.json"

STAGE07_DIR = ARTIFACTS_DIR / "07_evaluasi_dataset"
STAGE07_REPORT_JSON = STAGE07_DIR / "evaluation_report.json"
STAGE07_REPORT_TXT = STAGE07_DIR / "evaluation_report.txt"
STAGE07_PROBE_CSV = STAGE07_DIR / "probe_predictions.csv"

# Set evaluasi independen OPSIONAL (diisi manual oleh peneliti, lihat README).
PROBE_SET_DIR = TRAINING_DIR / "probe_set"

# ---------------------------------------------------------------------------
# 2. Metodologi skripsi & Konfigurasi Embedding
# ---------------------------------------------------------------------------
# Mode dimensi embedding utama: 512-D (Native Inception-ResNet-v1 VGGFace2 untuk akurasi tertinggi)
# Pipeline secara otomatis juga mengekstrak versi 128-D untuk uji komparasi ilmiah (Bahan Sidang Skripsi).
PRIMARY_EMBEDDING_DIM = 512
COMPARISON_EMBEDDING_DIM = 128
EMBEDDING_DIM = PRIMARY_EMBEDDING_DIM

FACENET_INPUT_SIZE = (160, 160)
UNKNOWN_LABEL = "Unknown"
L2_NORM_TOLERANCE = 1e-4              # toleransi |‖v‖₂ − 1|

# Kalibrasi Threshold Keputusan (Decision Boundary):
# DYNAMIC_THRESHOLD_SEARCH: True -> threshold dicari secara empiris dari distribusi data (EER / ROC)
# RECOGNITION_THRESHOLD: fallback awal jika pasangan inter-class belum cukup (< 2 aktor)
DYNAMIC_THRESHOLD_SEARCH = True
DEFAULT_FALLBACK_THRESHOLD = 0.65
RECOGNITION_THRESHOLD = DEFAULT_FALLBACK_THRESHOLD

# Path artefak tambahan untuk komparasi ilmiah & threshold terkalibrasi
STAGE04_VECTORS_512_DIR = STAGE04_DIR / "vectors_512"
STAGE04_VECTORS_128_DIR = STAGE04_DIR / "vectors_128"
STAGE05_OPTIMAL_THRESHOLD_JSON = STAGE05_DIR / "optimal_threshold.json"
STAGE05_DIM_COMPARISON_CSV = STAGE05_DIR / "dimension_comparison.csv"
STAGE05_ROC_CURVE_CSV = STAGE05_DIR / "roc_curve_data.csv"

# ---------------------------------------------------------------------------
# 3. Parameter pemrosesan & Augmentasi Training
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp"}
DEFAULT_CHECKPOINT_EVERY = 10         # simpan manifest setiap N gambar
NEAR_DUPLICATE_HAMMING = 5            # analisis saja: jarak Hamming dHash 64-bit <= nilai ini dilaporkan
SERVICE_URL = os.environ.get("INDOLENS_SERVICE_URL", "http://127.0.0.1:8002")

# Augmentasi training: memperkaya variasi wajah (rotasi halus, flip, ekspresi, pencahayaan film)
# agar proses training benar-benar berbobot dan melatih representasi yang tangguh terhadap scene film.
ENABLE_TRAINING_AUGMENTATION = True
AUGMENTATION_PASSES_PER_IMAGE = 3     # 1 original + 3 variasi terarah (flip, rotasi +-6 deg, brightness jitter)


def stage_dirs():
    """Semua folder artefak yang dibuat oleh pipeline."""
    return [
        STAGE01_CROPS_DIR, STAGE01_REJECTED_DIR,
        STAGE02_DIR,
        STAGE03_TENSORS_DIR, STAGE03_PREVIEWS_DIR,
        STAGE04_VECTORS_DIR, STAGE04_VECTORS_512_DIR, STAGE04_VECTORS_128_DIR,
        STAGE05_DIR,
        STAGE06_STAGING_DIR, STAGE06_BACKUP_DIR,
        STAGE07_DIR,
    ]


def ensure_artifact_dirs():
    for d in stage_dirs():
        d.mkdir(parents=True, exist_ok=True)


def validate_paths(require_yolo=True):
    """
    Pastikan path wajib benar-benar ada. Melempar RuntimeError berisi daftar masalah
    agar kegagalan konfigurasi tidak tersembunyi.
    """
    problems = []
    checks = [
        ("PROJECT_ROOT", PROJECT_ROOT, True),
        ("RUNTIME_PY_DIR (python/)", RUNTIME_PY_DIR, True),
        ("STORAGE_PUBLIC_ROOT", STORAGE_PUBLIC_ROOT, True),
        ("Laravel .env", LARAVEL_ENV_FILE, False),
    ]
    if require_yolo:
        checks.append(("YOLO_WEIGHTS", YOLO_WEIGHTS, True))
    for label, path, required in checks:
        if not path.exists():
            if required:
                problems.append(f"{label} tidak ditemukan: {path}")
            else:
                print(f"[INFO] {label} tidak ditemukan ({path}); kredensial DB harus lewat environment variable.")
    for sub in ("yolo", "facenet", "utils", "config", "recognition"):
        if not (RUNTIME_PY_DIR / sub).is_dir():
            problems.append(f"Modul runtime python/{sub} tidak ditemukan di {RUNTIME_PY_DIR}")
    if problems:
        raise RuntimeError("Konfigurasi path tidak valid:\n  - " + "\n  - ".join(problems))
    return True


def describe():
    """Ringkasan konfigurasi (tanpa kredensial)."""
    return {
        "PROJECT_ROOT": str(PROJECT_ROOT),
        "STORAGE_PUBLIC_ROOT": str(STORAGE_PUBLIC_ROOT),
        "YOLO_WEIGHTS": str(YOLO_WEIGHTS),
        "PRODUCTION_EMBEDDINGS_DIR": str(PRODUCTION_EMBEDDINGS_DIR),
        "ARTIFACTS_DIR": str(ARTIFACTS_DIR),
        "EMBEDDING_DIM": EMBEDDING_DIM,
        "FACENET_INPUT_SIZE": FACENET_INPUT_SIZE,
        "RECOGNITION_THRESHOLD": RECOGNITION_THRESHOLD,
    }
