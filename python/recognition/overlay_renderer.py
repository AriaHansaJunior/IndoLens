import cv2
from pathlib import Path
from recognition.frame_renderer import draw_known, draw_unknown

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_VIDEO_DIR = BASE_DIR / "outputs" / "videos"


def draw_overlay(frame, detections, actor_metadata=None):
    """
    Draw overlays for all face detections in a single image frame using optional metadata passed from Laravel.
    
    LOCK 26: Metadata Ownership - Python accepts metadata sent by Laravel.
    """
    char_map = {}
    if actor_metadata:
        if isinstance(actor_metadata, list):
            for meta in actor_metadata:
                if isinstance(meta, dict) and "actor" in meta:
                    char_map[meta["actor"]] = meta.get("character", meta["actor"])
        elif isinstance(actor_metadata, dict):
            char_map = actor_metadata

    for det in detections:
        bbox = det.get("bbox", [])
        status = det.get("status", "unknown")
        actor_name = det.get("actor", "Tidak Dikenali")

        if len(bbox) != 4:
            continue

        if status == "known":
            character_name = char_map.get(actor_name)
            draw_known(frame, bbox, actor_name, character_name=character_name)
        else:
            draw_unknown(frame, bbox)

    return frame


def render_frame(frame, detections, actor_metadata=None):
    """Alias for draw_overlay."""
    return draw_overlay(frame, detections, actor_metadata=actor_metadata)


def render_video(video_path, frames_detections, output_path=None, actor_metadata=None):
    """
    Render video with bounding box overlays burned onto every frame.
    
    :param video_path: str or Path to input video file
    :param frames_detections: list of frame detection dicts [{"frame": 1, "detections": [...]}, ...]
    :param output_path: str or Path optional output video path
    :param actor_metadata: optional list or dict of actor metadata passed from Laravel
    :return: str absolute path to output rendered mp4 video
    """
    video_path = Path(video_path)
    if not output_path:
        OUTPUT_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_VIDEO_DIR / f"{video_path.stem}_overlay.mp4"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file for overlay rendering: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Use Media Foundation backend on Windows with H264 which is widely supported by browsers
    fourcc = cv2.VideoWriter_fourcc(*"H264")
    out = cv2.VideoWriter(str(output_path), cv2.CAP_MSMF, fourcc, fps, (width, height))

    # Index detections by frame number for fast lookup
    detection_map = {item["frame"]: item.get("detections", []) for item in frames_detections}

    frame_idx = 1
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            dets = detection_map.get(frame_idx, [])
            rendered_frame = render_frame(frame, dets, actor_metadata=actor_metadata)
            out.write(rendered_frame)
            frame_idx += 1

    finally:
        cap.release()
        out.release()

    return str(output_path.resolve())


def export_video(video_path, frames_detections, output_path=None, actor_metadata=None):
    """Alias for render_video."""
    return render_video(video_path, frames_detections, output_path, actor_metadata=actor_metadata)


def save_video(video_path, frames_detections, output_path=None, actor_metadata=None):
    """Alias for render_video."""
    return render_video(video_path, frames_detections, output_path, actor_metadata=actor_metadata)
