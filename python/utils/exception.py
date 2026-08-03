"""
IndoLens - Custom Exception Handler Module
Handles exceptions across Python pipeline safely.
"""

import sys
import traceback
from typing import Dict, Any
from logger import log_error

class IndoLensException(Exception):
    """Base exception class for IndoLens application."""
    def __init__(self, message: str, code: str = "SYSTEM_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class ModelLoadError(IndoLensException):
    """Raised when YOLO or FaceNet models fail to initialize."""
    def __init__(self, message: str):
        super().__init__(message, code="MODEL_LOAD_ERROR")

class VideoProcessingError(IndoLensException):
    """Raised when input video file is corrupt, empty, or unreadable."""
    def __init__(self, message: str):
        super().__init__(message, code="VIDEO_PROCESSING_ERROR")

class DatasetError(IndoLensException):
    """Raised when dataset embeddings or dataset folders are missing."""
    def __init__(self, message: str):
        super().__init__(message, code="DATASET_ERROR")

def handle_exception(exc: Exception) -> Dict[str, Any]:
    """Generic exception handler."""
    log_error(f"Unhandled Exception: {str(exc)}")
    log_error(traceback.format_exc())
    return {
        "status": "error",
        "code": getattr(exc, "code", "UNKNOWN_ERROR"),
        "error": str(exc)
    }

def handle_model_error(exc: Exception) -> Dict[str, Any]:
    """Handle model initialization errors."""
    log_error(f"Model Failure: {str(exc)}")
    return {
        "status": "error",
        "code": "MODEL_LOAD_ERROR",
        "error": f"Failed to load AI model: {str(exc)}"
    }

def handle_video_error(exc: Exception) -> Dict[str, Any]:
    """Handle video read/process errors."""
    log_error(f"Video Processing Failure: {str(exc)}")
    return {
        "status": "error",
        "code": "VIDEO_PROCESSING_ERROR",
        "error": f"Invalid or corrupt video: {str(exc)}"
    }

def handle_dataset_error(exc: Exception) -> Dict[str, Any]:
    """Handle dataset/embedding errors."""
    log_error(f"Dataset Exception: {str(exc)}")
    return {
        "status": "error",
        "code": "DATASET_ERROR",
        "error": f"Dataset integrity issue: {str(exc)}"
    }
