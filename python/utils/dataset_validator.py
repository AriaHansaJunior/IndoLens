import os
from pathlib import Path
from config.dataset import DATASET_PATH, SUPPORTED_EXTENSION, MINIMUM_IMAGES

def count_images(actor_folder_path):
    """Count number of valid image files in actor folder."""
    folder = Path(actor_folder_path)
    if not folder.exists() or not folder.is_dir():
        return 0
    count = 0
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lstrip('.').lower() in SUPPORTED_EXTENSION:
            count += 1
    return count

def validate_images(actor_folder_path):
    """Validate all files inside an actor folder ensuring no invalid files exist."""
    folder = Path(actor_folder_path)
    errors = []
    
    for file_path in folder.iterdir():
        if file_path.is_dir():
            errors.append(f"Subfolder '{file_path.name}' found inside actor folder.")
        elif file_path.suffix.lstrip('.').lower() not in SUPPORTED_EXTENSION:
            errors.append(f"Unsupported file '{file_path.name}' found.")
            
    return len(errors) == 0, errors

def validate_actor_folder(actor_folder_path):
    """Validate single actor folder against dataset rules."""
    folder = Path(actor_folder_path)
    if not folder.exists():
        return False, ["Folder does not exist."]
    if not folder.is_dir():
        return False, ["Path is not a directory."]
        
    img_count = count_images(folder)
    if img_count < MINIMUM_IMAGES:
        return False, [f"Insufficient images: found {img_count}, minimum required is {MINIMUM_IMAGES}."]
        
    valid_imgs, img_errors = validate_images(folder)
    if not valid_imgs:
        return False, img_errors
        
    return True, []

def validate_dataset(dataset_path=DATASET_PATH):
    """Validate entire dataset structure."""
    base = Path(dataset_path)
    report = {
        "valid": True,
        "errors": [],
        "actors": {}
    }
    
    if not base.exists() or not base.is_dir():
        report["valid"] = False
        report["errors"].append("Base dataset path does not exist.")
        return report
        
    subfolders = [p for p in base.iterdir() if p.is_dir()]
    if len(subfolders) == 0:
        report["valid"] = False
        report["errors"].append("No actor folders found in dataset.")
        return report
        
    for folder in subfolders:
        is_valid, errors = validate_actor_folder(folder)
        report["actors"][folder.name] = {
            "valid": is_valid,
            "errors": errors,
            "image_count": count_images(folder)
        }
        if not is_valid:
            report["valid"] = False
            
    return report
