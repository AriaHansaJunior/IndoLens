import cv2
import numpy as np
from recognition.text_renderer import draw_text, draw_background, measure_text

# Actor to Character Mapping
CHARACTER_MAPPING = {
    "Bayu Skak": "Bayu",
    "bayu_skak": "Bayu"
}

# Bounding Box Color: Green for both known and unknown as per IndoLens design
GREEN_COLOR = (0, 255, 0)
WHITE_COLOR = (255, 255, 255)
BLACK_BG = (0, 0, 0)


def draw_bounding_box(img, bbox, color=GREEN_COLOR, thickness=2):
    """
    Draw green bounding box around face coordinates [x1, y1, x2, y2].
    """
    x1, y1, x2, y2 = [int(v) for v in bbox]
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
    return img


def draw_bbox(img, bbox, color=GREEN_COLOR, thickness=2):
    """Alias for draw_bounding_box."""
    return draw_bounding_box(img, bbox, color, thickness)


def calculate_position(img_shape, bbox, box_w, box_h):
    """
    Calculate text overlay position, ensuring it stays inside frame bounds.
    If top position is out of frame, flip to bottom of bounding box.
    """
    frame_h, frame_w = img_shape[:2]
    x1, y1, x2, y2 = [int(v) for v in bbox]

    # Try positioning above bounding box
    text_x = x1
    text_y = y1 - box_h - 5

    # If text goes above top edge, place below bounding box
    if text_y < 0:
        text_y = y2 + 5

    # If text exceeds right edge, adjust leftwards
    if text_x + box_w > frame_w:
        text_x = max(0, frame_w - box_w - 5)

    # If text exceeds bottom edge, clamp inside frame
    if text_y + box_h > frame_h:
        text_y = max(0, frame_h - box_h - 5)

    return int(text_x), int(text_y)


def adjust_position(img_shape, bbox, box_w, box_h):
    """Alias for calculate_position."""
    return calculate_position(img_shape, bbox, box_w, box_h)


def draw_actor_name(img, actor_name, position, font_scale=0.5, thickness=1):
    """Draw actor name on line 2."""
    return draw_text(img, actor_name, position, font_scale=font_scale, color=WHITE_COLOR, thickness=thickness)


def draw_actor(img, actor_name, position, font_scale=0.5, thickness=1):
    """Alias for draw_actor_name."""
    return draw_actor_name(img, actor_name, position, font_scale, thickness)


def draw_character_name(img, character_name, position, font_scale=0.6, thickness=2):
    """Draw character name on line 1."""
    return draw_text(img, character_name, position, font_scale=font_scale, color=GREEN_COLOR, thickness=thickness)


def draw_character(img, character_name, position, font_scale=0.6, thickness=2):
    """Alias for draw_character_name."""
    return draw_character_name(img, character_name, position, font_scale, thickness)


def draw_unknown(img, bbox):
    """
    Draw overlay for unknown actor ("Tidak Dikenali").
    """
    draw_bounding_box(img, bbox, color=GREEN_COLOR, thickness=2)

    label = "Tidak Dikenali"
    w, h, baseline = measure_text(label, font_scale=0.55, thickness=1)
    
    padding = 6
    box_w = w + padding * 2
    box_h = h + padding * 2
    
    pos_x, pos_y = calculate_position(img.shape, bbox, box_w, box_h)
    
    # Background rectangle
    draw_background(img, (pos_x, pos_y), (pos_x + box_w, pos_y + box_h), color=BLACK_BG, alpha=0.65)
    
    # Text
    draw_text(img, label, (pos_x + padding, pos_y + box_h - baseline - padding), font_scale=0.55, color=WHITE_COLOR, thickness=1)
    return img


def draw_known(img, bbox, actor_name, character_name=None):
    """
    Draw overlay for known actor:
    Line 1: Character Name
    Line 2: Actor Name
    """
    draw_bounding_box(img, bbox, color=GREEN_COLOR, thickness=2)

    if not character_name:
        character_name = CHARACTER_MAPPING.get(actor_name, actor_name)

    w1, h1, b1 = measure_text(character_name, font_scale=0.6, thickness=2)
    w2, h2, b2 = measure_text(actor_name, font_scale=0.5, thickness=1)

    max_w = max(w1, w2)
    padding = 6
    line_spacing = 4
    box_w = max_w + padding * 2
    box_h = h1 + h2 + line_spacing + padding * 2

    pos_x, pos_y = calculate_position(img.shape, bbox, box_w, box_h)

    # Semi-transparent background
    draw_background(img, (pos_x, pos_y), (pos_x + box_w, pos_y + box_h), color=BLACK_BG, alpha=0.65)

    # Line 1: Character Name
    draw_text(img, character_name, (pos_x + padding, pos_y + h1 + padding - b1), font_scale=0.6, color=GREEN_COLOR, thickness=2)

    # Line 2: Actor Name
    draw_text(img, actor_name, (pos_x + padding, pos_y + h1 + h2 + line_spacing + padding - b2), font_scale=0.5, color=WHITE_COLOR, thickness=1)

    return img
