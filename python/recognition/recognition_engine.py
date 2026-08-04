import sys
import time
import json
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import FACE_DISTANCE_THRESHOLD, FRAME_SAMPLE_RATE, MIN_FACE_CONFIDENCE
from facenet.embedding_generator import generate_embedding
from yolo.detector import load_model as yolo_load_model, predict_frame as yolo_predict_frame
from yolo.video_processor import open_video, read_frame, release_video
from yolo.frame_extractor import get_total_frame, get_fps
from utils.image_loader import read_image, convert_rgb

from recognition.embedding_matcher import load_all_embeddings, find_best_match
from recognition.recognition_result import export_recognition


def recognize_face(face_input, all_actor_embeddings=None, threshold=FACE_DISTANCE_THRESHOLD):
    """
    Recognize a single face crop using FaceNet 128-D embedding and minimum Euclidean distance.
    
    LOCK 6: One Face = One Embedding.
    
    :param face_input: numpy.ndarray, PIL Image, or file path of cropped face
    :param all_actor_embeddings: pre-loaded dict of reference embeddings (loaded automatically if None)
    :param threshold: float distance threshold
    :return: dict classification result {"actor": str, "distance": float, "status": str}
    """
    if face_input is None:
        return {
            "actor": "Tidak Dikenali",
            "distance": 999.0,
            "status": "unknown"
        }

    if all_actor_embeddings is None:
        all_actor_embeddings = load_all_embeddings()

    # Generate 128-D FaceNet L2-normalized embedding
    emb = generate_embedding(face_input)

    # Find minimum distance match across all actor reference embeddings
    match_res = find_best_match(emb, all_actor_embeddings, threshold=threshold)
    return match_res


def recognize_frame(frame, all_actor_embeddings=None, threshold=FACE_DISTANCE_THRESHOLD):
    """
    Recognize all faces in a single frame using YOLO face detection and FaceNet recognition.
    
    LOCK 2: Multi Face Recognition - Semua wajah diproses.
    LOCK 5: Bounding Box menggunakan hasil resmi YOLO.
    
    :param frame: numpy.ndarray input image frame or image file path
    :param all_actor_embeddings: pre-loaded reference embeddings dict
    :param threshold: float distance threshold
    :return: list of formatted detections [{"bbox": [...], "confidence": float, "actor": str, "distance": float, "status": str}]
    """
    if frame is None:
        return []

    if isinstance(frame, (str, Path)):
        img = read_image(frame)
        frame = convert_rgb(img)

    if hasattr(frame, "convert"):
        frame = np.array(frame.convert("RGB"))

    if all_actor_embeddings is None:
        all_actor_embeddings = load_all_embeddings()

    # Run YOLO face detection -> returns list of {"bbox": [...], "confidence": float, "crop": numpy.ndarray}
    yolo_dets = yolo_predict_frame(frame)
    frame_detections = []

    for det in yolo_dets:
        crop_img = det.get("crop")
        conf = det.get("confidence", 0.0)

        # Skip FaceNet embedding computation for low confidence detections
        if conf < MIN_FACE_CONFIDENCE or crop_img is None or not isinstance(crop_img, np.ndarray) or crop_img.size == 0:
            rec_res = {
                "actor": "Tidak Dikenali",
                "distance": 999.0,
                "status": "unknown"
            }
        else:
            rec_res = recognize_face(crop_img, all_actor_embeddings=all_actor_embeddings, threshold=threshold)

        frame_detections.append({
            "bbox": det["bbox"],
            "confidence": det["confidence"],
            "actor": rec_res["actor"],
            "distance": rec_res["distance"],
            "status": rec_res["status"]
        })

    return frame_detections


def recognize_video(video_path, all_actor_embeddings=None, threshold=FACE_DISTANCE_THRESHOLD, sample_rate=FRAME_SAMPLE_RATE, status_file_path=None):
    """
    Process video using Frame Sampling for face detection and actor recognition.
    
    LOCK 3: Pure Frame Sampling - Bounding box murni berasal dari hasil inferensi YOLO yang sesungguhnya.
    
    :param video_path: Path or str path to video file
    :param all_actor_embeddings: pre-loaded reference embeddings dict
    :param threshold: float distance threshold
    :param sample_rate: int process 1 frame every N frames
    :param status_file_path: optional path to write progress JSON file
    :return: dict formatted JSON response conforming to Session 5 contract
    """
    # Load reference actor embeddings ONCE before video processing loop
    if all_actor_embeddings is None:
        all_actor_embeddings = load_all_embeddings()

    # Preload YOLO model once
    yolo_load_model()

    cap = open_video(video_path)
    total_frames = get_total_frame(cap)
    fps = get_fps(cap)

    frames_output = []
    frame_number = 1

    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret or frame is None:
                break

            # Frame Sampling: Only execute YOLO & FaceNet on sampled frames
            if sample_rate <= 1 or (frame_number - 1) % sample_rate == 0:
                dets = recognize_frame(frame, all_actor_embeddings=all_actor_embeddings, threshold=threshold)
            else:
                dets = []
            
            frames_output.append({
                "frame": frame_number,
                "detections": dets
            })

            # Update progress file periodically
            if status_file_path and total_frames and total_frames > 0 and (frame_number % 15 == 0 or frame_number == total_frames):
                pct = int((frame_number / total_frames) * 75) # Reserve last 25% for video overlay rendering
                try:
                    with open(status_file_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "status": "processing",
                            "progress": min(pct, 75),
                            "stage": f"Recognizing Faces ({frame_number}/{total_frames})",
                            "video_url": None,
                            "actors": []
                        }, f, indent=2)
                except Exception as err:
                    from utils.logger import log_error
                    log_error(f"Failed to update progress JSON: {err}")

            frame_number += 1

    finally:
        release_video(cap)

    video_info = {
        "fps": int(round(fps)) if fps and fps > 0 else 30,
        "total_frames": int(total_frames) if total_frames and total_frames > 0 else len(frames_output)
    }

    data = {
        "video": video_info,
        "frames": frames_output
    }

    return export_recognition(data, command="recognize-video", message="Recognition completed.")
