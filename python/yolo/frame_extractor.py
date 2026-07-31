import cv2


def extract_frame(cap, frame_number):
    """
    Extract a specific frame by index from video capture.
    
    :param cap: cv2.VideoCapture object
    :param frame_number: int frame index
    :return: numpy.ndarray frame or None
    """
    if cap is None or not cap.isOpened():
        return None

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    if not ret:
        return None
    return frame


def get_total_frame(cap):
    """
    Get total frame count of video.
    
    :param cap: cv2.VideoCapture object
    :return: int total frames
    """
    if cap is None or not cap.isOpened():
        return 0
    return int(cap.get(cv2.CAP_PROP_FRAME_COUNT))


def get_fps(cap):
    """
    Get frames per second of video.
    
    :param cap: cv2.VideoCapture object
    :return: float FPS
    """
    if cap is None or not cap.isOpened():
        return 0.0
    return float(cap.get(cv2.CAP_PROP_FPS))


def get_resolution(cap):
    """
    Get video resolution (width, height).
    
    :param cap: cv2.VideoCapture object
    :return: tuple (width, height)
    """
    if cap is None or not cap.isOpened():
        return (0, 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return (width, height)
