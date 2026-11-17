"""Modul ekstraksi vektor embedding 512-D menggunakan JaringanFaceNetMandiri hasil training sendiri."""

from pathlib import Path
import numpy as np
import torch

from config.config import FILE_BOBOT_HASIL_TRAINING_FACENET
from config.dataset import (
    EMBEDDING_PATH,
    DIMENSI_EMBEDDING_FACENET,
    BATAS_AMBANG_JARAK_EUCLIDEAN,
    UKURAN_RESOLUSI_WAJAH_FACENET,
)
from facenet.arsitektur_facenet_manual import JaringanFaceNetMandiri
from utils.image_loader import baca_file_gambar_ke_array, ubah_format_bgr_ke_rgb
from utils.image_preprocessor import (
    ubah_ukuran_piksel_wajah,
    normalisasi_piksel_standar,
    ubah_array_ke_tensor_chw,
)

# Menyimpan instance model FaceNet hasil training mandiri dan objek device GPU di memori
_MODEL_FACENET_TERLATIH: JaringanFaceNetMandiri | None = None
_PERANGKAT_KOMPUTASI_FACENET: torch.device | None = None


def pilih_perangkat_komputasi_facenet() -> torch.device:
    """
    Memilih perangkat GPU NVIDIA GeForce RTX 4060 Laptop GPU (indeks cuda:0 di PyTorch / GPU 1 di Task Manager)
    agar ekstraksi vektor embedding 512-D berjalan di atas akselerasi CUDA.
    """
    global _PERANGKAT_KOMPUTASI_FACENET
    if _PERANGKAT_KOMPUTASI_FACENET is not None:
        return _PERANGKAT_KOMPUTASI_FACENET

    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        indeks_gpu = 0
        for indeks_uji in range(torch.cuda.device_count()):
            nama_gpu = torch.cuda.get_device_name(indeks_uji).upper()
            if "RTX" in nama_gpu or "NVIDIA" in nama_gpu:
                indeks_gpu = indeks_uji
                break
        _PERANGKAT_KOMPUTASI_FACENET = torch.device(f"cuda:{indeks_gpu}")
    else:
        _PERANGKAT_KOMPUTASI_FACENET = torch.device("cpu")

    return _PERANGKAT_KOMPUTASI_FACENET


def muat_model_hasil_training_facenet(
    path_bobot_facenet: Path | str | None = None,
) -> JaringanFaceNetMandiri:
    """
    Memuat bobot hasil_training_facenet_aktor.pth dari folder storage/app/ai/weights/ ke dalam
    JaringanFaceNetMandiri (torch.nn.Module) yang dilatih dari Epoch 0 dengan Triplet Margin Loss.
    Menolak pemakaian model pre-trained luar apabila file hasil training sendiri belum tersedia.
    """
    global _MODEL_FACENET_TERLATIH

    if _MODEL_FACENET_TERLATIH is not None and path_bobot_facenet is None:
        return _MODEL_FACENET_TERLATIH

    path_target = Path(path_bobot_facenet) if path_bobot_facenet else Path(FILE_BOBOT_HASIL_TRAINING_FACENET)
    if not path_target.exists():
        raise FileNotFoundError(
            f"Bobot hasil training mandiri FaceNet belum ditemukan di: {path_target}\n"
            "Jalankan Notebook_02_Training_Dataset_Wajah_Aktor.ipynb pada folder "
            "training_python/02_training_dataset_wajah_aktor terlebih dahulu."
        )

    perangkat_aktif = pilih_perangkat_komputasi_facenet()
    jaringan_facenet = JaringanFaceNetMandiri(dimensi_embedding=DIMENSI_EMBEDDING_FACENET)

    data_checkpoint = torch.load(str(path_target), map_location=perangkat_aktif, weights_only=False)
    if isinstance(data_checkpoint, dict) and "state_dict_model" in data_checkpoint:
        jaringan_facenet.load_state_dict(data_checkpoint["state_dict_model"])
    elif isinstance(data_checkpoint, dict) and "model_state_dict" in data_checkpoint:
        jaringan_facenet.load_state_dict(data_checkpoint["model_state_dict"])
    else:
        jaringan_facenet.load_state_dict(data_checkpoint)

    jaringan_facenet.to(perangkat_aktif)
    jaringan_facenet.eval()

    _MODEL_FACENET_TERLATIH = jaringan_facenet
    return _MODEL_FACENET_TERLATIH


def ekstrak_vektor_embedding_wajah(
    input_citra_wajah,
    model_facenet_aktif: JaringanFaceNetMandiri | None = None,
    sudah_ternormalisasi: bool = False,
) -> np.ndarray:
    """
    Mengubah potongan gambar wajah (file path, array BGR/RGB, atau tensor 160x160 ternormalisasi)
    menjadi vektor embedding 512-D ternormalisasi L2 (float32) menggunakan JaringanFaceNetMandiri di GPU RTX 4060.
    """
    model_aktif = model_facenet_aktif or muat_model_hasil_training_facenet()
    perangkat_aktif = next(model_aktif.parameters()).device

    if sudah_ternormalisasi and isinstance(input_citra_wajah, np.ndarray):
        array_ternormalisasi = input_citra_wajah.astype(np.float32)
    else:
        if isinstance(input_citra_wajah, (str, Path)):
            citra_bgr = baca_file_gambar_ke_array(input_citra_wajah)
            citra_rgb = ubah_format_bgr_ke_rgb(citra_bgr)
        else:
            citra_rgb = ubah_format_bgr_ke_rgb(input_citra_wajah)

        citra_160x160 = ubah_ukuran_piksel_wajah(
            citra_rgb,
            ukuran_target=UKURAN_RESOLUSI_WAJAH_FACENET,
        )
        array_ternormalisasi = normalisasi_piksel_standar(citra_160x160)

    tensor_masukan = ubah_array_ke_tensor_chw(array_ternormalisasi).to(perangkat_aktif)

    with torch.no_grad():
        vektor_keluaran = model_aktif(tensor_masukan).detach().cpu().numpy().flatten()

    if len(vektor_keluaran) > DIMENSI_EMBEDDING_FACENET:
        vektor_keluaran = vektor_keluaran[:DIMENSI_EMBEDDING_FACENET]
    elif len(vektor_keluaran) < DIMENSI_EMBEDDING_FACENET:
        vektor_keluaran = np.pad(
            vektor_keluaran,
            (0, DIMENSI_EMBEDDING_FACENET - len(vektor_keluaran)),
        )

    panjang_norm_l2 = float(np.linalg.norm(vektor_keluaran))
    if panjang_norm_l2 > 0.0:
        vektor_embedding_wajah = vektor_keluaran / panjang_norm_l2
    else:
        vektor_embedding_wajah = vektor_keluaran

    return vektor_embedding_wajah.astype(np.float32)


def simpan_vektor_embedding_ke_npy(
    vektor_embedding: np.ndarray,
    path_file_output: str | Path,
) -> str:
    """
    Menyimpan array vektor embedding 512-D ke dalam file biner .npy pada folder python/embeddings/.
    """
    path_tujuan = Path(path_file_output)
    path_tujuan.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path_tujuan), np.asarray(vektor_embedding, dtype=np.float32))
    return str(path_tujuan)


def muat_daftar_embedding_aktor(
    nama_slug_aktor: str,
    folder_dasar_embedding: str | Path = EMBEDDING_PATH,
) -> list[dict]:
    """
    Memuat seluruh file vektor referensi .npy milik satu aktor dari folder python/embeddings/<nama_slug_aktor>.
    """
    folder_aktor = Path(folder_dasar_embedding) / nama_slug_aktor
    daftar_embedding_aktor = []
    if not folder_aktor.exists():
        return daftar_embedding_aktor

    for file_npy in sorted(folder_aktor.glob("*.npy")):
        vektor_npy = np.load(str(file_npy))
        daftar_embedding_aktor.append(
            {
                "file": file_npy.name,
                "path": str(file_npy),
                "embedding": vektor_npy,
            }
        )

    return daftar_embedding_aktor


def hitung_jarak_euclidean_vektor(vektor_pertama, vektor_kedua) -> float:
    """
    Menghitung jarak Euclidean (norma L2 dari selisih dua vektor 512-D) menggunakan rumus sqrt(sum((v1 - v2)^2)).
    """
    array_1 = np.asarray(vektor_pertama, dtype=np.float32).flatten()
    array_2 = np.asarray(vektor_kedua, dtype=np.float32).flatten()
    return float(np.linalg.norm(array_1 - array_2))


def cari_kecocokan_aktor_terdekat(
    vektor_wajah_input: np.ndarray,
    kamus_semua_embedding_aktor: dict,
    batas_ambang_jarak: float = BATAS_AMBANG_JARAK_EUCLIDEAN,
) -> dict:
    """
    Mencari identitas aktor dengan jarak Euclidean paling minimum terhadap vektor_wajah_input
    dan membandingkannya terhadap batas_ambang_jarak (threshold).
    """
    aktor_terdekat = None
    jarak_euclidean_minimum = float("inf")

    for nama_aktor, daftar_item in kamus_semua_embedding_aktor.items():
        for item_ref in daftar_item:
            jarak_hitung = hitung_jarak_euclidean_vektor(vektor_wajah_input, item_ref["embedding"])
            if jarak_hitung < jarak_euclidean_minimum:
                jarak_euclidean_minimum = jarak_hitung
                aktor_terdekat = nama_aktor

    if jarak_euclidean_minimum <= batas_ambang_jarak and aktor_terdekat is not None:
        return {
            "actor": aktor_terdekat,
            "distance": round(jarak_euclidean_minimum, 4),
            "recognized": True,
        }

    return {
        "actor": "Unknown",
        "distance": round(jarak_euclidean_minimum, 4),
        "recognized": False,
    }


# Menyediakan alias fungsi untuk menjaga kompatibilitas pemanggilan lintas modul di folder python/
load_facenet_model = muat_model_hasil_training_facenet
generate_embedding = ekstrak_vektor_embedding_wajah
save_embedding = simpan_vektor_embedding_ke_npy
load_actor_embeddings = muat_daftar_embedding_aktor
calculate_euclidean_distance = hitung_jarak_euclidean_vektor
find_best_match = cari_kecocokan_aktor_terdekat
