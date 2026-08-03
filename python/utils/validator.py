"""
IndoLens - Pre-flight Validation Module
Validates inputs (video, datasets, embeddings, weights, output dirs) before processing.
"""

import os
from exception import VideoProcessingError, DatasetError

VALID_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkw']

def validate_video(video_path: str) -> bool:
    """Validate if video file exists, is non-empty, and has valid extension."""
    if not os.path.exists(video_path):
        raise VideoProcessingError(f"Video file not found at path: {video_path}")
    
    if os.path.getsize(video_path) == 0:
        raise VideoProcessingError(f"Video file is empty (0 bytes): {video_path}")

    ext = os.path.splitext(video_path)[1].lower()
    if ext not in VALID_VIDEO_EXTENSIONS:
        raise VideoProcessingError(f"Unsupported video format '{ext}'. Allowed: {VALID_VIDEO_EXTENSIONS}")

    return True

def validate_dataset(dataset_dir: str) -> bool:
    """Validate if actor dataset folder exists and is non-empty."""
    if not os.path.exists(dataset_dir):
        raise DatasetError(f"Dataset directory not found: {dataset_dir}")
    
    subdirs = [d for d in os.listdir(dataset_dir) if os.path.isdir(os.path.join(dataset_dir, d))]
    if not subdirs:
        raise DatasetError(f"No actor folders found inside dataset directory: {dataset_dir}")

    return True

def validate_embedding(embedding_path: str) -> bool:
    """Validate if embedding file exists and is non-empty."""
    if not os.path.exists(embedding_path):
        raise DatasetError(f"Embedding file not found: {embedding_path}")

    if os.path.getsize(embedding_path) == 0:
        raise DatasetError(f"Embedding file is empty (0 bytes): {embedding_path}")

    return True

def validate_output(output_dir: str) -> bool:
    """Validate and ensure output directory exists and is writable."""
    try:
        os.makedirs(output_dir, exist_ok=True)
        test_file = os.path.join(output_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception as e:
        raise OSError(f"Output directory '{output_dir}' is not writable: {str(e)}")
