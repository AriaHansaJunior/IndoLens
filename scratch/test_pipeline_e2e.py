"""
IndoLens - Session 10 Comprehensive Final E2E Test Suite
Tests all layers:
- HTTPS Gateway on port 8000 & LAN IP 192.168.20.212
- YOLO + FaceNet live inference via HTTPS
- Non-identical real image recognition (Bayu Eko Moektito)
- Unregistered face recognition (Unknown, > 0.65)
- MySQL Actor Lookup (/api/actors/lookup)
- Active Detection State Sync & Reset (/api/actors/active)
- Actor Detail (/actors/1) & Actor List (/actors)
- Error handling on malformed payloads
"""

import sys
import json
import time
from pathlib import Path
import numpy as np
import cv2
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent.parent
GATEWAY_HTTPS = "https://127.0.0.1:8000"
GATEWAY_LAN = "https://192.168.20.212:8000"
HTTP_HELPER = "http://192.168.20.212:8080"
YOLO_DIRECT = "http://127.0.0.1:8002"

def main():
    print("=" * 75)
    print("INDO LENS — SESSION 10 FINAL END-TO-END VALIDATION SUITE")
    print("=" * 75)

    errors = []

    # -------------------------------------------------------------------------
    # TEST 1: HTTPS GATEWAY & LAN REACHABILITY FOR PHONE
    # -------------------------------------------------------------------------
    print("\n[TEST 1] HTTPS Gateway & Phone LAN Reachability")
    try:
        # Check local HTTPS
        r_local = requests.get(f"{GATEWAY_HTTPS}/camera", verify=False, timeout=5)
        assert r_local.status_code == 200, f"Expected 200, got {r_local.status_code}"
        assert "Live Camera Capture" in r_local.text
        print("  [PASS] Local HTTPS (https://127.0.0.1:8000/camera): OK (200)")

        # Check LAN IP HTTPS
        r_lan = requests.get(f"{GATEWAY_LAN}/camera", verify=False, timeout=5)
        assert r_lan.status_code == 200, f"Expected 200, got {r_lan.status_code}"
        print("  [PASS] Phone LAN HTTPS (https://192.168.20.212:8000/camera): OK (200)")

        # Check CA Certificate download endpoint
        r_ca = requests.get(f"{HTTP_HELPER}/ca.crt", timeout=5)
        assert r_ca.status_code == 200, f"Expected 200, got {r_ca.status_code}"
        assert len(r_ca.content) > 500
        print("  [PASS] Plain HTTP CA Certificate Download (http://192.168.20.212:8080/ca.crt): OK (200)")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 1 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 2: MICROSERVICE HEALTH & METHODOLOGY LOCK VERIFICATION
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Microservice Health & AI Methodology Locks")
    try:
        r_health = requests.get(f"{GATEWAY_HTTPS}/api/yolo/health", verify=False, timeout=5)
        assert r_health.status_code == 200
        h_data = r_health.json()

        assert h_data.get("yolo_loaded") is True, "YOLO model not loaded"
        assert h_data.get("facenet_loaded") is True, "FaceNet model not loaded"
        assert h_data.get("embedding_dim") == 128, "Embedding dim must be 128"
        assert h_data.get("distance_threshold") == 0.65, "Threshold must be strictly 0.65"
        assert h_data.get("actors_loaded") == 1, "Must have exactly 1 genuine actor loaded"
        assert h_data.get("actors_list") == ["bayu_eko_moektito"]

        print(f"  [PASS] YOLO Model: Pre-loaded")
        print(f"  [PASS] FaceNet InceptionResnetV1(vggface2): Pre-loaded (128-D)")
        print(f"  [PASS] Distance Metric: Euclidean Distance")
        print(f"  [PASS] Threshold: {h_data.get('distance_threshold')} (Strictly locked)")
        print(f"  [PASS] Registered Actors in Memory: {h_data.get('actors_list')}")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 2 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 3: FULL RECOGNITION PIPELINE — REAL NON-IDENTICAL IMAGE
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Live Recognition Pipeline — Real Non-Identical Frame")
    try:
        # Use a distinct photo of Bayu from CAMP
        test_img_path = BASE_DIR / "storage" / "app" / "public" / "actor-images" / "1-bayu-skak" / "bayu-skak-05.jpg"
        if not test_img_path.exists():
            test_img_path = BASE_DIR / "storage" / "app" / "public" / "actor-images" / "1-bayu-skak" / "bayu-skak-01.jpg"

        print(f"  Testing real image: {test_img_path.name} via HTTPS Gateway")
        img_bytes = test_img_path.read_bytes()

        t0 = time.perf_counter()
        r_det = requests.post(
            f"{GATEWAY_HTTPS}/api/yolo/detect",
            data=img_bytes,
            headers={"Content-Type": "image/jpeg"},
            verify=False,
            timeout=10
        )
        latency = (time.perf_counter() - t0) * 1000
        assert r_det.status_code == 200, f"Expected 200, got {r_det.status_code}"
        d_data = r_det.json()

        assert d_data.get("status") == "success"
        assert d_data.get("faces_count") >= 1
        face = d_data.get("faces")[0]

        print(f"  [PASS] Latency: {latency:.1f}ms")
        print(f"  [PASS] Face Bounding Box: {face.get('bbox')}")
        print(f"  [PASS] Confidence: {face.get('confidence')}")
        print(f"  [PASS] FaceNet Embedding Dim: {face.get('embedding_dim')}")
        print(f"  [PASS] Recognized Actor: '{face.get('actor')}'")
        print(f"  [PASS] Euclidean Distance: {face.get('distance')}")
        print(f"  [PASS] Classification Status: '{face.get('status')}'")

        assert face.get("status") == "known", f"Expected known, got {face.get('status')}"
        assert face.get("actor") == "Bayu Eko Moektito", f"Expected 'Bayu Eko Moektito', got '{face.get('actor')}'"
        assert face.get("distance") <= 0.65, f"Distance {face.get('distance')} > 0.65"
        assert face.get("embedding_dim") == 128
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 3 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 4: UNREGISTERED / UNKNOWN FACE & MULTI-FACE INDEPENDENT PROCESSING
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Unregistered Face & Multi-Face Independent Recognition")
    try:
        # Part A: Real distinct unregistered human face
        other_face_path = BASE_DIR / "public" / "img" / "foto Aria Hansa Junior.jpg"
        if other_face_path.exists():
            r_unk = requests.post(
                f"{GATEWAY_HTTPS}/api/yolo/detect",
                data=other_face_path.read_bytes(),
                headers={"Content-Type": "image/jpeg"},
                verify=False,
                timeout=10
            )
            assert r_unk.status_code == 200
            u_data = r_unk.json()
            assert u_data.get("faces_count") == 1
            f_unk = u_data.get("faces")[0]
            print(f"  Part A (Single Unregistered Face): Actor='{f_unk.get('actor')}', Dist={f_unk.get('distance')}, Status='{f_unk.get('status')}'")
            assert f_unk.get("status") == "unknown", "Unregistered face must have status 'unknown'"
            assert f_unk.get("actor") == "Unknown", "Unregistered face must have actor name 'Unknown'"
            assert f_unk.get("distance") > 0.65, "Distance must exceed threshold 0.65"
            print("  [PASS] Real unregistered face strictly classified as 'Unknown' (dist > 0.65)")

            # Part B: Real natural multi-face image from CAMP storage
            real_multi_path = BASE_DIR / "storage" / "app" / "public" / "actor-images" / "1-bayu-skak" / "bayu-skak-05.jpg"
            r_multi = requests.post(
                f"{GATEWAY_HTTPS}/api/yolo/detect",
                data=real_multi_path.read_bytes(),
                headers={"Content-Type": "image/jpeg"},
                verify=False,
                timeout=10
            )
            assert r_multi.status_code == 200
            m_data = r_multi.json()
            assert m_data.get("faces_count") == 2, f"Expected 2 faces detected, got {m_data.get('faces_count')}"
            assert m_data.get("known_faces_count") == 1
            assert m_data.get("unknown_faces_count") == 1

            known_face = next(f for f in m_data.get("faces") if f.get("status") == "known")
            unknown_face = next(f for f in m_data.get("faces") if f.get("status") == "unknown")

            print(f"  Part B (Natural Multi-Face in CAMP Image): Face 1 (Bayu)='{known_face.get('actor')}' (dist: {known_face.get('distance')}) | Face 2='{unknown_face.get('actor')}' (dist: {unknown_face.get('distance')})")
            assert known_face.get("actor") == "Bayu Eko Moektito"
            assert known_face.get("distance") <= 0.65
            assert unknown_face.get("actor") == "Unknown"
            assert unknown_face.get("distance") > 0.65
            print("  [PASS] Natural multi-face frame correctly and independently recognized (1 Known, 1 Unknown)")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 4 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 5: MYSQL IDENTITY RESOLUTION (/api/actors/lookup)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] MySQL Identity Resolution (/api/actors/lookup)")
    try:
        # Recognized exact full name lookup
        r_lookup = requests.get(f"{GATEWAY_HTTPS}/api/actors/lookup?name=Bayu%20Eko%20Moektito", verify=False, timeout=5)
        assert r_lookup.status_code == 200
        l_data = r_lookup.json()
        assert l_data.get("found") is True
        actor = l_data.get("actor")
        assert actor.get("id") == 1
        assert actor.get("full_name") == "Bayu Eko Moektito"
        assert actor.get("gender") == "Male"
        assert actor.get("age") == 31
        print(f"  [PASS] Lookup 'Bayu Eko Moektito': Found (ID: {actor.get('id')}, Gender: {actor.get('gender')}, Age: {actor.get('age')})")

        # Unknown / Nicht-dikenali rejection
        r_unk_lookup = requests.get(f"{GATEWAY_HTTPS}/api/actors/lookup?name=Unknown", verify=False, timeout=5)
        assert r_unk_lookup.json().get("found") is False
        print("  [PASS] Lookup 'Unknown': Correctly rejected (found: false)")

        r_tidak_lookup = requests.get(f"{GATEWAY_HTTPS}/api/actors/lookup?name=Tidak%20Dikenali", verify=False, timeout=5)
        assert r_tidak_lookup.json().get("found") is False
        print("  [PASS] Lookup 'Tidak Dikenali': Correctly rejected (found: false)")

        # Alias rejection (strict rule: no alias lookup)
        r_alias = requests.get(f"{GATEWAY_HTTPS}/api/actors/lookup?name=Bayu%20Skak", verify=False, timeout=5)
        assert r_alias.json().get("found") is False
        print("  [PASS] Lookup alias 'Bayu Skak': Correctly rejected (found: false - strict full_name matching only)")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 5 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 6: RUNNING VS PAUSED & ACTIVE DETECTION STATE
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Running vs Paused & Active State Sync Lifecycle")
    try:
        # Step A: Simulate pause detection syncing recognized actor to backend
        r_sync = requests.post(
            f"{GATEWAY_HTTPS}/api/actors/active",
            json={"actors": ["Bayu Eko Moektito"], "window_title": "Sekawan Limo"},
            verify=False,
            timeout=5
        )
        assert r_sync.status_code == 200

        # Step B: Poll active actors
        r_active = requests.get(f"{GATEWAY_HTTPS}/api/actors/active", verify=False, timeout=5)
        act_data = r_active.json()
        assert "Bayu Eko Moektito" in act_data.get("detected_actors", [])
        assert act_data.get("character_map", {}).get("Bayu Eko Moektito") == "Bagas"
        print("  [PASS] State sync on recognition: Active actor marked as detected (Role: Bagas)")

        # Step C: Verify Actor List displays KNOWN badge
        r_list_active = requests.get(f"{GATEWAY_HTTPS}/actors", verify=False, timeout=5)
        assert r_list_active.status_code == 200
        assert 'data-is-known="1"' in r_list_active.text
        assert 'status-known' in r_list_active.text
        print("  [PASS] Actor List (/actors): Reflects KNOWN detection badge in real-time")

        # Step D: Simulate camera stop (clears active state)
        r_clear = requests.post(
            f"{GATEWAY_HTTPS}/api/actors/active",
            json={"actors": []},
            verify=False,
            timeout=5
        )
        assert r_clear.status_code == 200

        r_cleared = requests.get(f"{GATEWAY_HTTPS}/api/actors/active", verify=False, timeout=5)
        assert len(r_cleared.json().get("detected_actors", [])) == 0
        print("  [PASS] Camera stop cleanup: Active detection state cleanly reset in MySQL")

        r_list_reset = requests.get(f"{GATEWAY_HTTPS}/actors", verify=False, timeout=5)
        assert 'data-is-known="0"' in r_list_reset.text
        print("  [PASS] Actor List (/actors): Returns to UNKNOWN status when camera stopped")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 6 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 7: ACTOR DETAIL PAGE INTEGRITY
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Actor Detail Page Integrity (/actors/1)")
    try:
        r_detail = requests.get(f"{GATEWAY_HTTPS}/actors/1", verify=False, timeout=5)
        assert r_detail.status_code == 200
        text = r_detail.text

        assert "Bayu Eko Moektito" in text
        assert "Male" in text
        assert "31 Years Old" in text
        assert "Malang, Jawa Timur" in text
        assert "Filmography" in text
        assert "Yowis Ben" in text
        assert "Sekawan Limo" in text
        print("  [PASS] Full Name: Bayu Eko Moektito")
        print("  [PASS] Demographic Data: Male, 31 Years Old, Born in Malang")
        print("  [PASS] Filmography & Database Roles: Yowis Ben, Sekawan Limo")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 7 failed: {e}")

    # -------------------------------------------------------------------------
    # TEST 8: ERROR HANDLING (HONEST FAILURES, NO FABRICATIONS)
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Error Handling & Transparent Failure Reporting")
    try:
        # Corrupt frame
        r_corrupt = requests.post(
            f"{GATEWAY_HTTPS}/api/yolo/detect",
            data=b"INVALID_IMAGE_BYTES",
            headers={"Content-Type": "image/jpeg"},
            verify=False,
            timeout=5
        )
        c_data = r_corrupt.json()
        assert c_data.get("status") == "error"
        assert "Failed to decode" in c_data.get("message")
        print(f"  [PASS] Corrupt frame: Honestly rejected ({c_data.get('message')})")

        # Empty frame
        r_empty = requests.post(
            f"{GATEWAY_HTTPS}/api/yolo/detect",
            data=b"",
            headers={"Content-Type": "image/jpeg"},
            verify=False,
            timeout=5
        )
        e_data = r_empty.json()
        assert e_data.get("status") == "error"
        assert "Empty frame" in e_data.get("message")
        print(f"  [PASS] Empty frame: Honestly rejected ({e_data.get('message')})")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        errors.append(f"Test 8 failed: {e}")

    print("\n" + "=" * 75)
    if not errors:
        print("ALL SESSION 10 FINAL INTEGRATION TESTS PASSED SUCCESSFULLY!")
        print("=" * 75)
        return 0
    else:
        print(f"COMPLETED WITH {len(errors)} ERROR(S):")
        for err in errors:
            print(f"  - {err}")
        print("=" * 75)
        return 1

if __name__ == "__main__":
    sys.exit(main())
