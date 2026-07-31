import numpy as np
from PIL import Image
from config.dataset import IMAGE_SIZE

def resize_image(image, target_size=IMAGE_SIZE):
    """Resize input image to target dimensions (160x160)."""
    if isinstance(image, Image.Image):
        return image.resize(target_size, Image.BILINEAR)
    elif isinstance(image, np.ndarray):
        try:
            import cv2
            return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)
        except Exception:
            pil_img = Image.fromarray(image)
            return pil_img.resize(target_size, Image.BILINEAR)
    return image

def normalize_image(image_input):
    """Normalize pixel values for FaceNet input (standard float32 scaling)."""
    if isinstance(image_input, Image.Image):
        arr = np.array(image_input, dtype=np.float32)
    else:
        arr = np.float32(image_input)
        
    mean, std = arr.mean(), arr.std()
    std_adj = np.maximum(std, 1.0 / np.sqrt(max(arr.size, 1)))
    return (arr - mean) / std_adj

def prepare_tensor(normalized_image):
    """Convert normalized numpy image array to Tensor or array format (C, H, W)."""
    if isinstance(normalized_image, Image.Image):
        arr = np.array(normalized_image, dtype=np.float32)
    else:
        arr = np.array(normalized_image, dtype=np.float32)

    try:
        import torch
        if len(arr.shape) == 3:
            tensor = torch.from_numpy(arr).permute(2, 0, 1).float()
        else:
            tensor = torch.from_numpy(arr).float()
            
        if len(tensor.shape) == 3:
            tensor = tensor.unsqueeze(0)
        return tensor
    except Exception:
        # Fallback numpy format if PyTorch is not installed
        if len(arr.shape) == 3:
            tensor_arr = np.transpose(arr, (2, 0, 1))
        else:
            tensor_arr = arr
        if len(tensor_arr.shape) == 3:
            tensor_arr = np.expand_dims(tensor_arr, axis=0)
        return tensor_arr
