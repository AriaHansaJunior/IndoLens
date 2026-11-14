"""
Unit tests for Generic CAMP-to-Runtime Reference Embedding Synchronization (Session 7).
Tests sync-actor-embedding, delete-actor-embedding, delete-actor, and reload-embeddings.
"""

import sys
import shutil
import unittest
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import FACENET_EMBEDDING_DIM
from fastapi.testclient import TestClient
import yolo_service
from yolo_service import app


class TestSyncEmbeddings(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_actor_name = "Testing Generic Actor"
        self.test_actor_slug = "testing_generic_actor"
        self.test_dir = BASE_DIR / "embeddings" / self.test_actor_slug
        # Clean any preexisting test folder
        if self.test_dir.exists():
            shutil.rmtree(str(self.test_dir), ignore_errors=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(str(self.test_dir), ignore_errors=True)
        if self.test_actor_slug in yolo_service.ALL_ACTOR_EMBEDDINGS:
            del yolo_service.ALL_ACTOR_EMBEDDINGS[self.test_actor_slug]
        manifest = yolo_service.load_manifest()
        if self.test_actor_slug in manifest.get("actors", {}):
            del manifest["actors"][self.test_actor_slug]
            yolo_service.save_manifest(manifest)

    def test_sync_actor_embedding_with_real_face(self):
        # Use existing known image in dataset
        sample_img = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        self.assertTrue(sample_img.exists(), f"Sample image not found: {sample_img}")

        payload = {
            "actor_id": 999,
            "full_name": self.test_actor_name,
            "images": [
                {
                    "image_id": 9991,
                    "image_path": str(sample_img)
                }
            ]
        }

        res = self.client.post("/sync-actor-embedding", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["actor_slug"], self.test_actor_slug)
        self.assertEqual(data["generated_count"], 1)

        # Check file exists on disk
        saved_file = self.test_dir / "9991.npy"
        self.assertTrue(saved_file.exists())
        emb = np.load(str(saved_file))
        self.assertEqual(len(emb), FACENET_EMBEDDING_DIM)

        # Check in-memory update
        self.assertIn(self.test_actor_slug, yolo_service.ALL_ACTOR_EMBEDDINGS)
        self.assertEqual(len(yolo_service.ALL_ACTOR_EMBEDDINGS[self.test_actor_slug]), 1)

    def test_delete_actor_embedding_single(self):
        # Setup pre-existing embedding file
        self.test_dir.mkdir(parents=True, exist_ok=True)
        dummy_emb = np.random.randn(FACENET_EMBEDDING_DIM).astype(np.float32)
        dummy_emb = dummy_emb / np.linalg.norm(dummy_emb)
        np.save(str(self.test_dir / "8881.npy"), dummy_emb)
        np.save(str(self.test_dir / "8882.npy"), dummy_emb)

        # Reload into memory
        self.client.post("/reload-embeddings")
        self.assertIn(self.test_actor_slug, yolo_service.ALL_ACTOR_EMBEDDINGS)
        self.assertEqual(len(yolo_service.ALL_ACTOR_EMBEDDINGS[self.test_actor_slug]), 2)

        # Delete image 8881
        del_payload = {
            "actor_id": 888,
            "full_name": self.test_actor_name,
            "image_id": 8881
        }
        res = self.client.request("DELETE", "/delete-actor-embedding", json=del_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["deleted"])
        self.assertFalse((self.test_dir / "8881.npy").exists())
        self.assertTrue((self.test_dir / "8882.npy").exists())
        self.assertEqual(len(yolo_service.ALL_ACTOR_EMBEDDINGS[self.test_actor_slug]), 1)

    def test_delete_whole_actor(self):
        self.test_dir.mkdir(parents=True, exist_ok=True)
        dummy_emb = np.random.randn(FACENET_EMBEDDING_DIM).astype(np.float32)
        np.save(str(self.test_dir / "7771.npy"), dummy_emb)

        self.client.post("/reload-embeddings")
        self.assertIn(self.test_actor_slug, yolo_service.ALL_ACTOR_EMBEDDINGS)

        del_actor_payload = {
            "actor_id": 777,
            "full_name": self.test_actor_name
        }
        res = self.client.request("DELETE", "/delete-actor", json=del_actor_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["deleted"])
        self.assertFalse(self.test_dir.exists())
        self.assertNotIn(self.test_actor_slug, yolo_service.ALL_ACTOR_EMBEDDINGS)

    def test_prune_orphaned_actors(self):
        # Create an orphan actor directory
        orphan_dir = BASE_DIR / "embeddings" / "orphan_test_actor"
        orphan_dir.mkdir(parents=True, exist_ok=True)
        dummy_emb = np.random.randn(FACENET_EMBEDDING_DIM).astype(np.float32)
        np.save(str(orphan_dir / "1.npy"), dummy_emb)

        # Call reload so it is in memory
        self.client.post("/reload-embeddings")

        # Now prune orphans while keeping real database actors and self.test_actor_slug
        res = self.client.post("/prune-orphaned-actors", json={
            "active_actors": [
                {"actor_id": 1, "full_name": "Bayu Eko Moektito", "actor_slug": "bayu_eko_moektito"},
                {"actor_id": 999, "full_name": self.test_actor_name, "actor_slug": self.test_actor_slug}
            ]
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("orphan_test_actor", data["pruned_orphans"])
        self.assertFalse(orphan_dir.exists())
        self.assertNotIn("orphan_test_actor", yolo_service.ALL_ACTOR_EMBEDDINGS)

    def test_sync_actor_embedding_prunes_stale_files(self):
        # Setup pre-existing stale file in test_dir
        self.test_dir.mkdir(parents=True, exist_ok=True)
        stale_file = self.test_dir / "legacy_old.npy"
        dummy_emb = np.random.randn(FACENET_EMBEDDING_DIM).astype(np.float32)
        np.save(str(stale_file), dummy_emb)
        self.assertTrue(stale_file.exists())

        sample_img = BASE_DIR / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
        payload = {
            "actor_id": 999,
            "full_name": self.test_actor_name,
            "images": [
                {
                    "image_id": 9991,
                    "image_path": str(sample_img)
                }
            ]
        }
        res = self.client.post("/sync-actor-embedding", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("legacy_old.npy", data.get("pruned_files", []))
        self.assertFalse(stale_file.exists())
        self.assertTrue((self.test_dir / "9991.npy").exists())


if __name__ == "__main__":
    unittest.main()
