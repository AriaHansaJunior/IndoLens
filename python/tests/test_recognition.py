import sys
import unittest
import numpy as np
from pathlib import Path

# Add python directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import FACE_DISTANCE_THRESHOLD, FACENET_EMBEDDING_DIM
from recognition.euclidean_distance import calculate_distance, calculate_all_distances
from recognition.threshold import verify_threshold, classify_result, format_actor_name
from recognition.embedding_matcher import (
    load_actor_embeddings,
    load_all_embeddings,
    compare_embedding,
    find_best_match
)
from recognition.recognition_result import export_recognition
from recognition.recognition_engine import recognize_face, recognize_frame


class TestSession5Recognition(unittest.TestCase):

    def setUp(self):
        self.vec_a = np.ones(128, dtype=np.float32) / np.sqrt(128)
        self.vec_b = np.ones(128, dtype=np.float32) / np.sqrt(128)
        
        # Create an orthogonal vector
        vec_c_raw = np.ones(128, dtype=np.float32)
        vec_c_raw[:64] = -1.0
        self.vec_c = vec_c_raw / np.linalg.norm(vec_c_raw)

        self.mock_db = {
            "iqbaal_ramadhan": [
                {"file": "001.npy", "embedding": self.vec_a}
            ],
            "pevita_pearce": [
                {"file": "001.npy", "embedding": self.vec_c}
            ]
        }

    def test_euclidean_distance(self):
        """Test calculation of Euclidean distance between 128-D embeddings."""
        dist_same = calculate_distance(self.vec_a, self.vec_b)
        self.assertAlmostEqual(dist_same, 0.0, places=5)

        dist_diff = calculate_distance(self.vec_a, self.vec_c)
        self.assertGreater(dist_diff, 0.0)

    def test_calculate_all_distances(self):
        """Test calculating distance against all actors in database."""
        distances = calculate_all_distances(self.vec_a, self.mock_db)
        self.assertEqual(len(distances), 2)
        
        iqbaal_dist = next(d for d in distances if d["actor"] == "iqbaal_ramadhan")
        self.assertAlmostEqual(iqbaal_dist["distance"], 0.0, places=5)

    def test_verify_threshold(self):
        """Test threshold verification logic."""
        self.assertTrue(verify_threshold(0.43, threshold=0.6))
        self.assertTrue(verify_threshold(0.60, threshold=0.6))
        self.assertFalse(verify_threshold(0.61, threshold=0.6))
        self.assertFalse(verify_threshold(0.81, threshold=0.6))

    def test_format_actor_name(self):
        """Test formatting folder actor name to Title Case."""
        self.assertEqual(format_actor_name("iqbaal_ramadhan"), "Iqbaal Ramadhan")
        self.assertEqual(format_actor_name("reza_rahadian"), "Reza Rahadian")
        self.assertEqual(format_actor_name("Tidak Dikenali"), "Tidak Dikenali")

    def test_classify_result(self):
        """Test result classification according to LOCK 1 strategy."""
        known_res = classify_result("iqbaal_ramadhan", 0.43, is_below_threshold=True)
        self.assertEqual(known_res["actor"], "Iqbaal Ramadhan")
        self.assertEqual(known_res["distance"], 0.43)
        self.assertEqual(known_res["status"], "known")

        unknown_res = classify_result("pevita_pearce", 0.81, is_below_threshold=False)
        self.assertEqual(unknown_res["actor"], "Tidak Dikenali")
        self.assertEqual(unknown_res["distance"], 0.81)
        self.assertEqual(unknown_res["status"], "unknown")

    def test_find_best_match_known(self):
        """Test best match finding known actor below threshold."""
        match = find_best_match(self.vec_a, self.mock_db, threshold=0.6)
        self.assertEqual(match["actor"], "Iqbaal Ramadhan")
        self.assertEqual(match["status"], "known")
        self.assertLessEqual(match["distance"], 0.6)

    def test_find_best_match_unknown(self):
        """Test best match finding unknown status when distance exceeds threshold."""
        # Query vec_a against database containing only vec_c (distance ~ 1.414 > threshold 0.6)
        pevita_db = {"pevita_pearce": [{"file": "001.npy", "embedding": self.vec_c}]}
        match = find_best_match(self.vec_a, pevita_db, threshold=0.6)
        self.assertEqual(match["actor"], "Tidak Dikenali")
        self.assertEqual(match["status"], "unknown")
        self.assertGreater(match["distance"], 0.6)

    def test_export_recognition_json_contract(self):
        """Test JSON output contract structure matching LOCK 9."""
        sample_data = {
            "video": {"fps": 30, "total_frames": 100},
            "frames": [
                {
                    "frame": 1,
                    "detections": [
                        {
                            "bbox": [120, 80, 240, 260],
                            "confidence": 0.98,
                            "actor": "Iqbaal Ramadhan",
                            "distance": 0.43,
                            "status": "known"
                        }
                    ]
                }
            ]
        }
        exported = export_recognition(sample_data, command="recognize-video", message="Recognition completed.")
        self.assertEqual(exported["status"], "success")
        self.assertEqual(exported["command"], "recognize-video")
        self.assertEqual(exported["message"], "Recognition completed.")
        self.assertIn("video", exported["data"])
        self.assertIn("frames", exported["data"])
        self.assertEqual(exported["data"]["frames"][0]["detections"][0]["actor"], "Iqbaal Ramadhan")

    def test_recognize_frame_dummy(self):
        """Test recognize_frame on synthetic image array."""
        dummy_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        dets = recognize_frame(dummy_frame, all_actor_embeddings=self.mock_db)
        self.assertIsInstance(dets, list)


if __name__ == "__main__":
    unittest.main()
