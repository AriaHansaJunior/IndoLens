import sys
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import EMBEDDING_PATH
from config.config import FACE_DISTANCE_THRESHOLD
from recognition.euclidean_distance import calculate_distance, calculate_all_distances
from recognition.threshold import verify_threshold, classify_result


def load_actor_embeddings(actor_name, base_path=EMBEDDING_PATH):
    """
    Load all .npy 128-D embedding files for a specific actor.
    
    :param actor_name: str name of actor folder (e.g. 'iqbaal_ramadhan')
    :param base_path: Path or str base directory containing actor embeddings
    :return: list of dicts [{"file": str, "path": str, "embedding": np.ndarray}]
    """
    actor_dir = Path(base_path) / actor_name
    embeddings = []
    if not actor_dir.exists() or not actor_dir.is_dir():
        return embeddings

    for npy_file in sorted(actor_dir.glob("*.npy")):
        try:
            emb = np.load(str(npy_file))
            embeddings.append({
                "file": npy_file.name,
                "path": str(npy_file),
                "embedding": emb
            })
        except Exception as e:
            continue

    return embeddings


def load_all_embeddings(base_path=EMBEDDING_PATH):
    """
    Load all reference actor embeddings from base embedding path.
    
    :param base_path: Path or str base directory of embeddings
    :return: dict mapping actor_name -> list of embedding dicts
    """
    path = Path(base_path)
    all_embeddings = {}
    if not path.exists() or not path.is_dir():
        return all_embeddings

    for item in sorted(path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            actor_name = item.name
            actor_embs = load_actor_embeddings(actor_name, base_path=path)
            if actor_embs:
                all_embeddings[actor_name] = actor_embs

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
    best_actor = best_item["actor"]
    min_distance = best_item["distance"]

    is_below = verify_threshold(min_distance, threshold=threshold)
    return classify_result(best_actor, min_distance, is_below)
