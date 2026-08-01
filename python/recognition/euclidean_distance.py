import numpy as np

def calculate_distance(embedding1, embedding2):
    """
    Calculate Euclidean distance between two 128-D embedding vectors.
    
    :param embedding1: numpy.ndarray or list representation of embedding
    :param embedding2: numpy.ndarray or list representation of embedding
    :return: float Euclidean distance
    """
    emb1 = np.array(embedding1, dtype=np.float32).flatten()
    emb2 = np.array(embedding2, dtype=np.float32).flatten()
    return float(np.linalg.norm(emb1 - emb2))


def calculate_all_distances(query_embedding, all_actor_embeddings):
    """
    Calculate Euclidean distances between query embedding and all loaded reference actor embeddings.
    
    :param query_embedding: 128-D embedding vector
    :param all_actor_embeddings: dict mapping actor_name -> list of dicts containing 'embedding'
    :return: list of dicts [{"actor": actor_name, "distance": dist, "file": file_name}]
    """
    distances = []
    if not all_actor_embeddings:
        return distances

    for actor_name, emb_list in all_actor_embeddings.items():
        if isinstance(emb_list, list):
            for item in emb_list:
                stored_emb = item["embedding"] if isinstance(item, dict) and "embedding" in item else item
                file_name = item.get("file", "") if isinstance(item, dict) else ""
                dist = calculate_distance(query_embedding, stored_emb)
                distances.append({
                    "actor": actor_name,
                    "distance": dist,
                    "file": file_name
                })
        else:
            dist = calculate_distance(query_embedding, emb_list)
            distances.append({
                "actor": actor_name,
                "distance": dist,
                "file": ""
            })

    return distances
