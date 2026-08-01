import sys
import time
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import FACE_DISTANCE_THRESHOLD
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
        if crop_img is None or not isinstance(crop_img, np.ndarray) or crop_img.size == 0:
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


def recognize_video(video_path, all_actor_embeddings=None, threshold=FACE_DISTANCE_THRESHOLD):
    """
    Process video end-to-end for face detection and actor recognition frame-by-frame.
    
    LOCK 3: Stateless Recognition - Tidak menggunakan tracking.
    LOCK 4: Pipeline YOLO -> Crop -> FaceNet -> Euclidean -> Known / Unknown.
    LOCK 7: Compare against ALL embeddings.
    LOCK 8: Recognition tidak membaca MySQL.
    
    :param video_path: Path or str path to video file
    :param all_actor_embeddings: pre-loaded reference embeddings dict
    :param threshold: float distance threshold
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

            dets = recognize_frame(frame, all_actor_embeddings=all_actor_embeddings, threshold=threshold)
            
            frames_output.append({
                "frame": frame_number,
                "detections": dets
            })
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
