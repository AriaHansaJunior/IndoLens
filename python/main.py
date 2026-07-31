import sys
import json
import time
from pathlib import Path

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import DATASET_PATH, EMBEDDING_PATH
from utils.dataset_scanner import scan_dataset, scan_actor, scan_images
from utils.dataset_validator import validate_dataset, validate_actor_folder, validate_images, count_images
from utils.dataset_loader import load_dataset, load_actor, load_images
from utils.image_loader import read_image, convert_rgb
from utils.image_preprocessor import resize_image, normalize_image, prepare_tensor
from facenet.embedding_generator import (
    load_facenet_model,
    generate_embedding,
    save_embedding,
    load_actor_embeddings,
    calculate_euclidean_distance,
    find_best_match
)

# ==========================================
# RESERVED METHOD STUBS (Session 1, 3, & 4)
# ==========================================

# face detection method
def detect_faces(frame):
    """Detect faces in a given frame using YOLOv8."""
    pass

# face cropping
def crop_face(frame, bbox):
    """Crop face region from frame based on bounding box."""
    pass

# feature extraction method
def extract_features(face_img):
    """Extract visual features from face image."""
    pass

# triplet loss
def compute_triplet_loss(anchor, positive, negative):
    """Compute triplet loss for embedding optimization."""
    pass

# actor recognition
def recognize_actor(embedding, known_embeddings_db):
    """Match facial embedding against known actor dataset."""
    return find_best_match(embedding, known_embeddings_db)

# json writer
def format_json_response(status, command, message, data):
    """Format standard JSON output structure across all commands."""
    return json.dumps({
        "status": status,
        "command": command,
        "message": message,
        "data": data
    }, indent=2)

# video processor
def process_video(video_path):
    """Process input video frame by frame for facial detection and recognition."""
    pass

# overlay renderer
def render_overlay(frame, detections):
    """Draw bounding boxes and actor label overlays on video frame."""
    pass


def run_embedding_generation():
    """Scan dataset and generate 128-D .npy FaceNet embeddings for all actor images."""
    dataset = load_dataset()
    generated_count = 0
    results = {}

    for actor_name, actor_data in dataset.items():
        if not actor_data or not actor_data["images"]:
            continue

        actor_results = []
        for img_path in actor_data["images"]:
            emb = generate_embedding(img_path)
            out_filename = Path(img_path).stem + ".npy"
            out_path = EMBEDDING_PATH / actor_name / out_filename
            saved_file = save_embedding(emb, out_path)
            actor_results.append({
                "source": Path(img_path).name,
                "embedding": saved_file,
                "dimension": len(emb)
            })
            generated_count += 1

        results[actor_name] = actor_results

    return {
        "embeddings_generated": generated_count,
        "actors_processed": len(results),
        "details": results
    }


def main():
    start_time = time.time()
    command = sys.argv[1] if len(sys.argv) > 1 else "default"

    try:
        if command == "scan":
            summary = scan_dataset()
            print(format_json_response("success", "scan", "Dataset scanned successfully.", {"scan_results": summary}))

        elif command == "validate":
            report = validate_dataset()
            status_str = "success" if report.get("valid") else "error"
            msg = "Dataset validation passed." if report.get("valid") else "Dataset validation failed."
            print(format_json_response(status_str, "validate", msg, report))

        elif command == "generate-embeddings":
            res = run_embedding_generation()
            print(format_json_response("success", "generate-embeddings", "FaceNet embeddings generated successfully.", res))

        else:
            video_input = sys.argv[1] if len(sys.argv) > 1 else ""
            data = {
                "video": str(video_input),
                "actors": [],
                "detections": [],
                "processing_time": round(time.time() - start_time, 4)
            }
            print(format_json_response("initialized", "process-video", "Video processor initialized.", data))

    except Exception as err:
        print(format_json_response("error", command, str(err), {}))
        sys.exit(1)


if __name__ == "__main__":
    main()
