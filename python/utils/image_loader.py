from PIL import Image

def read_image(image_path):
    """Read an image file from path using PIL or OpenCV."""
    try:
        img = Image.open(str(image_path))
        img.load()
        return img
    except Exception as e:
        try:
            import cv2
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError(f"Failed to read image at path: {image_path}")
            return img
        except Exception:
            raise ValueError(f"Failed to read image at path: {image_path}. Error: {e}")

def convert_rgb(image):
    """Convert an image to RGB format."""
    if isinstance(image, Image.Image):
        return image.convert("RGB")
    else:
        try:
            import cv2
            if len(image.shape) == 3 and image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception:
            pass
    return image
