import os
import sys
from pathlib import Path
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(r"C:\laragon\www\IndoLens")
for p in [PROJECT_ROOT, PROJECT_ROOT / "training_python", PROJECT_ROOT / "python"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from training_python import tp_config as cfg
from training_python import tp_database as db
from training_python.tp_dataset_loader import resolve_image_path, load_image_bgr

def run_checks():
    print("=== PRE-FLIGHT VERIFICATION: MYSQL & STORAGE ===")
    
    # 1. Connection check
    try:
        conn = db.get_readonly_connection()
        print("[OK] MySQL connection successful (READ ONLY confirmed)")
    except Exception as e:
        print(f"[FAIL] MySQL connection failed: {e}")
        return

    cursor = conn.cursor(dictionary=True)

    # 2. Schema check for actors & actor_images
    try:
        cursor.execute("DESCRIBE actors")
        actors_cols = cursor.fetchall()
        print("\nSchema `actors`:")
        for col in actors_cols:
            print(f"  - {col['Field']} ({col['Type']}, Null={col['Null']}, Key={col['Key']})")

        cursor.execute("DESCRIBE actor_images")
        img_cols = cursor.fetchall()
        print("\nSchema `actor_images`:")
        for col in img_cols:
            print(f"  - {col['Field']} ({col['Type']}, Null={col['Null']}, Key={col['Key']})")
    except Exception as e:
        print(f"[FAIL] Failed to inspect schema: {e}")

    # 3. Actor count & sample mapping
    try:
        actors = db.fetch_registered_actors()
        print(f"\n[OK] Total registered actors: {len(actors)}")
        for a in actors:
            print(f"  * Actor ID {a['id']}: '{a['full_name']}'")
    except Exception as e:
        print(f"[FAIL] Failed to fetch registered actors: {e}")

    # 4. Fetch all image records
    try:
        records = db.fetch_actor_image_records()
        print(f"\n[OK] Total image records linked to actors: {len(records)}")
    except Exception as e:
        print(f"[FAIL] Failed to fetch image records: {e}")
        records = []

    # 5. Check path resolution and readability on disk
    if records:
        print("\nChecking file existence and readability against Laravel storage:")
        readable_count = 0
        missing_count = 0
        sample_results = []
        
        for i, rec in enumerate(records):
            rel_path = rec["relative_image_path"]
            resolved, err = resolve_image_path(rel_path)
            
            if err or resolved is None:
                missing_count += 1
                if i < 5:
                    sample_results.append((rec, None, None, err))
            else:
                # Test reading image
                img, read_err = load_image_bgr(resolved)
                if read_err or img is None:
                    missing_count += 1
                    if i < 5:
                        sample_results.append((rec, resolved, None, read_err))
                else:
                    readable_count += 1
                    if i < 5:
                        sample_results.append((rec, resolved, img.shape, "OK"))

        print(f"  * Total records: {len(records)}")
        print(f"  * Files found & readable on disk: {readable_count}")
        print(f"  * Files missing or unreadable: {missing_count}")
        
        print("\nSamples inspection (first up to 5):")
        for rec, path, shape, status in sample_results:
            print(f"  - ID {rec['image_id']} (Actor: '{rec['full_name']}'):")
            print(f"    DB relative path : {rec['relative_image_path']}")
            print(f"    Resolved path   : {path}")
            print(f"    Shape / Status  : {shape} | {status}")
            
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_checks()
