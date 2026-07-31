import cv2
from pathlib import Path


def open_video(video_path):
    """
    Open video file using OpenCV VideoCapture.
    
    :param video_path: Path or string pointing to video file
    :return: cv2.VideoCapture object
    """
    path_str = str(video_path)
    if not Path(path_str).exists():
        raise FileNotFoundError(f"Video file not found: {path_str}")

    cap = cv2.VideoCapture(path_str)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video stream: {path_str}")

    return cap


def read_frame(cap):
    """
    Read the next frame from the video capture stream.
    
    :param cap: cv2.VideoCapture object
    :return: Tuple (ret: bool, frame: numpy.ndarray or None)
    """
    if cap is None or not cap.isOpened():
        return False, None

    ret, frame = cap.read()
    return ret, frame


def release_video(cap):
    """
    Release video capture resources.
    
    :param cap: cv2.VideoCapture object
    """
    if cap is not None:
        cap.release()
