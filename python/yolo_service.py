"""
IndoLens - Python YOLO Face Detection & Recognition Micro-Service (Session 5)
Provides high-performance, low-latency face detection, 128-D embedding, and recognition endpoint.
Pre-loads YOLOv8, FaceNet InceptionResnetV1, and actor reference embeddings into memory on startup.
Computes Euclidean distance against reference embeddings using threshold 0.65 (Known vs Unknown).
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
from config.config import YOLO_MODEL_PATH, YOLO_CONFIDENCE, FACE_DISTANCE_THRESHOLD
from facenet.embedding_generator import load_facenet_model, generate_embedding
from recognition.embedding_matcher import load_all_embeddings, find_best_match
from config.dataset import FACENET_EMBEDDING_DIM

# Global model & database containers
YOLO_MODEL = None
FACENET_MODEL = None
ALL_ACTOR_EMBEDDINGS = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pre-load YOLO, FaceNet, and reference actor embeddings once into memory on server startup.
    Eliminates process initialization overhead and disk I/O during real-time streaming.
    """
    global YOLO_MODEL, FACENET_MODEL, ALL_ACTOR_EMBEDDINGS
    print(f"[YOLO Service] Loading YOLO face model from {YOLO_MODEL_PATH}...")
    YOLO_MODEL = load_model()

    print("[FaceNet Service] Pre-loading FaceNet model (InceptionResnetV1/vggface2)...")
    FACENET_MODEL = load_facenet_model()

    # Pre-load actor reference embeddings from python/embeddings/
    print("[Recognition Service] Pre-loading reference actor embeddings from python/embeddings/...")
    ALL_ACTOR_EMBEDDINGS = load_all_embeddings()
    print(f"[Recognition Service] Loaded embeddings for {len(ALL_ACTOR_EMBEDDINGS)} actors: {list(ALL_ACTOR_EMBEDDINGS.keys())}")

    # Warm-up inference with dummy frame to initialize PyTorch graphs
    dummy_frame = np.zeros((384, 384, 3), dtype=np.uint8)
    _ = predict_frame(dummy_frame)

    # Warm-up FaceNet with dummy face crop (160x160x3)
    dummy_crop = np.zeros((160, 160, 3), dtype=np.uint8)
    _ = generate_embedding(dummy_crop)

    print("[Pipeline Service] YOLO, FaceNet, and Actor Embeddings ready for real-time recognition.")
    yield
    print("[Pipeline Service] Shutting down.")


# Initialize FastAPI application with lifespan
app = FastAPI(
    title="IndoLens YOLO Face Detection & Recognition Service",
    description="Session 5 Real-time face detection, 128-D embedding, and recognition bridge",
    version="1.2.0",
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
        "service": "IndoLens YOLO + FaceNet + Recognition Service",
        "yolo_loaded": YOLO_MODEL is not None,
        "facenet_loaded": FACENET_MODEL is not None,
        "actors_loaded": len(ALL_ACTOR_EMBEDDINGS),
        "actors_list": list(ALL_ACTOR_EMBEDDINGS.keys()),
        "distance_threshold": FACE_DISTANCE_THRESHOLD,
        "confidence_threshold": YOLO_CONFIDENCE,
        "embedding_dim": FACENET_EMBEDDING_DIM,
    }


@app.post("/detect")
async def detect_faces_endpoint(request: Request):
    """
    Real-time face detection, FaceNet 128-D embedding, and Recognition endpoint (Session 5).
    Accepts raw binary image body (JPEG/PNG), runs Ultralytics YOLOv8 face detection,
    crops each detected face bounding box, extracts 128-D FaceNet embedding,
    and computes Euclidean Distance against reference embeddings with threshold 0.65.
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
    # predict_frame returns: [{"bbox": bbox, "confidence": conf, "crop": cropped_array}]
    detections = predict_frame(img_bgr)

    # FaceNet Embedding & Recognition Phase: process each face crop
    serializable_faces = []
    t_facenet_start = time.perf_counter()
    t_recognition_total = 0.0

    for det in detections:
        bbox = det["bbox"]  # [x1, y1, x2, y2]
        confidence = float(det["confidence"])
        crop = det.get("crop")

        face_data = {
            "bbox": bbox,
            "confidence": round(confidence, 4),
            "embedding_dim": 0,
            "embedding": None,
            "facenet_status": "no_crop",
            "actor": "Tidak Dikenali",
            "distance": 999.0,
            "status": "unknown"
        }

        if crop is not None and getattr(crop, "size", 0) > 0:
            try:
                emb = generate_embedding(crop)
                if emb is not None and len(emb) == FACENET_EMBEDDING_DIM:
                    face_data["embedding_dim"] = int(len(emb))
                    face_data["embedding"] = [round(float(v), 6) for v in emb]
                    face_data["facenet_status"] = "success"

                    # Session 5: Recognition via Euclidean Distance & Threshold 0.65
                    t_rec = time.perf_counter()
                    rec_res = find_best_match(emb, ALL_ACTOR_EMBEDDINGS, threshold=FACE_DISTANCE_THRESHOLD)
                    t_recognition_total += (time.perf_counter() - t_rec) * 1000

                    face_data["actor"] = rec_res["actor"]
                    face_data["distance"] = rec_res["distance"]
                    face_data["status"] = rec_res["status"]  # "known" | "unknown"
                else:
                    face_data["facenet_status"] = "invalid_dimension"
            except Exception as e:
                face_data["facenet_status"] = f"error: {str(e)}"

        serializable_faces.append(face_data)

    facenet_ms = round((time.perf_counter() - t_facenet_start) * 1000, 2)
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    processed_count = sum(1 for f in serializable_faces if f["facenet_status"] == "success")
    known_count = sum(1 for f in serializable_faces if f.get("status") == "known")
    unknown_count = sum(1 for f in serializable_faces if f.get("status") == "unknown")
    rec_ms = round(t_recognition_total, 2)

    return {
        "status": "success",
        "faces_count": len(serializable_faces),
        "facenet_processed_count": processed_count,
        "known_faces_count": known_count,
        "unknown_faces_count": unknown_count,
        "faces": serializable_faces,
        "frame_dimensions": [img_width, img_height],
        "inference_time_ms": elapsed_ms,
        "facenet_time_ms": facenet_ms,
        "recognition_time_ms": rec_ms
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
