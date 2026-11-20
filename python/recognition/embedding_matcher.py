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


def hitung_jarak_gabungan_per_aktor(
    vektor_wajah_input: np.ndarray,
    daftar_embedding_aktor: list[dict] | np.ndarray,
    jumlah_topk: int = 3,
    kecualikan_file_npy: set[str] | None = None,
) -> float | None:
    """
    Menghitung skor jarak Euclidean gabungan (50% jarak ke centroid L2 aktor + 50% rata-rata
    Top-K jarak terdekat) agar satu foto outlier tidak memicu salah deteksi wajah Unknown.
    """
    kumpulan_vektor: list[np.ndarray] = []
    daftar_jarak_individu: list[float] = []

    if isinstance(daftar_embedding_aktor, list):
        for item_ref in daftar_embedding_aktor:
            if isinstance(item_ref, dict):
                nama_file = str(item_ref.get("file", ""))
                if kecualikan_file_npy and nama_file in kecualikan_file_npy:
                    continue
                vektor_ref = np.asarray(item_ref["embedding"], dtype=np.float32).flatten()
            else:
                vektor_ref = np.asarray(item_ref, dtype=np.float32).flatten()

            kumpulan_vektor.append(vektor_ref)
            daftar_jarak_individu.append(hitung_jarak_euclidean(vektor_wajah_input, vektor_ref))
    else:
        vektor_ref = np.asarray(daftar_embedding_aktor, dtype=np.float32).flatten()
        kumpulan_vektor.append(vektor_ref)
        daftar_jarak_individu.append(hitung_jarak_euclidean(vektor_wajah_input, vektor_ref))

    if not kumpulan_vektor:
        return None

    if len(kumpulan_vektor) == 1:
        return float(daftar_jarak_individu[0])

    # Membentuk vektor pusat (centroid) ternormalisasi L2 dari seluruh foto referensi aktor
    matriks_vektor = np.stack(kumpulan_vektor, axis=0)
    vektor_centroid = np.mean(matriks_vektor, axis=0)
    norma_centroid = float(np.linalg.norm(vektor_centroid))
    if norma_centroid > 0.0:
        vektor_centroid = vektor_centroid / norma_centroid

    jarak_ke_centroid = hitung_jarak_euclidean(vektor_wajah_input, vektor_centroid)
    daftar_jarak_individu.sort()
    k_efektif = min(max(1, int(jumlah_topk)), len(daftar_jarak_individu))
    rata_jarak_topk = float(np.mean(daftar_jarak_individu[:k_efektif]))
    kuantil_25_jarak = float(np.percentile(daftar_jarak_individu, 25))

    return float((0.45 * jarak_ke_centroid) + (0.35 * rata_jarak_topk) + (0.20 * kuantil_25_jarak))


def cari_kecocokan_aktor_terdekat(
    vektor_wajah_input: np.ndarray,
    kamus_semua_embedding_aktor: dict,
    batas_ambang_jarak: float = BATAS_AMBANG_JARAK_EUCLIDEAN,
    kecualikan_file_npy: set[str] | None = None,
    selisih_margin_terdekat: float = 0.06,
    jumlah_topk: int = 3,
) -> dict:
    """
    Mencari aktor dengan skor jarak Euclidean gabungan (centroid + Top-K) paling minimum,
    memverifikasi terhadap batas_ambang_jarak serta selisih jarak terhadap kandidat kedua
    agar wajah asing yang berada di tengah-tengah dua aktor ditolak sebagai Tidak Dikenali.
    """
    if vektor_wajah_input is None or len(vektor_wajah_input) == 0:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    if not kamus_semua_embedding_aktor:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    daftar_skor_aktor: list[tuple[float, str]] = []
    for kunci_aktor, daftar_item in kamus_semua_embedding_aktor.items():
        skor_jarak_aktor = hitung_jarak_gabungan_per_aktor(
            vektor_wajah_input,
            daftar_item,
            jumlah_topk=jumlah_topk,
            kecualikan_file_npy=kecualikan_file_npy,
        )
        if skor_jarak_aktor is not None:
            daftar_skor_aktor.append((skor_jarak_aktor, kunci_aktor))

    if not daftar_skor_aktor:
        return klasifikasikan_hasil_pencocokan_wajah(None, float("inf"), False)

    daftar_skor_aktor.sort(key=lambda item: item[0])
    jarak_euclidean_minimum, kunci_aktor_terbaik = daftar_skor_aktor[0]

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

    # Memastikan kandidat terbaik unggul jelas dari kandidat kedua bila terdapat lebih dari 1 aktor
    if lolos_ambang and len(daftar_skor_aktor) >= 2 and selisih_margin_terdekat > 0.0:
        jarak_kandidat_kedua = daftar_skor_aktor[1][0]
        if (jarak_kandidat_kedua - jarak_euclidean_minimum) < float(selisih_margin_terdekat):
            lolos_ambang = False

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
