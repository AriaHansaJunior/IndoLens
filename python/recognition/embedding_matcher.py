"""Modul pencocokan vektor embedding wajah kamera terhadap database embedding referensi (.npy) di python/embeddings/."""

import json
import sys
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.dataset import (
    EMBEDDING_PATH,
    DIMENSI_EMBEDDING_FACENET,
    BATAS_AMBANG_JARAK_EUCLIDEAN,
)
from recognition.euclidean_distance import (
    hitung_jarak_euclidean,
    hitung_semua_jarak_ke_database,
)
from recognition.threshold import (
    verifikasi_batas_ambang_jarak,
    klasifikasikan_hasil_pencocokan_wajah,
)


def muat_embedding_satu_aktor(
    nama_slug_aktor: str,
    folder_dasar_embedding: str | Path = EMBEDDING_PATH,
    daftar_file_diizinkan: set | list | None = None,
    nama_lengkap_aktor: str | None = None,
) -> list[dict]:
    """
    Membaca seluruh file vektor .npy (512-D) milik satu aktor dari folder python/embeddings/<nama_slug_aktor>
    beserta nama lengkap aktor dari manifest.json.
    """
    folder_aktor = Path(folder_dasar_embedding) / nama_slug_aktor
    daftar_embedding = []
    if not folder_aktor.exists() or not folder_aktor.is_dir():
        return daftar_embedding

    for file_npy in sorted(folder_aktor.glob("*.npy")):
        if daftar_file_diizinkan is not None and file_npy.name not in daftar_file_diizinkan:
            continue
        try:
            vektor_npy = np.load(str(file_npy))
            if len(vektor_npy) == DIMENSI_EMBEDDING_FACENET:
                daftar_embedding.append(
                    {
                        "file": file_npy.name,
                        "path": str(file_npy),
                        "embedding": vektor_npy,
                        "full_name": nama_lengkap_aktor or nama_slug_aktor.replace("_", " ").title(),
                    }
                )
        except Exception:
            continue

    return daftar_embedding


def muat_semua_database_embedding_aktor(
    folder_dasar_embedding: str | Path = EMBEDDING_PATH,
) -> dict[str, list[dict]]:
    """
    Memuat seluruh embedding referensi (.npy) untuk semua aktor yang terdaftar di python/embeddings/manifest.json
    ke dalam memori untuk pencocokan Euclidean Distance pada evaluasi maupun kamera real-time.
    """
    path_dasar = Path(folder_dasar_embedding)
    kamus_semua_embedding: dict[str, list[dict]] = {}
    if not path_dasar.exists() or not path_dasar.is_dir():
        return kamus_semua_embedding

    file_manifest = path_dasar / "manifest.json"
    data_aktor_manifest = {}
    if file_manifest.exists():
        try:
            isi_json = json.loads(file_manifest.read_text(encoding="utf-8"))
            data_aktor_manifest = isi_json.get("actors", {})
        except Exception:
            data_aktor_manifest = {}

    for item_folder in sorted(path_dasar.iterdir()):
        if item_folder.is_dir() and not item_folder.name.startswith("."):
            slug_aktor = item_folder.name
            meta_aktor = (
                data_aktor_manifest.get(slug_aktor, {})
                if isinstance(data_aktor_manifest, dict)
                else {}
            )
            nama_lengkap = meta_aktor.get("full_name")
            file_aktif = meta_aktor.get("files")
            set_file_aktif = set(file_aktif) if isinstance(file_aktif, list) and file_aktif else None

            koleksi_embedding_aktor = muat_embedding_satu_aktor(
                slug_aktor,
                folder_dasar_embedding=path_dasar,
                daftar_file_diizinkan=set_file_aktif,
                nama_lengkap_aktor=nama_lengkap,
            )
            if koleksi_embedding_aktor:
                kamus_semua_embedding[slug_aktor] = koleksi_embedding_aktor

    return kamus_semua_embedding


def bandingkan_dua_vektor_embedding(vektor_input: np.ndarray, vektor_target: np.ndarray) -> float:
    """
    Menghitung jarak Euclidean antara dua vektor embedding 512-D melalui modul euclidean_distance.py.
    """
    return hitung_jarak_euclidean(vektor_input, vektor_target)


def cari_kecocokan_aktor_terdekat(
    vektor_wajah_input: np.ndarray,
    kamus_semua_embedding_aktor: dict,
    batas_ambang_jarak: float = BATAS_AMBANG_JARAK_EUCLIDEAN,
) -> dict:
    """
    Mencari jarak Euclidean paling minimum antara vektor_wajah_input terhadap seluruh embedding referensi aktor,
    lalu memverifikasi apakah jarak minimum tersebut berada di bawah batas_ambang_jarak (threshold).
    """
    if vektor_wajah_input is None or len(vektor_wajah_input) == 0:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    if not kamus_semua_embedding_aktor:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    semua_jarak = hitung_semua_jarak_ke_database(vektor_wajah_input, kamus_semua_embedding_aktor)
    if not semua_jarak:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    item_terdekat = min(semua_jarak, key=lambda x: x["distance"])
    kunci_aktor_terbaik = item_terdekat["actor"]
    jarak_euclidean_minimum = float(item_terdekat["distance"])

    nama_tampilan_aktor = kunci_aktor_terbaik
    daftar_milik_aktor = kamus_semua_embedding_aktor.get(kunci_aktor_terbaik, [])
    if daftar_milik_aktor and isinstance(daftar_milik_aktor, list):
        item_pertama = daftar_milik_aktor[0]
        if isinstance(item_pertama, dict) and item_pertama.get("full_name"):
            nama_tampilan_aktor = item_pertama["full_name"]

    lolos_ambang = verifikasi_batas_ambang_jarak(
        jarak_euclidean_minimum,
        batas_ambang_jarak=batas_ambang_jarak,
    )
    return klasifikasikan_hasil_pencocokan_wajah(
        nama_tampilan_aktor,
        jarak_euclidean_minimum,
        lolos_ambang,
    )


# Menyediakan alias fungsi untuk menjaga kompatibilitas pemanggilan di yolo_service.py dan modul lainnya
load_actor_embeddings = muat_embedding_satu_aktor
load_all_embeddings = muat_semua_database_embedding_aktor
compare_embedding = bandingkan_dua_vektor_embedding
find_best_match = cari_kecocokan_aktor_terdekat
