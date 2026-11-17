import cv2
import numpy as np
import torch
from PIL import Image

from config.dataset import UKURAN_RESOLUSI_WAJAH_FACENET


def ubah_ukuran_piksel_wajah(
    gambar_input,
    ukuran_target: tuple[int, int] = UKURAN_RESOLUSI_WAJAH_FACENET,
) -> np.ndarray:
    """
    Mengubah ukuran potongan gambar wajah menjadi resolusi standar 160x160 piksel.
    Alasan pemilihan resolusi 160x160 piksel:
    1. Geometri area kotak wajah manusia (dahi ke dagu, telinga kiri ke kanan) memiliki rasio aspek mendekati 1:1.
    2. Pada jaringan CNN FaceNet dengan 5 tahap reduksi spasial (stride 2 / pooling):
       160x160 -> 80x80 -> 40x40 -> 20x20 -> 10x10 -> 5x5.
       Peta fitur akhir berukuran 5x5 menjaga tata letak spasial mata, hidung, dan mulut secara optimal
       sebelum dirangkum oleh Global Average Pooling menjadi vektor 512-D.
    3. Menyeimbangkan ketajaman tekstur biometrik wajah (tidak pecah seperti 64x64)
       dengan kecepatan komputasi real-time di GPU (tidak seberat 224x224 atau 512x512).
    """
    if isinstance(gambar_input, Image.Image):
        array_gambar = np.array(gambar_input.convert("RGB"), dtype=np.uint8)
    else:
        array_gambar = np.asarray(gambar_input, dtype=np.uint8)

    tinggi_asal, lebar_asal = array_gambar.shape[:2]
    lebar_target, tinggi_target = int(ukuran_target[0]), int(ukuran_target[1])

    # Menggunakan interpolasi INTER_AREA saat memperkecil gambar dan INTER_LINEAR saat memperbesar gambar
    metode_interpolasi = (
        cv2.INTER_AREA
        if (tinggi_asal > tinggi_target or lebar_asal > lebar_target)
        else cv2.INTER_LINEAR
    )
    gambar_160x160 = cv2.resize(
        array_gambar,
        (lebar_target, tinggi_target),
        interpolation=metode_interpolasi,
    )
    return gambar_160x160


def normalisasi_piksel_standar(gambar_rgb_160x160) -> np.ndarray:
    """
    Menghitung rata-rata (mean) dan simpangan baku (standard deviation) nilai piksel RGB secara manual,
    lalu menormalisasi setiap piksel menggunakan rumus (piksel - mean) / std_adjusted menjadi float32.
    Normalisasi ini menyamakan distribusi kontras cahaya sebelum masuk ke jaringan FaceNet.
    """
    if isinstance(gambar_rgb_160x160, Image.Image):
        array_piksel = np.array(gambar_rgb_160x160, dtype=np.float32)
    else:
        array_piksel = np.asarray(gambar_rgb_160x160, dtype=np.float32)

    nilai_rata_rata = float(np.mean(array_piksel))
    nilai_simpangan_baku = float(np.std(array_piksel))
    batas_minimum_std = 1.0 / float(np.sqrt(max(array_piksel.size, 1)))
    pembagi_std_aman = max(nilai_simpangan_baku, batas_minimum_std)

    array_ternormalisasi = (array_piksel - nilai_rata_rata) / pembagi_std_aman
    return array_ternormalisasi.astype(np.float32)


def buat_augmentasi_citra_wajah(gambar_rgb_160x160: np.ndarray) -> dict[str, np.ndarray]:
    """
    Menghasilkan variasi augmentasi piksel wajah 160x160 (cermin horizontal, rotasi kemiringan kepala +-8 derajat,
    dan perubahan pencahayaan terang/redup) untuk memperkaya data latih FaceNet Triplet Loss pada Tahap 03 & Tahap 04
    agar model tetap mengenali wajah aktor ketika agak menoleh atau pencahayaan berubah.
    """
    citra_dasar = np.asarray(gambar_rgb_160x160, dtype=np.uint8)
    tinggi_citra, lebar_citra = citra_dasar.shape[:2]
    titik_pusat = (lebar_citra / 2.0, tinggi_citra / 2.0)

    # Membalik piksel secara horizontal (kiri ke kanan) untuk mensimulasikan arah tolehan berlawanan
    citra_flip_horizontal = cv2.flip(citra_dasar, 1)

    # Memutar citra sebesar +8 derajat dan -8 derajat dengan mode pengisian tepi reflektif
    matriks_rotasi_kiri = cv2.getRotationMatrix2D(titik_pusat, 8.0, 1.0)
    citra_rotasi_kiri = cv2.warpAffine(
        citra_dasar,
        matriks_rotasi_kiri,
        (lebar_citra, tinggi_citra),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    matriks_rotasi_kanan = cv2.getRotationMatrix2D(titik_pusat, -8.0, 1.0)
    citra_rotasi_kanan = cv2.warpAffine(
        citra_dasar,
        matriks_rotasi_kanan,
        (lebar_citra, tinggi_citra),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    # Mengatur variasi pencahayaan terang (+15%) dan redup (-15%)
    citra_cahaya_terang = np.clip(citra_dasar.astype(np.float32) * 1.15 + 8.0, 0, 255).astype(np.uint8)
    citra_cahaya_redup = np.clip(citra_dasar.astype(np.float32) * 0.85 - 8.0, 0, 255).astype(np.uint8)

    return {
        "asli": citra_dasar,
        "flip_horizontal": citra_flip_horizontal,
        "rotasi_kiri": citra_rotasi_kiri,
        "rotasi_kanan": citra_rotasi_kanan,
        "cahaya_terang": citra_cahaya_terang,
        "cahaya_redup": citra_cahaya_redup,
    }


def ubah_array_ke_tensor_chw(gambar_ternormalisasi) -> torch.Tensor:
    """
    Mengubah susunan dimensi array gambar ternormalisasi dari (Tinggi, Lebar, Kanal) [160, 160, 3]
    menjadi tensor PyTorch (Batch, Kanal, Tinggi, Lebar) [1, 3, 160, 160] untuk dikirim ke jaringan FaceNet.
    """
    array_float = np.asarray(gambar_ternormalisasi, dtype=np.float32)
    if array_float.ndim == 3:
        tensor_chw = torch.from_numpy(array_float).permute(2, 0, 1).float().unsqueeze(0)
    elif array_float.ndim == 4:
        tensor_chw = torch.from_numpy(array_float).float()
    else:
        tensor_chw = torch.from_numpy(array_float).float().unsqueeze(0)
    return tensor_chw


def proses_lengkap_citra_wajah_ke_tensor(
    gambar_rgb_input,
    ukuran_target: tuple[int, int] = UKURAN_RESOLUSI_WAJAH_FACENET,
) -> torch.Tensor:
    """
    Menjalankan alur preprocessing wajah secara berurutan mulai dari penyekalaan piksel 160x160,
    normalisasi standar, hingga konversi ke tensor PyTorch [1, 3, 160, 160].
    """
    wajah_160x160 = ubah_ukuran_piksel_wajah(gambar_rgb_input, ukuran_target=ukuran_target)
    wajah_ternormalisasi = normalisasi_piksel_standar(wajah_160x160)
    return ubah_array_ke_tensor_chw(wajah_ternormalisasi)


# Menyediakan alias nama fungsi untuk kompatibilitas pemanggilan lintas modul
resize_image = ubah_ukuran_piksel_wajah
normalize_image = normalisasi_piksel_standar
prepare_tensor = ubah_array_ke_tensor_chw
