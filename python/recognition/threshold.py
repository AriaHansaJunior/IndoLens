import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import FACE_DISTANCE_THRESHOLD


def verify_threshold(distance, threshold=FACE_DISTANCE_THRESHOLD):
    """
    Verify if minimum Euclidean distance satisfies distance threshold constraint.
    
    :param distance: float minimum distance
    :param threshold: float threshold from config (default: FACE_DISTANCE_THRESHOLD)
    :return: bool True if distance <= threshold, False otherwise
    """
    if distance is None:
        return False
    return bool(distance <= threshold)


def format_actor_name(actor_name):
    """Format folder actor name to title case (e.g. 'iqbaal_ramadhan' -> 'Iqbaal Ramadhan')."""
    if not actor_name or actor_name == "Tidak Dikenali":
        return "Tidak Dikenali"
    return actor_name.replace("_", " ").title()


def classify_result(actor_name, min_distance, is_below_threshold):
    """
    Classify facial match result based on threshold verification.
    
    LOCK 1:
    min(distance) <= threshold -> Known (actor_name, status="known")
    min(distance) > threshold -> Tidak Dikenali (actor="Tidak Dikenali", status="unknown")
    
    :param actor_name: raw or formatted name of actor with minimum distance
    :param min_distance: float minimum calculated Euclidean distance
    :param is_below_threshold: bool result of verify_threshold()
    :return: dict classification result {"actor": str, "distance": float, "status": str}
    """
    if is_below_threshold and actor_name:
        return {
            "actor": format_actor_name(actor_name),
            "distance": round(float(min_distance), 2),
            "status": "known"
        }
    else:
        dist_val = round(float(min_distance), 2) if min_distance != float('inf') else 999.0
        return {
            "actor": "Tidak Dikenali",
            "distance": dist_val,
            "status": "unknown"
        }
