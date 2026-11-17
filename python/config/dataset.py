from pathlib import Path

# Menentukan direktori dasar modul python dan lokasi penyimpanan dataset serta embedding referensi
BASE_DIR = Path(__file__).resolve().parent.parent
FOLDER_DATASET_UTAMA = BASE_DIR / "datasets"
FOLDER_DATASET_YOLO_WAJAH = FOLDER_DATASET_UTAMA / "dataset_yolo_wajah"
FOLDER_DATASET_FACENET_AKTOR = FOLDER_DATASET_UTAMA / "dataset_facenet_aktor"
DATASET_PATH = FOLDER_DATASET_FACENET_AKTOR / "wajah_aktor_target"
EMBEDDING_PATH = BASE_DIR / "embeddings"

# Mendefinisikan ekstensi file gambar yang didukung oleh pipeline pemrosesan
SUPPORTED_EXTENSION = ["jpg", "jpeg", "png", "webp", "avif"]

# Menetapkan ukuran resolusi input wajah menjadi 160x160 piksel dengan 3 alasan teknis:
# 1. Geometri area kotak wajah manusia (dahi ke dagu, telinga kiri ke kanan) mendekati rasio persegi 1:1.
# 2. Pada jaringan CNN FaceNet dengan 5 tahap reduksi spasial (stride 2 / pooling):
#    160x160 -> 80x80 -> 40x40 -> 20x20 -> 10x10 -> 5x5.
#    Ukuran peta fitur akhir 5x5 pas untuk menjaga tata letak spasial mata, hidung, dan mulut sebelum masuk ke Global Average Pooling.
# 3. Menjaga titik keseimbangan antara ketajaman detail biometrik wajah (tidak pecah seperti 64x64)
#    dan kecepatan inferensi kamera real-time (tidak membebani GPU seperti ukuran 224x224 atau 512x512).
UKURAN_RESOLUSI_WAJAH_FACENET = (160, 160)
IMAGE_SIZE = UKURAN_RESOLUSI_WAJAH_FACENET
MINIMUM_IMAGES = 1

# Menetapkan dimensi vektor embedding 512-D dan batas ambang jarak Euclidean (threshold)
DIMENSI_EMBEDDING_FACENET = 512
FACENET_EMBEDDING_DIM = DIMENSI_EMBEDDING_FACENET
BATAS_AMBANG_JARAK_EUCLIDEAN = 0.85
FACE_DISTANCE_THRESHOLD = BATAS_AMBANG_JARAK_EUCLIDEAN
