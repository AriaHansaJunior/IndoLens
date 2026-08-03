from recognition.euclidean_distance import (
    calculate_distance,
    calculate_all_distances
)
from recognition.threshold import (
    verify_threshold,
    classify_result
)
from recognition.embedding_matcher import (
    load_all_embeddings,
    load_actor_embeddings,
    compare_embedding,
    find_best_match
)
from recognition.recognition_result import (
    export_recognition
)
from recognition.recognition_engine import (
    recognize_face,
    recognize_frame,
    recognize_video
)
from recognition.overlay_renderer import (
    render_video,
    render_frame,
    draw_overlay,
    export_video,
    save_video
)
from recognition.frame_renderer import (
    draw_bounding_box,
    draw_bbox,
    draw_actor_name,
    draw_actor,
    draw_character_name,
    draw_character,
    draw_known,
    draw_unknown,
    calculate_position,
    adjust_position
)
from recognition.text_renderer import (
    draw_text,
    draw_background,
    measure_text,
    wrap_text
)
from recognition.animation import (
    fade_in,
    typewriter,
    alpha_transition,
    transition
)

__all__ = [
    "load_all_embeddings",
    "load_actor_embeddings",
    "compare_embedding",
    "find_best_match",
    "calculate_distance",
    "calculate_all_distances",
    "verify_threshold",
    "classify_result",
    "recognize_face",
    "recognize_frame",
    "recognize_video",
    "export_recognition",
    "render_video",
    "render_frame",
    "draw_overlay",
    "export_video",
    "save_video",
    "draw_bounding_box",
    "draw_bbox",
    "draw_actor_name",
    "draw_actor",
    "draw_character_name",
    "draw_character",
    "draw_known",
    "draw_unknown",
    "calculate_position",
    "adjust_position",
    "draw_text",
    "draw_background",
    "measure_text",
    "wrap_text",
    "fade_in",
    "typewriter",
    "alpha_transition",
    "transition"
]
