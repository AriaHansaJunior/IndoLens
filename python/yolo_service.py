"""
IndoLens - Python YOLO Face Detection Micro-Service (Session 3)
Provides high-performance, low-latency face detection endpoint using
the pre-existing Ultralytics YOLOv8 face model in yolo/detector.py.
Model weights are loaded ONCE into memory on startup.
"""

import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Ensure python directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from yolo.detector import load_model, predict_frame
from config.config import YOLO_MODEL_PATH, YOLO_CONFIDENCE

# Global model container
MODEL = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-load YOLO model once into memory on server startup.
    Eliminates process initialization overhead during real-time streaming.
    """
    global MODEL
    print(f"[YOLO Service] Loading YOLO face model from {YOLO_MODEL_PATH}...")
    MODEL = load_model()
    # Warm-up inference with dummy frame to initialize PyTorch graphs
    dummy_frame = np.zeros((384, 384, 3), dtype=np.uint8)
    _ = predict_frame(dummy_frame)
    print("[YOLO Service] Model warmed up and ready for real-time inference.")
    yield
    print("[YOLO Service] Shutting down.")


# Initialize FastAPI application with lifespan
app = FastAPI(
    title="IndoLens YOLO Face Detection Service",
    description="Session 3 Real-time face detection bridge",
    version="1.0.0",
    lifespan=lifespan
)

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint for gateway verification."""
    return {
        "status": "ready",
        "service": "IndoLens YOLO Service",
        "model_loaded": MODEL is not None,
        "confidence_threshold": YOLO_CONFIDENCE,
    }


@app.post("/detect")
async def detect_faces_endpoint(request: Request):
    """
    Real-time face detection endpoint.
    Accepts raw binary image body (JPEG/PNG), runs Ultralytics YOLOv8 face detection,
    and returns bounding box coordinates and confidence scores.

    NO FaceNet, NO embeddings, NO recognition.
    """
    start_time = time.perf_counter()

    # Read raw body bytes directly (no python-multipart dependency)
    contents = await request.body()
    if not contents:
        return {
            "status": "error",
            "message": "Empty frame data received.",
            "faces_count": 0,
            "faces": []
        }

    # Decode image bytes to OpenCV BGR numpy array
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        return {
            "status": "error",
            "message": "Failed to decode image frame.",
            "faces_count": 0,
            "faces": []
        }

    img_height, img_width = img_bgr.shape[:2]

    # Run existing YOLO prediction pipeline (Ultralytics natively expects BGR)
    detections = predict_frame(img_bgr)

    # Format bounding box results
    serializable_faces = []
    for det in detections:
        bbox = det["bbox"]  # [x1, y1, x2, y2]
        confidence = float(det["confidence"])
        serializable_faces.append({
            "bbox": bbox,
            "confidence": round(confidence, 4)
        })

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "status": "success",
        "faces_count": len(serializable_faces),
        "faces": serializable_faces,
        "frame_dimensions": [img_width, img_height],
        "inference_time_ms": elapsed_ms
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
