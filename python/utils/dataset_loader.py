from pathlib import Path
from config.dataset import DATASET_PATH
from utils.dataset_scanner import scan_images

def load_images(actor_folder_path):
    """Load image paths for a given actor folder."""
    return scan_images(actor_folder_path)

def load_actor(actor_folder_path):
    """Load actor data including folder path and image list."""
    folder = Path(actor_folder_path)
    if not folder.exists():
        return None
    return {
        "actor_name": folder.name,
        "folder": folder,
        "images": load_images(folder)
    }

def load_dataset(dataset_path=DATASET_PATH):
    """Load all valid actor dataset structures."""
    base = Path(dataset_path)
    dataset = {}
    if not base.exists():
        return dataset
        
    for folder in sorted(base.iterdir()):
        if folder.is_dir():
            dataset[folder.name] = load_actor(folder)
            
    return dataset
