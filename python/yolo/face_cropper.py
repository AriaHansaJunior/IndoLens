import numpy as np


def potong_kotak_wajah_dengan_margin(
    frame_gambar: np.ndarray,
    koordinat_bbox: list | tuple,
    rasio_margin: float = 0.12,
) -> np.ndarray:
    """
    Memotong area wajah dari array piksel frame_gambar berdasarkan koordinat_bbox [x1, y1, x2, y2]
    yang dikirim oleh python/yolo/detector.py dengan tambahan ruang tepi (rasio_margin 12%).
    Margin tambahan menjaga agar dahi, dagu, dan kontur pipi saat wajah agak menoleh tidak terpotong
    sebelum dikirim ke python/utils/image_preprocessor.py dan jaringan FaceNet.
    """
    if frame_gambar is None or not isinstance(frame_gambar, np.ndarray):
        raise ValueError("Input frame_gambar tidak valid: harus berupa numpy.ndarray")

    x1_asli, y1_asli, x2_asli, y2_asli = [float(nilai) for nilai in koordinat_bbox]
    tinggi_frame, lebar_frame = frame_gambar.shape[:2]

    lebar_kotak = max(1.0, x2_asli - x1_asli)
    tinggi_kotak = max(1.0, y2_asli - y1_asli)

    tambahan_horizontal = lebar_kotak * max(0.0, float(rasio_margin))
    tambahan_vertikal = tinggi_kotak * max(0.0, float(rasio_margin))

    x1_margin = max(0, min(int(round(x1_asli - tambahan_horizontal)), lebar_frame))
    y1_margin = max(0, min(int(round(y1_asli - tambahan_vertikal)), tinggi_frame))
    x2_margin = max(0, min(int(round(x2_asli + tambahan_horizontal)), lebar_frame))
    y2_margin = max(0, min(int(round(y2_asli + tambahan_vertikal)), tinggi_frame))

    if x2_margin <= x1_margin or y2_margin <= y1_margin:
        return np.empty((0, 0, 3), dtype=frame_gambar.dtype)

    potongan_piksel_wajah = frame_gambar[y1_margin:y2_margin, x1_margin:x2_margin]
    return konversi_ke_array_numpy(potongan_piksel_wajah)


def validasi_potongan_wajah(
    array_potongan_wajah: np.ndarray,
    ukuran_minimum_piksel: int = 16,
) -> bool:
    """
    Memeriksa apakah hasil potongan piksel wajah memiliki dimensi tinggi dan lebar yang valid
    sebelum diteruskan ke tahap normalisasi piksel 160x160.
    """
    if array_potongan_wajah is None or not isinstance(array_potongan_wajah, np.ndarray):
        return False

    if array_potongan_wajah.size == 0 or array_potongan_wajah.ndim < 2:
        return False

    tinggi_potongan, lebar_potongan = array_potongan_wajah.shape[:2]
    return tinggi_potongan >= ukuran_minimum_piksel and lebar_potongan >= ukuran_minimum_piksel


def konversi_ke_array_numpy(objek_gambar) -> np.ndarray:
    """
    Mengubah objek gambar potongan wajah menjadi numpy.ndarray yang salinannya terpisah di memori.
    """
    if isinstance(objek_gambar, np.ndarray):
        return objek_gambar.copy()
    return np.asarray(objek_gambar)


# Menyediakan alias nama fungsi untuk menjaga kompatibilitas pemanggilan lintas modul di folder python/yolo
crop_face = potong_kotak_wajah_dengan_margin
validate_crop = validasi_potongan_wajah
convert_numpy = konversi_ke_array_numpy
