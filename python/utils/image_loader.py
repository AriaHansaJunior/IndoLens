from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def baca_file_gambar_ke_array(path_file_gambar: str | Path) -> np.ndarray:
    """
    Membaca file gambar dari penyimpanan lokal (JPEG, PNG, WebP, AVIF, BMP) menggunakan OpenCV
    atau PIL lalu mengembalikannya sebagai array piksel BGR numpy.ndarray untuk diproses modul YOLO dan Preprocessing.
    """
    path_str = str(path_file_gambar)
    try:
        gambar_bgr = cv2.imread(path_str, cv2.IMREAD_COLOR)
        if gambar_bgr is not None and gambar_bgr.size > 0:
            return gambar_bgr
    except Exception:
        pass

    try:
        with Image.open(path_str) as gambar_pil:
            array_rgb = np.array(gambar_pil.convert("RGB"), dtype=np.uint8)
            return cv2.cvtColor(array_rgb, cv2.COLOR_RGB2BGR)
    except Exception as galat_baca:
        raise ValueError(f"Gagal membaca file gambar pada lokasi: {path_file_gambar}. Detail: {galat_baca}") from galat_baca


def ubah_format_bgr_ke_rgb(data_gambar) -> np.ndarray:
    """
    Mengubah susunan kanal warna gambar dari format BGR (OpenCV) atau objek PIL menjadi array piksel RGB 3-kanal
    sebelum diubah ukurannya menjadi 160x160 piksel pada python/utils/image_preprocessor.py.
    """
    if isinstance(data_gambar, Image.Image):
        return np.array(data_gambar.convert("RGB"), dtype=np.uint8)

    array_input = np.asarray(data_gambar)
    if array_input.ndim == 2:
        return cv2.cvtColor(array_input, cv2.COLOR_GRAY2RGB)

    if array_input.ndim == 3 and array_input.shape[2] == 4:
        return cv2.cvtColor(array_input, cv2.COLOR_BGRA2RGB)

    if array_input.ndim == 3 and array_input.shape[2] == 3:
        return cv2.cvtColor(array_input, cv2.COLOR_BGR2RGB)

    return array_input


# Menyediakan alias nama fungsi untuk menjaga kompatibilitas pemanggilan modul lama
read_image = baca_file_gambar_ke_array
convert_rgb = ubah_format_bgr_ke_rgb
