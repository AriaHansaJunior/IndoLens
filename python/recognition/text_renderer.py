import cv2
import numpy as np

def measure_text(text, font_scale=0.6, thickness=1, font=cv2.FONT_HERSHEY_SIMPLEX):
    """
    Measure text width and height in pixels.
    """
    (width, height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    return width, height + baseline, baseline


def wrap_text(text, max_width, font_scale=0.6, thickness=1, font=cv2.FONT_HERSHEY_SIMPLEX):
    """
    Wrap text into multiple lines if it exceeds max_width pixels.
    """
    words = text.split(" ")
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        w, _, _ = measure_text(test_line, font_scale, thickness, font)
        if w <= max_width or not current_line:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


def draw_background(img, pt1, pt2, color=(0, 0, 0), alpha=0.6):
    """
    Draw a semi-transparent background rectangle on image frame.
    """
    x1, y1 = int(pt1[0]), int(pt1[1])
    x2, y2 = int(pt2[0]), int(pt2[1])
    
    h, w, _ = img.shape
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    
    if x2 <= x1 or y2 <= y1:
        return img

    sub_img = img[y1:y2, x1:x2]
    rect = np.full(sub_img.shape, color, dtype=np.uint8)
    res = cv2.addWeighted(sub_img, 1.0 - alpha, rect, alpha, 0)
    img[y1:y2, x1:x2] = res
    return img


def draw_text(img, text, position, font_scale=0.6, color=(255, 255, 255), thickness=1, font=cv2.FONT_HERSHEY_SIMPLEX):
    """
    Draw text onto frame at given (x, y) position.
    """
    x, y = int(position[0]), int(position[1])
    cv2.putText(img, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return img
