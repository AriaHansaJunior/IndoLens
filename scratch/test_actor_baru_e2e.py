"""
End-to-End Test for Actor Baru creation in CAMP -> Automatic Embedding -> Live Recognition -> Cleanup.
Validates the generic pipeline without manual intervention.
"""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def run_test():
    print("=" * 60)
    print("  E2E Validation: CAMP -> Reference Embedding -> Recognition")
    print("=" * 60)

    # 1. Verify YOLO service is listening
    health_url = "http://127.0.0.1:8002/health"
    req = urllib.request.Request(health_url)
    with urllib.request.urlopen(req) as resp:
        health_data = json.loads(resp.read().decode('utf-8'))
        print(f"[1] YOLO Service Health: status={health_data['status']}, actors_loaded={health_data['actors_loaded']}")
        print(f"    Current actors: {health_data['actors_list']}")

    # 2. Pick a real face image from datasets for testing
    sample_face = BASE_DIR / "python" / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_03.jpg"
    assert sample_face.exists(), f"Sample face image does not exist at {sample_face}"

    # 3. Simulate CAMP upload for 'Aktor Baru'
    new_actor_name = "Aktor Baru"
    new_actor_id = 999
    sync_url = "http://127.0.0.1:8002/sync-actor-embedding"
    sync_payload = json.dumps({
        "actor_id": new_actor_id,
        "full_name": new_actor_name,
        "images": [
            {
                "image_id": 99901,
                "image_path": str(sample_face)
            }
        ]
    }).encode('utf-8')

    req = urllib.request.Request(sync_url, data=sync_payload, headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req) as resp:
        sync_result = json.loads(resp.read().decode('utf-8'))
        print(f"[2] Sync Actor Baru Response: {sync_result}")
        assert sync_result["status"] == "success"
        assert sync_result["actor_slug"] == "aktor_baru"
        assert sync_result["generated_count"] == 1

    # 4. Verify embedding file exists on disk
    emb_file = BASE_DIR / "python" / "embeddings" / "aktor_baru" / "99901.npy"
    assert emb_file.exists(), f"Embedding file {emb_file} was not created!"
    print(f"[3] Embedding file created on disk: {emb_file}")

    # 5. Verify /health now lists 'aktor_baru' without restart
    with urllib.request.urlopen(health_url) as resp:
        health_after = json.loads(resp.read().decode('utf-8'))
        print(f"[4] Health after sync: actors_loaded={health_after['actors_loaded']}")
        assert "aktor_baru" in health_after["actors_list"], "aktor_baru not found in active in-memory actors list!"
        print("    [OK] 'aktor_baru' is ACTIVE in microservice memory!")

    # 6. Test /detect with sample_face
    detect_url = "http://127.0.0.1:8002/detect"
    with open(sample_face, "rb") as f:
        img_bytes = f.read()

    req = urllib.request.Request(detect_url, data=img_bytes, headers={'Content-Type': 'image/jpeg'}, method='POST')
    with urllib.request.urlopen(req) as resp:
        detect_result = json.loads(resp.read().decode('utf-8'))
        print(f"[5] Recognition result for Aktor Baru image:")
        faces = detect_result.get("faces", [])
        assert len(faces) > 0, "No face detected in test image!"
        matched_face = faces[0]
        print(f"    Actor: {matched_face.get('actor')}")
        print(f"    Distance: {matched_face.get('distance')}")
        print(f"    Status: {matched_face.get('status')}")
        assert matched_face.get("status") == "known", f"Expected known, got {matched_face.get('status')}"
        assert matched_face.get("distance") <= 0.65, f"Distance {matched_face.get('distance')} > 0.65"
        print(f"    [OK] Recognized with distance {matched_face.get('distance')} <= 0.65!")

    # 7. Test delete single image embedding
    del_img_url = "http://127.0.0.1:8002/delete-actor-embedding"
    del_payload = json.dumps({
        "actor_id": new_actor_id,
        "full_name": new_actor_name,
        "image_id": 99901
    }).encode('utf-8')

    req = urllib.request.Request(del_img_url, data=del_payload, headers={'Content-Type': 'application/json'}, method='DELETE')
    with urllib.request.urlopen(req) as resp:
        del_result = json.loads(resp.read().decode('utf-8'))
        print(f"[6] Delete embedding response: {del_result}")
        assert del_result["status"] == "success"
        assert del_result["deleted"] is True
        assert not emb_file.exists(), "Embedding file should have been deleted from disk!"

    # 8. Test delete whole actor
    del_actor_url = "http://127.0.0.1:8002/delete-actor"
    del_actor_payload = json.dumps({
        "actor_id": new_actor_id,
        "full_name": new_actor_name
    }).encode('utf-8')

    req = urllib.request.Request(del_actor_url, data=del_actor_payload, headers={'Content-Type': 'application/json'}, method='DELETE')
    with urllib.request.urlopen(req) as resp:
        del_actor_result = json.loads(resp.read().decode('utf-8'))
        print(f"[7] Delete actor response: {del_actor_result}")
        assert del_actor_result["status"] == "success"

    # Verify actor is gone from memory
    with urllib.request.urlopen(health_url) as resp:
        health_final = json.loads(resp.read().decode('utf-8'))
        assert "aktor_baru" not in health_final["actors_list"], "aktor_baru should not be in memory after delete!"
        print(f"[8] Cleanup confirmed: actors_loaded={health_final['actors_loaded']}")

    print("\n[SUCCESS] ALL E2E TESTS FOR 'AKTOR BARU' PASSED!")

if __name__ == "__main__":
    run_test()
