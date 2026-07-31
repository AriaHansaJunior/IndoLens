import os
from pathlib import Path
from config.dataset import DATASET_PATH, SUPPORTED_EXTENSION

def scan_images(actor_folder_path):
    """Scan and return list of supported image file paths inside an actor folder."""
    folder = Path(actor_folder_path)
    if not folder.exists() or not folder.is_dir():
        return []
    
    image_files = []
    for ext in SUPPORTED_EXTENSION:
        image_files.extend(list(folder.glob(f"*.{ext}")))
        image_files.extend(list(folder.glob(f"*.{ext.upper()}")))
    
    return sorted(list(set(image_files)))

def scan_actor(actor_folder_path):
    """Scan single actor folder and return actor summary dict."""
    folder = Path(actor_folder_path)
    actor_name = folder.name.replace("_", " ").title()
    images = scan_images(folder)
    
    return {
        "actor": actor_name,
        "folder_name": folder.name,
        "images": len(images),
        "folder": str(folder.relative_to(DATASET_PATH.parent.parent)),
        "image_paths": [str(p) for p in images]
    }

def scan_dataset(dataset_path=DATASET_PATH):
    """Scan full actors dataset directory and return summary list."""
    base = Path(dataset_path)
    if not base.exists():
        return []
    
    actors_summary = []
    for entry in sorted(base.iterdir()):
        if entry.is_dir():
            summary = scan_actor(entry)
            actors_summary.append(summary)
            
    return actors_summary
