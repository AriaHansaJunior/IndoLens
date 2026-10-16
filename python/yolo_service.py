"""
IndoLens - Python YOLO Face Detection & Recognition Micro-Service (Session 5)
Provides high-performance, low-latency face detection, 128-D embedding, and recognition endpoint.
Pre-loads YOLOv8, FaceNet InceptionResnetV1, and actor reference embeddings into memory on startup.
Computes Euclidean distance against reference embeddings using threshold 0.65 (Known vs Unknown).
"""

import sys
import time
import re
import shutil
import json
from pathlib import Path
from contextlib import asynccontextmanager
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Ensure python directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from yolo.detector import load_model, predict_frame
from config.config import YOLO_MODEL_PATH, YOLO_CONFIDENCE, FACE_DISTANCE_THRESHOLD
from facenet.embedding_generator import load_facenet_model, generate_embedding
from recognition.embedding_matcher import load_all_embeddings, find_best_match, load_actor_embeddings
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


MANIFEST_PATH = BASE_DIR / "embeddings" / "manifest.json"


def load_image_bgr(path_or_str):
    """
    Robust image loader supporting JPEG, PNG, WebP, AVIF, and other formats.
    Attempts cv2.imread first, falls back to PIL.Image.open converted to OpenCV BGR.
    """
    p_str = str(path_or_str)
    try:
        img_bgr = cv2.imread(p_str)
        if img_bgr is not None:
            return img_bgr
    except Exception:
        pass

    try:
        pil_img = Image.open(p_str)
        rgb = np.array(pil_img.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def load_manifest():
    """Load reference embedding manifest linking actors to database records."""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"actors": {}, "updated_at": 0}


def save_manifest(manifest):
    """Save reference embedding manifest to disk."""
    manifest["updated_at"] = time.time()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


@app.post("/prune-orphaned-actors")
async def prune_orphaned_actors_endpoint(request: Request):
    """
    Prune any actor folders in python/embeddings/ that are not present in active MySQL database.
    Ensures zero stale or orphaned actor references exist (Session 8 Rule 5).
    """
    global ALL_ACTOR_EMBEDDINGS
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON body"}

    active_actors = body.get("active_actors", [])
    active_slugs = set()
    for a in active_actors:
        slug = a.get("actor_slug")
        if not slug and a.get("full_name"):
            slug = re.sub(r'[^a-zA-Z0-9]+', '_', a["full_name"]).lower().strip('_')
        if slug:
            active_slugs.add(slug)

    emb_dir = BASE_DIR / "embeddings"
    pruned_orphans = []
    if emb_dir.exists():
        for item in list(emb_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                if item.name not in active_slugs:
                    shutil.rmtree(str(item), ignore_errors=True)
                    pruned_orphans.append(item.name)
                    ALL_ACTOR_EMBEDDINGS.pop(item.name, None)

    # Clean manifest of any slug not in active_slugs
    manifest = load_manifest()
    actors_map = manifest.get("actors", {})
    manifest_changed = False
    for orphan in list(actors_map.keys()):
        if orphan not in active_slugs:
            del actors_map[orphan]
            manifest_changed = True
    if manifest_changed:
        manifest["actors"] = actors_map
        save_manifest(manifest)

    return {
        "status": "success",
        "pruned_orphans": pruned_orphans,
        "active_actors_count": len(active_slugs),
        "total_actors_loaded": len(ALL_ACTOR_EMBEDDINGS)
    }


@app.post("/sync-actor-embedding")
async def sync_actor_embedding_endpoint(request: Request):
    """
    Generic Reference Embedding Synchronization (Session 8).
    Accepts actor ID, full name, and list of image files.
    Runs exact same pipeline as runtime:
      load_image_bgr -> YOLO face detection -> Face crop -> FaceNet 128-D embedding -> save .npy.
    Prunes stale/orphaned files for this actor and updates manifest.
    Immediately updates in-memory reference embeddings so live recognition reflects new data instantly.
    """
    global ALL_ACTOR_EMBEDDINGS
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON body"}

    actor_id = body.get("actor_id")
    full_name = str(body.get("full_name", "")).strip()
    force = bool(body.get("force", False))
    if not full_name:
        return {"status": "error", "message": "Missing actor full_name"}

    images = body.get("images", [])
    if not images and "image_id" in body and "image_path" in body:
        images = [{"image_id": body["image_id"], "image_path": body["image_path"]}]

    # Canonical actor slug strictly derived from full_name
    actor_slug = re.sub(r'[^a-zA-Z0-9]+', '_', full_name).lower().strip('_')
    actor_dir = BASE_DIR / "embeddings" / actor_slug
    actor_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    skipped_no_face = []
    skipped_not_found = []
    active_file_names = set()

    for item in images:
        image_id = item.get("image_id")
        img_path_str = item.get("image_path")
        if not img_path_str or image_id is None:
            continue

        target_file = actor_dir / f"{image_id}.npy"
        active_file_names.add(f"{image_id}.npy")

        # Reuse existing valid embedding if not forced
        if not force and target_file.exists():
            try:
                cached_emb = np.load(str(target_file))
                if len(cached_emb) == FACENET_EMBEDDING_DIM:
                    generated.append(image_id)
                    continue
            except Exception:
                pass

        img_path = Path(img_path_str)
        if not img_path.exists():
            skipped_not_found.append(image_id)
            continue

        img_bgr = load_image_bgr(img_path)
        if img_bgr is None:
            skipped_not_found.append(image_id)
            continue

        # Exact same YOLO face detection pipeline
        detections = predict_frame(img_bgr)
        if not detections:
            skipped_no_face.append(image_id)
            continue

        # Use primary detected face (highest confidence)
        best_det = max(detections, key=lambda d: d.get("confidence", 0))
        crop = best_det.get("crop")
        if crop is None or getattr(crop, "size", 0) == 0:
            skipped_no_face.append(image_id)
            continue

        # Exact same FaceNet embedding pipeline (128-D L2-normalized)
        emb = generate_embedding(crop)
        if emb is not None and len(emb) == FACENET_EMBEDDING_DIM:
            np.save(str(target_file), emb.astype(np.float32))
            generated.append(image_id)
        else:
            skipped_no_face.append(image_id)

    # Prune any stale .npy files in this actor directory not belonging to active images
    pruned_files = []
    if images:
        for f in list(actor_dir.glob("*.npy")):
            if f.name not in active_file_names:
                f.unlink(missing_ok=True)
                pruned_files.append(f.name)

    # Update manifest with real MySQL full_name and actor_id
    manifest = load_manifest()
    manifest.setdefault("actors", {})[actor_slug] = {
        "actor_id": actor_id,
        "full_name": full_name,
        "slug": actor_slug,
        "files": sorted([f.name for f in actor_dir.glob("*.npy")]),
    }
    save_manifest(manifest)

    # Immediately reload actor embeddings in memory with real full_name
    ALL_ACTOR_EMBEDDINGS[actor_slug] = load_actor_embeddings(
        actor_slug,
        base_path=BASE_DIR / "embeddings",
        full_name=full_name
    )

    return {
        "status": "success",
        "actor_id": actor_id,
        "full_name": full_name,
        "actor_slug": actor_slug,
        "generated_count": len(generated),
        "generated_image_ids": generated,
        "pruned_files": pruned_files,
        "skipped_no_face": skipped_no_face,
        "skipped_not_found": skipped_not_found,
        "total_embeddings_for_actor": len(ALL_ACTOR_EMBEDDINGS.get(actor_slug, [])),
        "total_actors_loaded": len(ALL_ACTOR_EMBEDDINGS)
    }


@app.delete("/delete-actor-embedding")
async def delete_actor_embedding_endpoint(request: Request):
    """
    Delete specific reference embedding when an image is deleted in CAMP.
    """
    global ALL_ACTOR_EMBEDDINGS
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON body"}

    full_name = str(body.get("full_name", "")).strip()
    image_id = body.get("image_id")
    if not full_name or image_id is None:
        return {"status": "error", "message": "Missing full_name or image_id"}

    actor_slug = re.sub(r'[^a-zA-Z0-9]+', '_', full_name).lower().strip('_')
    target_file = BASE_DIR / "embeddings" / actor_slug / f"{image_id}.npy"

    deleted = False
    if target_file.exists():
        target_file.unlink()
        deleted = True

    # Update manifest
    manifest = load_manifest()
    if actor_slug in manifest.get("actors", {}):
        flist = manifest["actors"][actor_slug].get("files", [])
        rem_name = f"{image_id}.npy"
        if rem_name in flist:
            flist.remove(rem_name)
            manifest["actors"][actor_slug]["files"] = flist
            save_manifest(manifest)

    # Reload embeddings for this actor
    reloaded = load_actor_embeddings(actor_slug, base_path=BASE_DIR / "embeddings", full_name=full_name)
    if reloaded:
        ALL_ACTOR_EMBEDDINGS[actor_slug] = reloaded
    else:
        ALL_ACTOR_EMBEDDINGS.pop(actor_slug, None)

    return {
        "status": "success",
        "deleted": deleted,
        "actor_slug": actor_slug,
        "remaining_embeddings": len(ALL_ACTOR_EMBEDDINGS.get(actor_slug, [])),
        "total_actors_loaded": len(ALL_ACTOR_EMBEDDINGS)
    }


@app.delete("/delete-actor")
async def delete_actor_endpoint(request: Request):
    """
    Delete all reference embeddings for an actor when deleted in CAMP.
    """
    global ALL_ACTOR_EMBEDDINGS
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON body"}

    full_name = str(body.get("full_name", "")).strip()
    if not full_name:
        return {"status": "error", "message": "Missing full_name"}

    actor_slug = re.sub(r'[^a-zA-Z0-9]+', '_', full_name).lower().strip('_')
    actor_dir = BASE_DIR / "embeddings" / actor_slug

    deleted = False
    if actor_dir.exists():
        shutil.rmtree(str(actor_dir), ignore_errors=True)
        deleted = True

    # Update manifest
    manifest = load_manifest()
    if actor_slug in manifest.get("actors", {}):
        del manifest["actors"][actor_slug]
        save_manifest(manifest)

    ALL_ACTOR_EMBEDDINGS.pop(actor_slug, None)

    return {
        "status": "success",
        "deleted": deleted,
        "actor_slug": actor_slug,
        "total_actors_loaded": len(ALL_ACTOR_EMBEDDINGS)
    }


@app.post("/reload-embeddings")
def reload_embeddings_endpoint():
    """
    Force reload all reference embeddings from python/embeddings/ directory.
    Uses manifest.json if present to filter out orphaned/stale references.
    """
    global ALL_ACTOR_EMBEDDINGS
    ALL_ACTOR_EMBEDDINGS = load_all_embeddings(base_path=BASE_DIR / "embeddings")
    return {
        "status": "success",
        "actors_loaded": len(ALL_ACTOR_EMBEDDINGS),
        "actors_list": list(ALL_ACTOR_EMBEDDINGS.keys())
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
        try:
            import io
            pil_img = Image.open(io.BytesIO(contents))
            rgb = np.array(pil_img.convert("RGB"))
            img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            img_bgr = None

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
    t_yolo_start = time.perf_counter()
    detections = predict_frame(img_bgr)
    yolo_ms = round((time.perf_counter() - t_yolo_start) * 1000, 2)

    # FaceNet Embedding & Recognition Phase: process each face crop
    serializable_faces = []
    t_facenet_start = time.perf_counter()
    t_recognition_total = 0.0

    for idx, det in enumerate(detections):
        bbox = det["bbox"]  # [x1, y1, x2, y2]
        confidence = float(det["confidence"])
        crop = det.get("crop")

        face_data = {
            "bbox": bbox,
            "confidence": round(confidence, 4),
            "embedding_dim": 0,
            "embedding": None,
            "facenet_status": "no_crop",
            "actor": "Unknown",
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

                    face_data["actor"] = rec_res["actor"] if rec_res["status"] == "known" else "Unknown"
                    face_data["distance"] = rec_res["distance"]
                    face_data["status"] = rec_res["status"]  # "known" | "unknown"

                    print(f"[Recognition Diagnostic] Face #{idx+1} -> Match: {face_data['actor']} | Dist: {face_data['distance']} | Threshold: {FACE_DISTANCE_THRESHOLD} | Status: {face_data['status']}")
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
        "yolo_time_ms": yolo_ms,
        "facenet_time_ms": facenet_ms,
        "recognition_time_ms": rec_ms
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
