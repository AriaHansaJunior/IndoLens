import sys
from pathlib import Path
import cv2

BASE_DIR = Path("python").resolve()
sys.path.insert(0, str(BASE_DIR))

from yolo.detector import load_model, predict_frame
from facenet.embedding_generator import load_facenet_model, generate_embedding

load_model()
load_facenet_model()

img_dir = Path("storage/app/public/actor-images/1-bayu-skak")
for img_path in sorted(img_dir.glob("*.jpg")):
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"{img_path.name}: Failed to read image")
        continue
    dets = predict_frame(img)
    if not dets:
        print(f"{img_path.name}: NO FACE DETECTED (dets={dets})")
    else:
        best = max(dets, key=lambda d: d.get("confidence", 0))
        crop = best.get("crop")
        conf = best.get("confidence", 0)
        crop_shape = crop.shape if crop is not None else None
        emb = generate_embedding(crop) if crop is not None else None
        print(f"{img_path.name}: {len(dets)} face(s), best conf={conf:.4f}, crop={crop_shape}, emb_dim={len(emb) if emb is not None else 0}")
