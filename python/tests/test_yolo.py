import sys
import unittest
import numpy as np
from pathlib import Path

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import (
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE,
    YOLO_IOU,
    YOLO_IMAGE_SIZE,
    YOLO_DEVICE
)
from yolo.face_cropper import crop_face, validate_crop, convert_numpy
from yolo.video_processor import open_video, read_frame, release_video
from yolo.frame_extractor import extract_frame, get_total_frame, get_fps, get_resolution
from yolo.detector import (
    load_model,
    detect_faces,
    predict_frame,
    export_detection
)
from yolo.renderer import render_boxes


class TestSession4YOLO(unittest.TestCase):

    def test_config_parameters_loaded(self):
        """Verify YOLO config constants are present and correctly typed."""
        self.assertIsNotNone(YOLO_MODEL_PATH)
        self.assertIsInstance(YOLO_CONFIDENCE, float)
        self.assertIsInstance(YOLO_IOU, float)
        self.assertIsInstance(YOLO_IMAGE_SIZE, int)
        self.assertIsInstance(YOLO_DEVICE, str)

    def test_face_cropper_in_memory_numpy(self):
        """Test cropping returns numpy.ndarray in memory without writing files."""
        dummy_frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
        bbox = [100, 100, 200, 200]
        cropped = crop_face(dummy_frame, bbox)

        self.assertIsInstance(cropped, np.ndarray)
        self.assertTrue(validate_crop(cropped))
        self.assertEqual(cropped.shape, (100, 100, 3))

    def test_cropper_validation(self):
        """Test crop validation logic."""
        invalid_array = np.empty((0, 0, 3), dtype=np.uint8)
        self.assertFalse(validate_crop(invalid_array))
        self.assertFalse(validate_crop(None))

    def test_yolo_model_loading_and_prediction(self):
        """Test YOLO official model loading and frame prediction."""
        model = load_model()
        self.assertIsNotNone(model)

        dummy_frame = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)
        dets = predict_frame(dummy_frame)
        self.assertIsInstance(dets, list)

    def test_export_detection_format(self):
        """Test Session 3 compliant JSON export format."""
        data = {
            "frames": 10,
            "detections": []
        }
        res = export_detection(data)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["command"], "detect-video")
        self.assertEqual(res["message"], "Face detection completed.")
        self.assertIn("data", res)


if __name__ == "__main__":
    unittest.main()
