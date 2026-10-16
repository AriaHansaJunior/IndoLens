"""
Test Distinct Actor Baru Proof:
1. Tests unknown face ('foto Aria Hansa Junior.jpg') -> MUST be Unknown (dist > 0.65).
2. Syncs as new actor 'Aria Hansa Junior' -> MUST become Known ('Aria Hansa Junior', dist <= 0.65).
3. Deletes actor -> MUST return to Unknown (dist > 0.65).
"""

import sys
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
face_path = BASE_DIR / "public" / "img" / "foto Aria Hansa Junior.jpg"
assert face_path.exists(), f"Image not found at {face_path}"

with open(face_path, "rb") as f:
    img_bytes = f.read()

detect_url = "http://127.0.0.1:8002/detect"
sync_url = "http://127.0.0.1:8002/sync-actor-embedding"
del_url = "http://127.0.0.1:8002/delete-actor"

# Step 1: Query face BEFORE registration
print("--- STEP 1: Query face BEFORE registration ---")
req = urllib.request.Request(detect_url, data=img_bytes, headers={'Content-Type': 'image/jpeg'}, method='POST')
with urllib.request.urlopen(req) as resp:
    res1 = json.loads(resp.read().decode('utf-8'))
    faces1 = res1.get("faces", [])
    assert len(faces1) > 0, "No face detected in test image"
    f1 = faces1[0]
    print(f"Result: Actor={f1.get('actor')}, Distance={f1.get('distance')}, Status={f1.get('status')}")
    assert f1.get("status") == "unknown", f"Expected unknown, got {f1.get('status')}"
    assert f1.get("distance") > 0.65, f"Expected distance > 0.65, got {f1.get('distance')}"
    print("[PASS] Unregistered face is correctly classified as UNKNOWN (distance > 0.65)!")

# Step 2: Register as new Actor 'Aria Hansa Junior'
print("\n--- STEP 2: Register new Actor 'Aria Hansa Junior' ---")
sync_payload = json.dumps({
    "actor_id": 500,
    "full_name": "Aria Hansa Junior",
    "images": [
        {
            "image_id": 5001,
            "image_path": str(face_path)
        }
    ]
}).encode('utf-8')

req = urllib.request.Request(sync_url, data=sync_payload, headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    sync_res = json.loads(resp.read().decode('utf-8'))
    print(f"Sync Result: {sync_res}")
    assert sync_res["status"] == "success"
    assert sync_res["actor_slug"] == "aria_hansa_junior"
    assert sync_res["generated_count"] == 1

# Step 3: Query face AFTER registration
print("\n--- STEP 3: Query face AFTER registration ---")
req = urllib.request.Request(detect_url, data=img_bytes, headers={'Content-Type': 'image/jpeg'}, method='POST')
with urllib.request.urlopen(req) as resp:
    res2 = json.loads(resp.read().decode('utf-8'))
    faces2 = res2.get("faces", [])
    assert len(faces2) > 0, "No face detected in test image"
    f2 = faces2[0]
    print(f"Result: Actor={f2.get('actor')}, Distance={f2.get('distance')}, Status={f2.get('status')}")
    assert f2.get("status") == "known", f"Expected known, got {f2.get('status')}"
    assert f2.get("actor") == "Aria Hansa Junior", f"Expected 'Aria Hansa Junior', got {f2.get('actor')}"
    assert f2.get("distance") <= 0.65, f"Expected distance <= 0.65, got {f2.get('distance')}"
    print("[PASS] Newly registered actor is IMMEDIATELY recognized as 'Aria Hansa Junior' (distance <= 0.65)!")

# Step 4: Delete actor and verify returns to unknown
print("\n--- STEP 4: Delete Actor 'Aria Hansa Junior' ---")
del_payload = json.dumps({
    "actor_id": 500,
    "full_name": "Aria Hansa Junior"
}).encode('utf-8')

req = urllib.request.Request(del_url, data=del_payload, headers={'Content-Type': 'application/json'}, method='DELETE')
with urllib.request.urlopen(req) as resp:
    del_res = json.loads(resp.read().decode('utf-8'))
    print(f"Delete Result: {del_res}")
    assert del_res["status"] == "success"

req = urllib.request.Request(detect_url, data=img_bytes, headers={'Content-Type': 'image/jpeg'}, method='POST')
with urllib.request.urlopen(req) as resp:
    res3 = json.loads(resp.read().decode('utf-8'))
    faces3 = res3.get("faces", [])
    f3 = faces3[0]
    print(f"Result: Actor={f3.get('actor')}, Distance={f3.get('distance')}, Status={f3.get('status')}")
    assert f3.get("status") == "unknown", f"Expected unknown after delete, got {f3.get('status')}"
    assert f3.get("distance") > 0.65, f"Expected distance > 0.65 after delete, got {f3.get('distance')}"
    print("[PASS] After deletion, face returns to UNKNOWN (distance > 0.65)!")

print("\n[SUCCESS] PROOF COMPLETE: Generic dynamic CAMP reference pipeline is 100% verified!")
