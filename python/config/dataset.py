from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "datasets" / "actors"
EMBEDDING_PATH = BASE_DIR / "embeddings"

# Dataset constraints & options
SUPPORTED_EXTENSION = ["jpg", "jpeg", "png"]
IMAGE_SIZE = (160, 160)
MINIMUM_IMAGES = 1

# FaceNet Model & Recognition parameters
FACENET_EMBEDDING_DIM = 128
FACE_DISTANCE_THRESHOLD = 0.6
