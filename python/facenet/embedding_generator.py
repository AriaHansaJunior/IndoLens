import os
from pathlib import Path
import numpy as np
from config.dataset import EMBEDDING_PATH, FACENET_EMBEDDING_DIM, FACE_DISTANCE_THRESHOLD
from utils.image_loader import read_image, convert_rgb
from utils.image_preprocessor import resize_image, normalize_image, prepare_tensor

_FACENET_MODEL = None

def load_facenet_model():
    """Load official FaceNet InceptionResnetV1 pretrained model (vggface2)."""
    global _FACENET_MODEL
    if _FACENET_MODEL is not None:
        return _FACENET_MODEL

    try:
        import torch
        from facenet_pytorch import InceptionResnetV1
        model = InceptionResnetV1(pretrained='vggface2').eval()
        _FACENET_MODEL = model
        return _FACENET_MODEL
    except Exception as e:
        raise RuntimeError(f"FaceNet model gagal dimuat: {e}")

def generate_embedding(image_input):
    """Generate 128-dimensional L2-normalized FaceNet embedding vector.
    
    Accepts:
    - Path or string to an image file
    - Numpy array (e.g. cropped face bounding box from YOLO)
    - PIL Image object
    """
    model = load_facenet_model()
    
    if isinstance(image_input, (str, Path)):
        img = read_image(image_input)
        img_rgb = convert_rgb(img)
    else:
        img_rgb = convert_rgb(image_input)

    resized = resize_image(img_rgb)
    normalized = normalize_image(resized)
    tensor = prepare_tensor(normalized)

    import torch
    with torch.no_grad():
        if not isinstance(tensor, torch.Tensor):
            tensor = torch.from_numpy(tensor).float()
        raw_embedding = model(tensor).detach().cpu().numpy().flatten()

    # Truncate or pad if dimension differs from FACENET_EMBEDDING_DIM
    if len(raw_embedding) > FACENET_EMBEDDING_DIM:
        raw_embedding = raw_embedding[:FACENET_EMBEDDING_DIM]
    elif len(raw_embedding) < FACENET_EMBEDDING_DIM:
        raw_embedding = np.pad(raw_embedding, (0, FACENET_EMBEDDING_DIM - len(raw_embedding)))

    # L2 normalize embedding vector
    norm = np.linalg.norm(raw_embedding)
    if norm > 0:
        embedding = raw_embedding / norm
    else:
        embedding = raw_embedding

    return embedding.astype(np.float32)

def save_embedding(embedding, output_path):
    """Save 128D embedding numpy array to .npy file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path), embedding)
    return str(path)

def load_actor_embeddings(actor_name, base_embedding_path=EMBEDDING_PATH):
    """Load all .npy embedding files for a given actor."""
    actor_dir = Path(base_embedding_path) / actor_name
    embeddings = []
    if not actor_dir.exists():
        return embeddings

    for npy_file in sorted(actor_dir.glob("*.npy")):
        emb = np.load(str(npy_file))
        embeddings.append({
            "file": npy_file.name,
            "path": str(npy_file),
            "embedding": emb
        })

    return embeddings

def calculate_euclidean_distance(embedding1, embedding2):
    """Calculate Euclidean distance between two embedding vectors."""
    emb1 = np.array(embedding1).flatten()
    emb2 = np.array(embedding2).flatten()
    return float(np.linalg.norm(emb1 - emb2))

def find_best_match(query_embedding, all_actor_embeddings, threshold=FACE_DISTANCE_THRESHOLD):
    """Find closest actor match using minimum Euclidean distance against threshold."""
    best_match = None
    min_distance = float('inf')

    for actor_name, emb_list in all_actor_embeddings.items():
        for item in emb_list:
            dist = calculate_euclidean_distance(query_embedding, item["embedding"])
            if dist < min_distance:
                min_distance = dist
                best_match = actor_name

    if min_distance <= threshold:
        return {
            "actor": best_match,
            "distance": round(min_distance, 4),
            "recognized": True
        }
    else:
        return {
            "actor": "Unknown",
            "distance": round(min_distance, 4),
            "recognized": False
        }
