import os
import json
import time
from pathlib import Path
from ultralytics import YOLO

from config.config import (
    YOLO_MODEL_PATH,
    YOLO_FALLBACK_MODEL,
    YOLO_CONFIDENCE,
    YOLO_IOU,
    YOLO_IMAGE_SIZE,
    YOLO_DEVICE
)
from yolo.video_processor import open_video, read_frame, release_video
from yolo.frame_extractor import get_total_frame, get_fps, get_resolution
from yolo.face_cropper import crop_face, validate_crop

# Global cached model instance
_YOLO_MODEL = None


def load_model(model_path=None):
    """
    Load YOLO model instance using official Ultralytics API.
    
    :param model_path: Path to .pt file or official model string
    :return: YOLO model instance
    """
    global _YOLO_MODEL

    target_path = model_path if model_path else YOLO_MODEL_PATH

    # If target path does not exist, use fallback model or target path string
    if isinstance(target_path, Path) and not target_path.exists():
        target_path = str(YOLO_FALLBACK_MODEL)
    else:
        target_path = str(target_path)

    _YOLO_MODEL = YOLO(target_path)
    return _YOLO_MODEL


def detect_faces(frame):
    """
    Detect faces in a given frame using Ultralytics YOLO model.
    Reads detection thresholds and parameters directly from config.py.
    
    :param frame: numpy.ndarray input image/frame
    :return: Ultralytics Results list
    """
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        _YOLO_MODEL = load_model()

    results = _YOLO_MODEL(
        frame,
        conf=YOLO_CONFIDENCE,
        iou=YOLO_IOU,
        imgsz=YOLO_IMAGE_SIZE,
        device=YOLO_DEVICE,
        verbose=False
    )
    return results


def predict_frame(frame):
    """
    Predict face bounding boxes and confidence scores for a single frame.
    Also crops face regions into in-memory numpy.ndarray objects.
    
    :param frame: numpy.ndarray frame
    :return: list of dicts [{"bbox": [x1, y1, x2, y2], "confidence": float, "crop": numpy.ndarray}]
    """
    if frame is None:
        return []

    results = detect_faces(frame)
    detections = []

    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = [int(round(v)) for v in xyxy]
            conf = float(box.conf[0].cpu().numpy().item())

            bbox = [x1, y1, x2, y2]
            cropped_array = crop_face(frame, bbox)

            if validate_crop(cropped_array):
                detections.append({
                    "bbox": bbox,
                    "confidence": round(conf, 4),
                    "crop": cropped_array
                })

    return detections


def predict_video(video_path):
    """
    Process input video frame-by-frame for facial detection.
    Extracts bounding boxes and crops faces into memory as numpy.ndarray.
    
    :param video_path: Path to video file
    :return: dict structured detection result matching Session 3 JSON schema
    """
    start_time = time.time()
    # Load model ONCE before video processing loop
    load_model()

    cap = open_video(video_path)


    total_frames = get_total_frame(cap)
    fps = get_fps(cap)
    res = get_resolution(cap)

    frame_index = 0
    all_frame_detections = []
    total_face_crops = 0

    try:
        while True:
            ret, frame = read_frame(cap)
            if not ret or frame is None:
                break

            frame_dets = predict_frame(frame)
            if frame_dets:
                serializable_faces = []
                for det in frame_dets:
                    total_face_crops += 1
                    serializable_faces.append({
                        "bbox": det["bbox"],
                        "confidence": det["confidence"]
                    })

                all_frame_detections.append({
                    "frame_index": frame_index,
                    "faces_count": len(serializable_faces),
                    "faces": serializable_faces
                })

            frame_index += 1

    finally:
        release_video(cap)

    elapsed = round(time.time() - start_time, 4)

    data = {
        "video": str(video_path),
        "total_frames": total_frames,
        "processed_frames": frame_index,
        "fps": fps,
        "resolution": list(res),
        "total_detections": total_face_crops,
        "processing_time": elapsed,
        "detections": all_frame_detections
    }

    return export_detection(data)


def export_detection(data):
    """
    Format detection output data into Session 3 JSON schema dictionary.
    
    :param data: dict detection payload
    :return: dict formatted response
    """
    return {
        "status": "success",
        "command": "detect-video",
        "message": "Face detection completed.",
        "data": data
    }
