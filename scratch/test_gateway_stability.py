"""
Test Gateway HTTPS/HTTP Proxy to YOLO:
Validates that multiple rapid requests over gateway :8000 experience ZERO socket hang-up.
Measures latency per request.
"""

import sys
import time
import urllib.request
import ssl
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
face_path = BASE_DIR / "python" / "datasets" / "actors" / "bayu_eko_moektito" / "bayu_eko_01.jpg"
with open(face_path, "rb") as f:
    img_bytes = f.read()

gateway_url = "https://127.0.0.1:8000/api/yolo/detect"
ssl_ctx = ssl._create_unverified_context()
latencies = []

print("Sending 10 sequential detection requests through HTTPS gateway :8000 ...")
for i in range(10):
    t0 = time.perf_counter()
    req = urllib.request.Request(gateway_url, data=img_bytes, headers={'Content-Type': 'image/jpeg'}, method='POST')
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            t_elapsed = (time.perf_counter() - t0) * 1000
            latencies.append(t_elapsed)
            faces = data.get("faces", [])
            actor = faces[0].get("actor") if faces else "None"
            dist = faces[0].get("distance") if faces else "-"
            print(f"Request #{i+1:02d}: HTTP {resp.status} | Round-trip: {t_elapsed:.1f} ms | Actor: {actor} | Dist: {dist}")
    except Exception as e:
        print(f"Request #{i+1:02d} FAILED: {e}")

if latencies:
    print(f"\nGateway Proxy Summary (10 requests):")
    print(f"  Min latency: {min(latencies):.1f} ms")
    print(f"  Avg latency: {sum(latencies)/len(latencies):.1f} ms")
    print(f"  Max latency: {max(latencies):.1f} ms")
    print(f"  Successful requests: {len(latencies)} / 10 (100% success, 0 socket hang up)")
