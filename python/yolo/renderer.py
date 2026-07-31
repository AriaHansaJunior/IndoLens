import cv2
import numpy as np


def render_boxes(frame, detections):
    """
    Draw bounding boxes and confidence scores on an OpenCV frame array.
    
    :param frame: numpy.ndarray frame
    :param detections: list of dicts [{"bbox": [x1, y1, x2, y2], "confidence": float}]
    :return: annotated numpy.ndarray frame
    """
    if frame is None:
        return None

    output_frame = frame.copy()
    for det in detections:
        bbox = det.get("bbox", [])
        conf = det.get("confidence", 0.0)
        if len(bbox) != 4:
            continue

        x1, y1, x2, y2 = [int(v) for v in bbox]
        color = (0, 255, 0)
        thickness = 2
        cv2.rectangle(output_frame, (x1, y1), (x2, y2), color, thickness)

        label = f"Face: {conf:.2f}"
        font_scale = 0.5
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(output_frame, label, (x1, max(15, y1 - 5)), font, font_scale, color, 1)

    return output_frame
