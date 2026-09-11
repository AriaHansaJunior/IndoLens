import sys
import unittest
import numpy as np
import cv2
from pathlib import Path
from fastapi.testclient import TestClient

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import FACE_DISTANCE_THRESHOLD, FACENET_EMBEDDING_DIM
from facenet.embedding_generator import load_facenet_model, generate_embedding
from yolo.detector import load_model as yolo_load_model, predict_frame
from recognition.embedding_matcher import load_all_embeddings, find_best_match
from recognition.threshold import verify_threshold, classify_result
from yolo_service import app


class TestSession5LiveRecognition(unittest.TestCase):
    """
    Automated test suite for Session 5 — Recognition.
    Pipeline: YOLO -> Face Crop -> FaceNet 128-D -> Euclidean Distance -> Threshold 0.65 -> Known/Unknown.
    """

    @classmethod
    def setUpClass(cls):
        # Pre-load models & reference embeddings
        cls.yolo_model = yolo_load_model()
        cls.facenet_model = load_facenet_model()
        cls.all_embeddings = load_all_embeddings()

    def test_threshold_constant_is_0_65(self):
        """Verify the configured threshold is strictly 0.65."""
        self.assertEqual(FACE_DISTANCE_THRESHOLD, 0.65)

    def test_threshold_boundary_rules(self):
        """
        Verify boundary behavior around threshold 0.65:
        <= 0.65 -> Known
        > 0.65  -> Unknown (Tidak Dikenali)
        """
        self.assertTrue(verify_threshold(0.50, threshold=0.65))
        self.assertTrue(verify_threshold(0.64, threshold=0.65))
        self.assertTrue(verify_threshold(0.65, threshold=0.65))  # Boundary inclusive
        self.assertFalse(verify_threshold(0.6501, threshold=0.65))
        self.assertFalse(verify_threshold(0.66, threshold=0.65))
        self.assertFalse(verify_threshold(0.95, threshold=0.65))

        # Classification results
        res_known = classify_result("bayu_eko_moektito", 0.65, is_below_threshold=True)
        self.assertEqual(res_known["actor"], "Bayu Eko Moektito")
        self.assertEqual(res_known["status"], "known")
        self.assertEqual(res_known["distance"], 0.65)

        res_unknown = classify_result("bayu_eko_moektito", 0.66, is_below_threshold=False)
        self.assertEqual(res_unknown["actor"], "Tidak Dikenali")
        self.assertEqual(res_unknown["status"], "unknown")
        self.assertEqual(res_unknown["distance"], 0.66)

    def test_known_actor_recognition(self):
        """
        Test that an actual dataset actor (bayu_eko_01.jpg) is correctly recognized:
        YOLO Face Crop -> FaceNet -> 128-D -> Euclidean distance <= 0.65 -> Known ('Bayu Eko Moektito').
        """
        img_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        self.assertTrue(img_path.exists(), f"Sample image not found: {img_path}")

        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        # 1. YOLO face detection
        dets = predict_frame(img)
        self.assertGreaterEqual(len(dets), 1)

        crop = dets[0]["crop"]
        self.assertIsNotNone(crop)
        self.assertGreater(crop.size, 0)

        # 2. FaceNet embedding (128-D)
        emb = generate_embedding(crop)
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)

        # 3. Recognition against reference embeddings with threshold 0.65
        match = find_best_match(emb, self.all_embeddings, threshold=0.65)

        self.assertEqual(match["status"], "known")
        self.assertEqual(match["actor"], "Bayu Eko Moektito")
        self.assertLessEqual(match["distance"], 0.65)

    def test_unknown_face_recognition(self):
        """
        Test that an unknown face produces Euclidean distance > 0.65 and status 'unknown'.
        """
        # Synthetic neutral face crop not present in reference database
        unknown_crop = np.full((160, 160, 3), 128, dtype=np.uint8)

        emb = generate_embedding(unknown_crop)
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)

        match = find_best_match(emb, self.all_embeddings, threshold=0.65)

        self.assertEqual(match["status"], "unknown")
        self.assertEqual(match["actor"], "Tidak Dikenali")
        self.assertGreater(match["distance"], 0.65)

    def test_multi_face_independent_recognition(self):
        """
        Test that multiple faces (1 Known + 1 Unknown) in the same pipeline run
        are recognized independently without cross-interference.
        """
        img_known_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        img_known = cv2.imread(str(img_known_path))
        dets = predict_frame(img_known)
        crop_known = dets[0]["crop"]

        crop_unknown = np.full((160, 160, 3), 128, dtype=np.uint8)

        emb_known = generate_embedding(crop_known)
        emb_unknown = generate_embedding(crop_unknown)

        match_known = find_best_match(emb_known, self.all_embeddings, threshold=0.65)
        match_unknown = find_best_match(emb_unknown, self.all_embeddings, threshold=0.65)

        # Face A: Known
        self.assertEqual(match_known["status"], "known")
        self.assertEqual(match_known["actor"], "Bayu Eko Moektito")
        self.assertLessEqual(match_known["distance"], 0.65)

        # Face B: Unknown
        self.assertEqual(match_unknown["status"], "unknown")
        self.assertEqual(match_unknown["actor"], "Tidak Dikenali")
        self.assertGreater(match_unknown["distance"], 0.65)

    def test_yolo_service_endpoint_recognition_payload(self):
        """
        Test FastAPI /detect endpoint live response for Session 5 recognition contract.
        """
        img_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        img_bytes = img_path.read_bytes()

        with TestClient(app) as client:
            # Check /health endpoint
            h_res = client.get("/health")
            self.assertEqual(h_res.status_code, 200)
            h_data = h_res.json()
            self.assertTrue(h_data["yolo_loaded"])
            self.assertTrue(h_data["facenet_loaded"])
            self.assertGreaterEqual(h_data["actors_loaded"], 1)
            self.assertEqual(h_data["distance_threshold"], 0.65)

            # Check /detect endpoint with known actor image
            res = client.post("/detect", content=img_bytes, headers={"Content-Type": "image/jpeg"})
            self.assertEqual(res.status_code, 200)

            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertGreaterEqual(data["faces_count"], 1)
            self.assertGreaterEqual(data["known_faces_count"], 1)
            self.assertIn("recognition_time_ms", data)

            face = data["faces"][0]
            self.assertIn("bbox", face)
            self.assertIn("confidence", face)
            self.assertEqual(face["embedding_dim"], 128)
            self.assertEqual(face["facenet_status"], "success")
            self.assertEqual(face["status"], "known")
            self.assertEqual(face["actor"], "Bayu Eko Moektito")
            self.assertLessEqual(face["distance"], 0.65)


if __name__ == "__main__":
    unittest.main()
