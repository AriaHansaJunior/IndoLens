import numpy as np


def crop_face(frame, bbox):
    """
    Crop face region from frame based on bounding box.
    Output is in-memory numpy.ndarray (NOT saved to disk).
    
    :param frame: numpy.ndarray input image/frame
    :param bbox: list/tuple [x1, y1, x2, y2]
    :return: cropped numpy.ndarray
    """
    if frame is None or not isinstance(frame, np.ndarray):
        raise ValueError("Invalid frame: expected numpy.ndarray")

    x1, y1, x2, y2 = [int(v) for v in bbox]

    h, w = frame.shape[:2]
    x1 = max(0, min(x1, w))
    y1 = max(0, min(y1, h))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))

    if x2 <= x1 or y2 <= y1:
        return np.empty((0, 0, 3), dtype=frame.dtype)

    cropped = frame[y1:y2, x1:x2]
    return convert_numpy(cropped)


def validate_crop(cropped_img):
    """
    Validate that cropped image is a valid, non-empty numpy array.
    
    :param cropped_img: input image object
    :return: bool True if valid, False otherwise
    """
    if cropped_img is None or not isinstance(cropped_img, np.ndarray):
        return False

    if cropped_img.size == 0 or cropped_img.ndim < 2:
        return False

    h, w = cropped_img.shape[:2]
    return h > 0 and w > 0


def convert_numpy(cropped_img):
    """
    Ensure cropped image object is a numpy.ndarray.
    
    :param cropped_img: input image
    :return: numpy.ndarray
    """
    if isinstance(cropped_img, np.ndarray):
        return cropped_img
    return np.asarray(cropped_img)
