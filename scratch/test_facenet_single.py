import sys
from pathlib import Path
import cv2
import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent if "__file__" in locals() else Path(r"C:\laragon\www\IndoLens")
for p in [PROJECT_ROOT, PROJECT_ROOT / "training_python", PROJECT_ROOT / "python"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from training_python import tp_config as cfg

from facenet_pytorch import InceptionResnetV1

def test_facenet():
    print("Testing FaceNet InceptionResnetV1...")
    # Dummy / test crop (160, 160, 3)
    dummy_crop = np.random.randint(0, 255, (160, 160, 3), dtype=np.uint8)
    
    # Preprocess (VGGFace2 standardization)
    arr = dummy_crop.astype(np.float32)
    mean = arr.mean()
    std = arr.std()
    std_adj = np.maximum(std, 1.0 / np.sqrt(max(arr.size, 1)))
    normalized = (arr - mean) / std_adj
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    model = InceptionResnetV1(pretrained='vggface2').eval().to(device)
    tensor_chw = torch.from_numpy(normalized).permute(2, 0, 1).float().unsqueeze(0).to(device)
    
    with torch.no_grad():
        raw_output = model(tensor_chw).detach().cpu().numpy().flatten()
    
    raw_128 = raw_output[:128]
    norm = np.linalg.norm(raw_128)
    emb_128 = raw_128 / norm
    
    print(f"[OK] Embedding shape: {emb_128.shape}")
    print(f"[OK] L2 norm: {np.linalg.norm(emb_128):.6f}")
    print(f"[OK] Has NaN: {np.isnan(emb_128).any()} | Has Inf: {np.isinf(emb_128).any()}")

if __name__ == "__main__":
    test_facenet()
