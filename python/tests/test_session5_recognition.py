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

    def test_threshold_constant_synced(self):
        self.assertEqual(FACE_DISTANCE_THRESHOLD, 0.85)

    def test_threshold_boundary_rules(self):
        self.assertTrue(verify_threshold(0.50, threshold=FACE_DISTANCE_THRESHOLD))
        self.assertTrue(verify_threshold(FACE_DISTANCE_THRESHOLD - 0.01, threshold=FACE_DISTANCE_THRESHOLD))
        self.assertTrue(verify_threshold(FACE_DISTANCE_THRESHOLD, threshold=FACE_DISTANCE_THRESHOLD))
        self.assertFalse(verify_threshold(FACE_DISTANCE_THRESHOLD + 0.0001, threshold=FACE_DISTANCE_THRESHOLD))
        self.assertFalse(verify_threshold(FACE_DISTANCE_THRESHOLD + 0.05, threshold=FACE_DISTANCE_THRESHOLD))

        res_known = classify_result("bayu_eko_moektito", FACE_DISTANCE_THRESHOLD, is_below_threshold=True)
        self.assertEqual(res_known["actor"], "Bayu Eko Moektito")
        self.assertEqual(res_known["status"], "known")

        res_unknown = classify_result("bayu_eko_moektito", FACE_DISTANCE_THRESHOLD + 0.05, is_below_threshold=False)
        self.assertEqual(res_unknown["actor"], "Tidak Dikenali")
        self.assertEqual(res_unknown["status"], "unknown")

    def test_known_actor_recognition(self):
        img_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        self.assertTrue(img_path.exists(), f"Sample image not found: {img_path}")

        img = cv2.imread(str(img_path))
        self.assertIsNotNone(img)

        dets = predict_frame(img)
        self.assertGreaterEqual(len(dets), 1)

        crop = dets[0]["crop"]
        self.assertIsNotNone(crop)
        self.assertGreater(crop.size, 0)

        emb = generate_embedding(crop)
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)

        match = find_best_match(emb, self.all_embeddings, threshold=FACE_DISTANCE_THRESHOLD)

        self.assertEqual(match["status"], "known")
        self.assertEqual(match["actor"], "Bayu Eko Moektito")
        self.assertLessEqual(match["distance"], FACE_DISTANCE_THRESHOLD)

    def test_unknown_face_recognition(self):
        unknown_crop = np.full((160, 160, 3), 128, dtype=np.uint8)

        emb = generate_embedding(unknown_crop)
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)

        match = find_best_match(emb, self.all_embeddings, threshold=FACE_DISTANCE_THRESHOLD)

        self.assertEqual(match["status"], "unknown")
        self.assertEqual(match["actor"], "Tidak Dikenali")
        self.assertGreater(match["distance"], FACE_DISTANCE_THRESHOLD)

    def test_multi_face_independent_recognition(self):
        img_known_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        img_known = cv2.imread(str(img_known_path))
        dets = predict_frame(img_known)
        crop_known = dets[0]["crop"]

        crop_unknown = np.full((160, 160, 3), 128, dtype=np.uint8)

        emb_known = generate_embedding(crop_known)
        emb_unknown = generate_embedding(crop_unknown)

        match_known = find_best_match(emb_known, self.all_embeddings, threshold=FACE_DISTANCE_THRESHOLD)
        match_unknown = find_best_match(emb_unknown, self.all_embeddings, threshold=FACE_DISTANCE_THRESHOLD)

        self.assertEqual(match_known["status"], "known")
        self.assertEqual(match_known["actor"], "Bayu Eko Moektito")
        self.assertLessEqual(match_known["distance"], FACE_DISTANCE_THRESHOLD)

        self.assertEqual(match_unknown["status"], "unknown")
        self.assertEqual(match_unknown["actor"], "Tidak Dikenali")
        self.assertGreater(match_unknown["distance"], FACE_DISTANCE_THRESHOLD)

    def test_yolo_service_endpoint_recognition_payload(self):
        img_path = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        img_bytes = img_path.read_bytes()

        with TestClient(app) as client:
            h_res = client.get("/health")
            self.assertEqual(h_res.status_code, 200)
            h_data = h_res.json()
            self.assertTrue(h_data["yolo_loaded"])
            self.assertTrue(h_data["facenet_loaded"])
            self.assertGreaterEqual(h_data["actors_loaded"], 1)
            self.assertEqual(h_data["distance_threshold"], FACE_DISTANCE_THRESHOLD)

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
            self.assertEqual(face["embedding_dim"], FACENET_EMBEDDING_DIM)
            self.assertEqual(face["facenet_status"], "success")
            self.assertEqual(face["status"], "known")
            self.assertEqual(face["actor"], "Bayu Eko Moektito")
            self.assertLessEqual(face["distance"], FACE_DISTANCE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
