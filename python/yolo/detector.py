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

# Python - YOLO
_YOLO_MODEL = None


def predict_frame(frame):
    """Predict face bounding boxes and crops for a single frame."""
    if frame is None:
        return []

    results = detect_faces(frame)
    detections = []

    for result in results:
        boxes = getattr(result, "boxes", None)
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
    """Process input video frame-by-frame for facial detection."""
    start_time = time.time()
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
    """Format detection output data into structured JSON dictionary."""
    return {
        "status": "success",
        "command": "detect-video",
        "message": "Face detection completed.",
        "data": data
    }
