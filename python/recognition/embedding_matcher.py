import sys
import json
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import EMBEDDING_PATH, FACENET_EMBEDDING_DIM, FACE_DISTANCE_THRESHOLD
from recognition.euclidean_distance import calculate_distance, calculate_all_distances
from recognition.threshold import verify_threshold, classify_result


def load_actor_embeddings(actor_name, base_path=EMBEDDING_PATH, allowed_files=None, full_name=None):
    """Load valid FaceNet reference embeddings (.npy) for a specific actor."""
    actor_dir = Path(base_path) / actor_name
    embeddings = []
    if not actor_dir.exists() or not actor_dir.is_dir():
        return embeddings

    for npy_file in sorted(actor_dir.glob("*.npy")):
        if allowed_files is not None and npy_file.name not in allowed_files:
            continue
        try:
            emb = np.load(str(npy_file))
            if len(emb) == FACENET_EMBEDDING_DIM:
                embeddings.append({
                    "file": npy_file.name,
                    "path": str(npy_file),
                    "embedding": emb,
                    "full_name": full_name or actor_name.replace("_", " ").title()
                })
        except Exception:
            continue

    return embeddings


def load_all_embeddings(base_path=EMBEDDING_PATH):
    """
    Load all reference actor embeddings from base embedding path.
    If manifest.json exists, enriches actor records with real MySQL full_name.
    
    :param base_path: Path or str base directory of embeddings
    :return: dict mapping actor_name -> list of embedding dicts
    """
    path = Path(base_path)
    all_embeddings = {}
    if not path.exists() or not path.is_dir():
        return all_embeddings

    manifest_file = path / "manifest.json"
    manifest_actors = {}
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
                manifest_actors = manifest_data.get("actors", {})
        except Exception:
            manifest_actors = {}

    for item in sorted(path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            actor_slug = item.name
            meta = manifest_actors.get(actor_slug, {}) if isinstance(manifest_actors, dict) else {}
            full_name = meta.get("full_name")
            actor_embs = load_actor_embeddings(
                actor_slug,
                base_path=path,
                full_name=full_name
            )
            if actor_embs:
                all_embeddings[actor_slug] = actor_embs

    return all_embeddings


def compare_embedding(query_embedding, target_embedding):
    """
    Compare two 128-D embedding vectors using Euclidean Distance.
    
    :param query_embedding: numpy.ndarray
    :param target_embedding: numpy.ndarray
    :return: float Euclidean distance
    """
    return calculate_distance(query_embedding, target_embedding)


def find_best_match(query_embedding, all_actor_embeddings, threshold=FACE_DISTANCE_THRESHOLD):
    """
    Find closest matching actor embedding via minimum Euclidean distance across ALL loaded actor embeddings.
    
    LOCK 7: Compare against ALL embeddings.
    LOCK 1: min(distance) <= threshold -> Known; min(distance) > threshold -> Tidak Dikenali
    
    :param query_embedding: 128-D query embedding numpy array
    :param all_actor_embeddings: dict of loaded actor embeddings
    :param threshold: float distance threshold
    :return: dict classification result {"actor": str, "distance": float, "status": str}
    """
    if query_embedding is None or len(query_embedding) == 0:
        return classify_result(None, float('inf'), False)

    if not all_actor_embeddings:
        return classify_result(None, float('inf'), False)

    all_distances = calculate_all_distances(query_embedding, all_actor_embeddings)
    if not all_distances:
        return classify_result(None, float('inf'), False)

    # Find global minimum distance item
    best_item = min(all_distances, key=lambda x: x["distance"])
    best_actor_key = best_item["actor"]
    min_distance = best_item["distance"]

    # Use the real MySQL full_name if recorded on the embedding item
    actor_display_name = best_actor_key
    actor_list = all_actor_embeddings.get(best_actor_key, [])
    if actor_list and isinstance(actor_list, list) and len(actor_list) > 0:
        first_item = actor_list[0]
        if isinstance(first_item, dict) and "full_name" in first_item and first_item["full_name"]:
            actor_display_name = first_item["full_name"]

    is_below = verify_threshold(min_distance, threshold=threshold)
    return classify_result(actor_display_name, min_distance, is_below)
