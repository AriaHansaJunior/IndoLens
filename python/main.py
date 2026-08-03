import sys
import json
import time
from pathlib import Path

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from utils.logger import initialize_logger, log_info, log_success, log_warning, log_error, log_execution
from utils.exception import handle_exception, handle_model_error, handle_video_error, handle_dataset_error, IndoLensException
from utils.validator import validate_video, validate_dataset, validate_output
from recognition.recognition_engine import recognize_video
from recognition.overlay_renderer import render_video

# ==========================================
# RESERVED METHOD STUBS (Session 1, 3, 4 & 5)
# ==========================================

# face detection method
def detect_faces(frame):
    """Detect faces in a given frame using YOLOv8."""
    return yolo_detect_faces(frame)

# face cropping
def crop_face(frame, bbox):
    """Crop face region from frame based on bounding box into in-memory numpy array."""
    return yolo_crop_face(frame, bbox)

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
    """Process input video frame by frame for facial detection."""
    return yolo_predict_video(video_path)

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
    logger = initialize_logger()
    command = sys.argv[1] if len(sys.argv) > 1 else "default"

    log_info(f"Command [{command}] received.")

    try:
        if command == "scan":
            summary = scan_dataset()
            log_success("Dataset scanned successfully.")
            print(format_json_response("success", "scan", "Dataset scanned successfully.", {"scan_results": summary}))

        elif command == "validate":
            report = validate_dataset()
            status_str = "success" if report.get("valid") else "error"
            msg = "Dataset validation passed." if report.get("valid") else "Dataset validation failed."
            if report.get("valid"):
                log_success(msg)
            else:
                log_warning(msg)
            print(format_json_response(status_str, "validate", msg, report))

        elif command == "generate-embeddings":
            res = run_embedding_generation()
            log_success("FaceNet embeddings generated successfully.")
            print(format_json_response("success", "generate-embeddings", "FaceNet embeddings generated successfully.", res))

        elif command == "detect-video":
            video_input = sys.argv[2] if len(sys.argv) > 2 else ""
            validate_video(video_input)
            res = process_video(video_input)
            log_success(f"Detection completed for video: {video_input}")
            print(json.dumps(res, indent=2))

        elif command == "detect-frame":
            image_input = sys.argv[2] if len(sys.argv) > 2 else ""
            if not image_input:
                raise ValueError("Missing image file argument for detect-frame command.")
            img = read_image(image_input)
            if hasattr(img, "convert"):
                import numpy as np
                img = np.array(img.convert("RGB"))
            dets = yolo_predict_frame(img)
            serializable_dets = []
            for d in dets:
                serializable_dets.append({
                    "bbox": d["bbox"],
                    "confidence": d["confidence"]
                })
            res = export_detection({
                "image": str(image_input),
                "faces_count": len(serializable_dets),
                "faces": serializable_dets
            })
            res["command"] = "detect-frame"
            log_success(f"Detection completed for image: {image_input}")
            print(json.dumps(res, indent=2))

        elif command == "recognize-video":
            video_input = sys.argv[2] if len(sys.argv) > 2 else ""
            validate_video(video_input)
            
            # Optional Metadata Injection passed from Laravel (LOCK 26 & 28)
            actor_metadata = None
            if len(sys.argv) > 3:
                raw_meta = sys.argv[3]
                try:
                    if Path(raw_meta).exists():
                        with open(raw_meta, "r", encoding="utf-8") as f:
                            actor_metadata = json.load(f)
                    else:
                        actor_metadata = json.loads(raw_meta)
                except Exception:
                    actor_metadata = None

            # 1. Recognize via AI Core (LOCK 27: Pure Recognition)
            res = recognize_video(video_input)
            
            # 2. Extract Detections
            frames_data = res.get("data", {}).get("frames", [])
            
            # 3. Render Video with Metadata Overlay (LOCK 28)
            output_video_path = render_video(video_input, frames_data, actor_metadata=actor_metadata)
            
            # 4. Inject Output Video Path & Metadata to JSON response
            if "data" in res and isinstance(res["data"], dict):
                res["data"]["output_video"] = output_video_path
                if actor_metadata:
                    res["data"]["actor_metadata"] = actor_metadata

            # 5. Return JSON Single Source of Truth
            elapsed = time.time() - start_time
            log_success(f"Recognition completed for video '{video_input}' in {elapsed:.2f}s.")
            print(json.dumps(res, indent=2))

        elif command == "recognize-frame":
            image_input = sys.argv[2] if len(sys.argv) > 2 else ""
            if not image_input:
                raise ValueError("Missing image file argument for recognize-frame command.")
            dets = recognize_frame(image_input)
            res = export_recognition({
                "image": str(image_input),
                "faces_count": len(dets),
                "detections": dets
            }, command="recognize-frame", message="Recognition completed.")
            print(json.dumps(res, indent=2))

        else:
            video_input = sys.argv[1] if len(sys.argv) > 1 else ""
            data = {
                "video": str(video_input),
                "actors": [],
                "detections": [],
                "processing_time": round(time.time() - start_time, 4)
            }
            print(format_json_response("initialized", "process-video", "Video processor initialized.", data))

    except IndoLensException as err:
        log_error(f"IndoLensException: {err.message}")
        print(format_json_response("error", command, err.message, {"code": err.code}))
        sys.exit(2)
    except ValueError as err:
        log_error(f"ValueError: {str(err)}")
        print(format_json_response("error", command, str(err), {}))
        sys.exit(2)
    except FileNotFoundError as err:
        log_error(f"FileNotFoundError: {str(err)}")
        print(format_json_response("error", command, str(err), {}))
        sys.exit(2)
    except Exception as err:
        log_error(f"Exception: {str(err)}")
        err_str = str(err)
        exit_code = 3 if ("model" in err_str.lower() or "torch" in err_str.lower() or "yolo" in err_str.lower() or "facenet" in err_str.lower()) else 1
        print(format_json_response("error", command, err_str, {}))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()

