import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# AI Storage paths
STORAGE_AI_DIR = PROJECT_ROOT / "storage" / "app" / "ai"
VIDEOS_DIR = STORAGE_AI_DIR / "videos"
OUTPUTS_DIR = STORAGE_AI_DIR / "outputs"
EMBEDDINGS_DIR = STORAGE_AI_DIR / "embeddings"
LOGS_DIR = STORAGE_AI_DIR / "logs"
CACHE_DIR = STORAGE_AI_DIR / "cache"
TEMP_DIR = STORAGE_AI_DIR / "temp"
WEIGHTS_DIR = STORAGE_AI_DIR / "weights"

# Public paths
PUBLIC_DIR = PROJECT_ROOT / "public"
UPLOADS_DIR = PUBLIC_DIR / "uploads"
RESULTS_DIR = PUBLIC_DIR / "results"

# Recognition settings
FACENET_EMBEDDING_DIM = 128
FACE_DISTANCE_THRESHOLD = 0.6
