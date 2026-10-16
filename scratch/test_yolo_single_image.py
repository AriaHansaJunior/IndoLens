import sys
from pathlib import Path
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(r"C:\laragon\www\IndoLens")
for p in [PROJECT_ROOT, PROJECT_ROOT / "training_python", PROJECT_ROOT / "python"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from training_python import tp_config as cfg
from training_python import tp_database as db
from training_python.tp_dataset_loader import resolve_image_path, load_image_bgr

from ultralytics import YOLO

def test_single_yolo():
    print("Testing YOLOv8 Face on first actual MySQL record...")
    records = db.fetch_actor_image_records()
    if not records:
        print("[FAIL] No records found.")
        return
    
    first_rec = records[0]
    print(f"Record: Image ID {first_rec['image_id']} | Actor: {first_rec['full_name']}")
    print(f"Path: {first_rec['relative_image_path']}")
    
    img_path, err = resolve_image_path(first_rec["relative_image_path"])
    if err:
        print(f"[FAIL] Path resolution error: {err}")
        return
        
    img_bgr, r_err = load_image_bgr(img_path)
    if r_err:
        print(f"[FAIL] Load error: {r_err}")
        return
        
    print(f"Loaded image size: {img_bgr.shape}")
    
    # Load YOLO
    print(f"Weights path: {cfg.YOLO_WEIGHTS} (exists={cfg.YOLO_WEIGHTS.exists()})")
    model = YOLO(str(cfg.YOLO_WEIGHTS))
    
    results = model.predict(img_bgr, conf=0.45, verbose=False)
    boxes = results[0].boxes
    print(f"YOLO detection count: {len(boxes)}")
    
    if len(boxes) > 0:
        box = boxes[0]
        xyxy = [int(round(v)) for v in box.xyxy[0].cpu().numpy().tolist()]
        conf = float(box.conf[0].cpu().numpy().item())
        print(f"[OK] Detected face bbox: {xyxy}, confidence: {conf:.4f}")
    else:
        print("[WARN] Zero faces detected.")

if __name__ == "__main__":
    test_single_yolo()
