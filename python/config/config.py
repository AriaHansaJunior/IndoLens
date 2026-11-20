import os
from pathlib import Path

from config.dataset import (
    DIMENSI_EMBEDDING_FACENET,
    FACENET_EMBEDDING_DIM,
    BATAS_AMBANG_JARAK_EUCLIDEAN,
    FACE_DISTANCE_THRESHOLD,
    UKURAN_RESOLUSI_WAJAH_FACENET,
    IMAGE_SIZE,
)

# Menentukan path absolut direktori modul python dan root proyek IndoLens
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# Menentukan lokasi folder penyimpanan bobot model, log, dan hasil pemrosesan di storage/app/ai
STORAGE_AI_DIR = PROJECT_ROOT / "storage" / "app" / "ai"
VIDEOS_DIR = STORAGE_AI_DIR / "videos"
OUTPUTS_DIR = STORAGE_AI_DIR / "outputs"
EMBEDDINGS_DIR = STORAGE_AI_DIR / "embeddings"
LOGS_DIR = STORAGE_AI_DIR / "logs"
CACHE_DIR = STORAGE_AI_DIR / "cache"
TEMP_DIR = STORAGE_AI_DIR / "temp"
WEIGHTS_DIR = STORAGE_AI_DIR / "weights"

# Menentukan lokasi folder publik untuk akses file dari antarmuka web Laravel
PUBLIC_DIR = PROJECT_ROOT / "public"
UPLOADS_DIR = PUBLIC_DIR / "uploads"
RESULTS_DIR = PUBLIC_DIR / "results"

# Menentukan lokasi file konfigurasi arsitektur YOLOv8 dan lokasi file bobot hasil training
FILE_ARSITEKTUR_YOLOV8_WAJAH = BASE_DIR / "config" / "arsitektur_yolov8_wajah.yaml"
FILE_BOBOT_HASIL_TRAINING_YOLO = WEIGHTS_DIR / "hasil_training_yolov8_wajah.pt"
FILE_BOBOT_HASIL_TRAINING_FACENET = WEIGHTS_DIR / "hasil_training_facenet_aktor.pth"

# Menyediakan alias kompatibilitas untuk modul detektor dan service runtime
YOLO_MODEL_PATH = FILE_BOBOT_HASIL_TRAINING_YOLO
YOLO_FALLBACK_MODEL = None

# Mengatur parameter deteksi wajah YOLOv8 saat inferensi kamera dan ekstraksi dataset
FRAME_SAMPLE_RATE = int(os.getenv("FRAME_SAMPLE_RATE", 3))
BATAS_CONFIDENCE_DETEKSI_YOLO = float(os.getenv("YOLO_CONFIDENCE", 0.45))
YOLO_CONFIDENCE = BATAS_CONFIDENCE_DETEKSI_YOLO
MIN_FACE_CONFIDENCE = float(os.getenv("MIN_FACE_CONFIDENCE", 0.45))
BATAS_IOU_NMS_YOLO = float(os.getenv("YOLO_IOU", 0.45))
YOLO_IOU = BATAS_IOU_NMS_YOLO
UKURAN_GAMBAR_INFERENSI_YOLO = int(os.getenv("YOLO_IMAGE_SIZE", 480))
YOLO_IMAGE_SIZE = UKURAN_GAMBAR_INFERENSI_YOLO
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "0")
