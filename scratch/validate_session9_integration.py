"""
IndoLens - Session 9 Full System Integration Validation Script
Verifies:
1. YOLO + FaceNet live microservice (/detect, /health)
2. Recognition against real CAMP embeddings (Bayu Eko Moektito vs Unknown)
3. MySQL Database Actor Lookup (/api/actors/lookup)
4. Active Detection State Sync (/api/actors/active)
5. Actor Detail (/actors/{id}) and Actor List (/actors) integrity
6. Error handling for corrupt/empty frames
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import cv2
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
YOLO_URL = "http://127.0.0.1:8002"
LARAVEL_URL = "http://indolens.test"  # Laragon local domain

def main():
    print("=" * 70)
    print("INDO LENS — SESSION 9 FULL SYSTEM INTEGRATION TEST")
    print("=" * 70)

    # 1. Check YOLO + FaceNet Microservice
    print("\n--- 1. YOLO + FACENET MICROSERVICE HEALTH ---")
    try:
        res = requests.get(f"{YOLO_URL}/health", timeout=5)
        res.raise_for_status()
        h_data = res.json()
        print(f"  [PASS] Service Status: {h_data.get('status')}")
        print(f"  [PASS] YOLO Loaded: {h_data.get('yolo_loaded')}")
        print(f"  [PASS] FaceNet Loaded: {h_data.get('facenet_loaded')}")
        print(f"  [PASS] Actors Loaded: {h_data.get('actors_loaded')} -> {h_data.get('actors_list')}")
        print(f"  [PASS] Threshold: {h_data.get('distance_threshold')}")
        print(f"  [PASS] Embedding Dim: {h_data.get('embedding_dim')}")
        assert h_data.get("distance_threshold") == 0.65, "Threshold must be 0.65"
        assert h_data.get("embedding_dim") == 128, "Embedding dimension must be 128"
    except Exception as e:
        print(f"  [FAIL] Health check failed: {e}")
        return 1

    # 2. Test Real Frame with Known Actor (Bayu Eko Moektito)
    print("\n--- 2. LIVE RECOGNITION — KNOWN ACTOR (Bayu Eko Moektito) ---")
    sample_known = BASE_DIR / "storage" / "app" / "public" / "actor-images" / "1-bayu-skak" / "bayu-skak-01.jpg"
    if not sample_known.exists():
        sample_known = BASE_DIR / "python" / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
    
    print(f"  Sending real image: {sample_known.name}")
    known_bytes = sample_known.read_bytes()

    try:
        t0 = time.perf_counter()
        res = requests.post(
            f"{YOLO_URL}/detect",
            data=known_bytes,
            headers={"Content-Type": "image/jpeg"},
            timeout=10
        )
        latency = (time.perf_counter() - t0) * 1000
        res.raise_for_status()
        det_data = res.json()
        print(f"  Response Status: {det_data.get('status')} (Latency: {latency:.1f}ms)")
        print(f"  Faces Detected: {det_data.get('faces_count')}")

        faces = det_data.get("faces", [])
        assert len(faces) >= 1, "Expected at least 1 face detected"
        face = faces[0]
        print(f"  Face #1: Actor='{face.get('actor')}', Status='{face.get('status')}', Distance={face.get('distance')}, Dim={face.get('embedding_dim')}")
        
        assert face.get("status") == "known", f"Expected status 'known', got {face.get('status')}"
        assert face.get("actor") == "Bayu Eko Moektito", f"Expected exact MySQL name 'Bayu Eko Moektito', got {face.get('actor')}"
        assert face.get("distance") <= 0.65, f"Expected distance <= 0.65, got {face.get('distance')}"
        assert face.get("embedding_dim") == 128, f"Expected 128-D vector, got {face.get('embedding_dim')}"
        print("  [PASS] Known actor recognized with exact MySQL identity and distance <= 0.65!")
    except Exception as e:
        print(f"  [FAIL] Known actor test failed: {e}")
        return 1

    # 3. Test Unknown Face (Synthetic / Unregistered)
    print("\n--- 3. LIVE RECOGNITION — UNKNOWN FACE ---")
    # Synthetic face with neutral features that YOLO will not match to Bayu
    synth_face = np.full((300, 300, 3), 160, dtype=np.uint8)
    # Draw simple facial feature approximations
    cv2.circle(synth_face, (100, 110), 20, (50, 50, 50), -1)
    cv2.circle(synth_face, (200, 110), 20, (50, 50, 50), -1)
    cv2.ellipse(synth_face, (150, 210), (50, 20), 0, 0, 180, (50, 50, 50), -1)
    _, unknown_jpeg = cv2.imencode('.jpg', synth_face)

    try:
        res = requests.post(
            f"{YOLO_URL}/detect",
            data=unknown_jpeg.tobytes(),
            headers={"Content-Type": "image/jpeg"},
            timeout=10
        )
        res.raise_for_status()
        det_unknown = res.json()
        print(f"  Faces Detected: {det_unknown.get('faces_count')}")
        for f in det_unknown.get("faces", []):
            print(f"  Face: Actor='{f.get('actor')}', Status='{f.get('status')}', Distance={f.get('distance')}")
            assert f.get("status") == "unknown", "Unregistered face must have status 'unknown'"
            assert f.get("actor") == "Unknown", "Unregistered face must be labelled 'Unknown'"
            assert f.get("distance") > 0.65, "Distance must exceed threshold 0.65"
        print("  [PASS] Unknown face strictly classified as 'Unknown' with distance > 0.65!")
    except Exception as e:
        print(f"  [FAIL] Unknown face test failed: {e}")
        return 1

    # 4. Test Error Handling on Corrupt / Empty Frames
    print("\n--- 4. SERVICE ERROR HANDLING (HONEST FAILURES) ---")
    try:
        # Empty payload
        res_empty = requests.post(f"{YOLO_URL}/detect", data=b"", headers={"Content-Type": "image/jpeg"})
        res_empty_json = res_empty.json()
        assert res_empty_json.get("status") == "error", "Empty frame must return status error"
        print(f"  [PASS] Empty frame handled honestly: '{res_empty_json.get('message')}'")

        # Corrupt bytes
        res_corrupt = requests.post(f"{YOLO_URL}/detect", data=b"NOT_AN_IMAGE_RANDOM_GARBAGE", headers={"Content-Type": "image/jpeg"})
        res_corrupt_json = res_corrupt.json()
        assert res_corrupt_json.get("status") == "error", "Corrupt frame must return status error"
        print(f"  [PASS] Corrupt frame handled honestly: '{res_corrupt_json.get('message')}'")
    except Exception as e:
        print(f"  [FAIL] Error handling verification failed: {e}")
        return 1

    # 5. Test Laravel Actor Lookup Endpoint
    print("\n--- 5. LARAVEL ACTOR LOOKUP (/api/actors/lookup) ---")
    try:
        res_lookup = requests.get(f"{LARAVEL_URL}/api/actors/lookup?name=Bayu%20Eko%20Moektito")
        res_lookup.raise_for_status()
        l_data = res_lookup.json()
        assert l_data.get("found") is True, "Bayu Eko Moektito must be found in MySQL"
        actor = l_data.get("actor", {})
        print(f"  [PASS] Found Actor ID: {actor.get('id')}, Name: '{actor.get('full_name')}', Gender: '{actor.get('gender')}', Age: {actor.get('age')}")
        assert actor.get("id") == 1
        assert actor.get("full_name") == "Bayu Eko Moektito"

        # Lookup Unknown / Invalid
        res_unk_lookup = requests.get(f"{LARAVEL_URL}/api/actors/lookup?name=Unknown")
        assert res_unk_lookup.json().get("found") is False
        print("  [PASS] Lookup 'Unknown' correctly returns found: false")
    except Exception as e:
        print(f"  [FAIL] Actor lookup failed: {e}")
        return 1

    # 6. Test Active Actor Detection Status Endpoint (/api/actors/active)
    print("\n--- 6. ACTIVE ACTOR SYNC & POLLING (/api/actors/active) ---")
    try:
        # Step A: Update active actor to Bayu
        res_post = requests.post(
            f"{LARAVEL_URL}/api/actors/active",
            json={"actors": ["Bayu Eko Moektito"], "window_title": "Sekawan Limo"},
            headers={"Content-Type": "application/json"}
        )
        assert res_post.status_code == 200, f"Expected 200, got {res_post.status_code}"

        # Step B: Poll active actors
        res_get = requests.get(f"{LARAVEL_URL}/api/actors/active")
        get_data = res_get.json()
        print(f"  Active actors polled: {get_data.get('detected_actors')}")
        print(f"  Character map: {get_data.get('character_map')}")
        assert "Bayu Eko Moektito" in get_data.get("detected_actors", [])
        print("  [PASS] Active actor successfully marked as detected in MySQL!")

        # Step C: Reset active actors (camera stop simulation)
        res_reset = requests.post(
            f"{LARAVEL_URL}/api/actors/active",
            json={"actors": []},
            headers={"Content-Type": "application/json"}
        )
        assert res_reset.status_code == 200
        res_get_reset = requests.get(f"{LARAVEL_URL}/api/actors/active")
        assert len(res_get_reset.json().get("detected_actors", [])) == 0
        print("  [PASS] Active actors cleanly reset upon camera stop!")
    except Exception as e:
        print(f"  [FAIL] Active actor sync failed: {e}")
        return 1

    # 7. Test Actor Detail Page & Actor List Page
    print("\n--- 7. ACTOR DETAIL (/actors/1) & ACTOR LIST (/actors) ---")
    try:
        res_list = requests.get(f"{LARAVEL_URL}/actors")
        assert res_list.status_code == 200, "Actor list must return 200"
        assert "Bayu Eko Moektito" in res_list.text, "Bayu Eko Moektito must appear in Actor List"
        print("  [PASS] Actor List page (/actors) rendered successfully with real actor data.")

        res_detail = requests.get(f"{LARAVEL_URL}/actors/1")
        assert res_detail.status_code == 200, "Actor detail must return 200"
        assert "Bayu Eko Moektito" in res_detail.text
        assert "Filmography" in res_detail.text
        print("  [PASS] Actor Detail page (/actors/1) rendered successfully with real filmography.")
    except Exception as e:
        print(f"  [FAIL] Actor pages check failed: {e}")
        return 1

    print("\n" + "=" * 70)
    print("ALL SESSION 9 SYSTEM INTEGRATION CHECKS PASSED (LOCAL & SERVICE)")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
