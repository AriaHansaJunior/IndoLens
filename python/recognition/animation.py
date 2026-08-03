import cv2
import numpy as np

def fade_in(alpha_current, target_alpha=1.0, step=0.1):
    """
    Calculate incremented alpha value for smooth fade-in animation.
    """
    return min(target_alpha, alpha_current + step)


def typewriter(text, current_char_count, speed=1):
    """
    Return partial text slice based on typewriter character count progression.
    """
    next_count = min(len(text), current_char_count + speed)
    return text[:next_count], next_count


def alpha_transition(img1, img2, alpha):
    """
    Perform alpha blend transition between two image frames.
    """
    alpha = max(0.0, min(1.0, alpha))
    return cv2.addWeighted(img1, alpha, img2, 1.0 - alpha, 0)


def transition(img1, img2, alpha):
    """
    Alias for alpha_transition.
    """
    return alpha_transition(img1, img2, alpha)
