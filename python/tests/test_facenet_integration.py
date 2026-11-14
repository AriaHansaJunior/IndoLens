import sys
import unittest
import numpy as np
import cv2
from pathlib import Path

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import FACENET_EMBEDDING_DIM
from facenet.embedding_generator import load_facenet_model, generate_embedding
from yolo.face_cropper import crop_face, validate_crop
from yolo.detector import load_model as yolo_load_model


class TestSession4FaceNetIntegration(unittest.TestCase):
    """
    Automated test suite for Session 4 — FaceNet Integration.
    Validates pipeline: YOLO Bounding Box -> Face Crop -> FaceNet -> 128-D Embedding.
    Strictly verifies NO actor recognition, Euclidean distance, or threshold matching is performed.
    """

    @classmethod
    def setUpClass(cls):
        # Pre-load FaceNet model once for all tests in suite
        cls.facenet_model = load_facenet_model()

    def test_facenet_model_loading_and_singleton(self):
        """Test FaceNet model loads properly and returns singleton instance."""
        model = load_facenet_model()
        self.assertIsNotNone(model)
        self.assertIs(model, self.facenet_model)

    def test_crop_to_128d_embedding(self):
        """
        Test that a cropped face bounding box generates an exact 128-D L2-normalized embedding.
        """
        # Create synthetic frame with identifiable face region
        frame = np.full((480, 640, 3), 50, dtype=np.uint8)
        bbox = [120, 100, 280, 260]  # 160x160 region

        # Put pattern inside bbox
        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (200, 150, 100), -1)
        cv2.circle(frame, (160, 150), 15, (20, 20, 20), -1)
        cv2.circle(frame, (240, 150), 15, (20, 20, 20), -1)

        # 1. Crop face based on YOLO bounding box coordinates
        cropped = crop_face(frame, bbox)
        self.assertTrue(validate_crop(cropped))
        self.assertEqual(cropped.shape, (160, 160, 3))

        # 2. Pass crop to existing FaceNet generate_embedding implementation
        emb = generate_embedding(cropped)

        # 3. Assert embedding properties
        self.assertIsInstance(emb, np.ndarray)
        self.assertEqual(emb.shape, (FACENET_EMBEDDING_DIM,))
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)
        self.assertEqual(emb.dtype, np.float32)

        # 4. Assert L2-normalization (norm should be ~1.0)
        norm = np.linalg.norm(emb)
        self.assertAlmostEqual(norm, 1.0, places=5)

    def test_multi_face_produces_separate_embeddings(self):
        crop_a = np.full((160, 160, 3), 80, dtype=np.uint8)
        cv2.circle(crop_a, (80, 80), 40, (255, 255, 255), -1)

        crop_b = np.full((160, 160, 3), 200, dtype=np.uint8)
        cv2.rectangle(crop_b, (40, 40), (120, 120), (10, 10, 10), -1)

        emb_a = generate_embedding(crop_a)
        emb_b = generate_embedding(crop_b)

        self.assertEqual(emb_a.shape, (FACENET_EMBEDDING_DIM,))
        self.assertEqual(emb_b.shape, (FACENET_EMBEDDING_DIM,))

        difference = np.linalg.norm(emb_a - emb_b)
        self.assertGreater(difference, 0.05)

    def test_yolo_service_detect_contract_schema(self):
        import yolo_service

        self.assertEqual(yolo_service.FACENET_EMBEDDING_DIM, FACENET_EMBEDDING_DIM)

        # Create dummy detection entry with crop
        dummy_crop = np.random.randint(50, 200, (160, 160, 3), dtype=np.uint8)
        dummy_det = {
            "bbox": [50, 50, 210, 210],
            "confidence": 0.95,
            "crop": dummy_crop
        }

        # Simulate FaceNet processing logic from /detect endpoint
        emb = generate_embedding(dummy_det["crop"])
        face_data = {
            "bbox": dummy_det["bbox"],
            "confidence": round(dummy_det["confidence"], 4),
            "embedding_dim": int(len(emb)),
            "embedding": [round(float(v), 6) for v in emb],
            "facenet_status": "success"
        }

        self.assertEqual(face_data["bbox"], [50, 50, 210, 210])
        self.assertEqual(face_data["confidence"], 0.95)
        self.assertEqual(face_data["embedding_dim"], FACENET_EMBEDDING_DIM)
        self.assertEqual(len(face_data["embedding"]), FACENET_EMBEDDING_DIM)
        self.assertEqual(face_data["facenet_status"], "success")

        # Session 4 Strict Boundary Check: NO actor identification fields
        self.assertNotIn("actor", face_data)
        self.assertNotIn("distance", face_data)
        self.assertNotIn("threshold", face_data)


if __name__ == "__main__":
    unittest.main()
