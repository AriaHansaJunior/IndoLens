"""Modul perhitungan jarak Euclidean (Euclidean Distance) pada ruang vektor embedding 512-D."""

import numpy as np


def hitung_jarak_euclidean(vektor_input, vektor_referensi) -> float:
    """
    Menghitung jarak Euclidean antara vektor_input (512-D) dan vektor_referensi (512-D)
    menggunakan rumus akar kuadrat dari jumlah selisih kuadrat tiap elemen: sqrt(sum((v1 - v2)^2)).
    Hasil jarak dikirimkan ke modul python/recognition/threshold.py dan embedding_matcher.py.
    """
    array_input = np.asarray(vektor_input, dtype=np.float32).flatten()
    array_referensi = np.asarray(vektor_referensi, dtype=np.float32).flatten()
    selisih_vektor = array_input - array_referensi
    jarak_euclidean = float(np.sqrt(np.sum(selisih_vektor * selisih_vektor)))
    return jarak_euclidean


def hitung_semua_jarak_ke_database(
    vektor_wajah_input: np.ndarray,
    kamus_semua_embedding_aktor: dict,
) -> list[dict]:
    """
    Menghitung jarak Euclidean antara vektor_wajah_input terhadap seluruh file embedding referensi (.npy)
    milik semua aktor yang tersimpan di dalam kamus_semua_embedding_aktor.
    """
    daftar_jarak_terhitung = []
    if not kamus_semua_embedding_aktor:
        return daftar_jarak_terhitung

    for nama_aktor, daftar_item_embedding in kamus_semua_embedding_aktor.items():
        if isinstance(daftar_item_embedding, list):
            for item_ref in daftar_item_embedding:
                vektor_tersimpan = (
                    item_ref["embedding"]
                    if isinstance(item_ref, dict) and "embedding" in item_ref
                    else item_ref
                )
                nama_file_npy = item_ref.get("file", "") if isinstance(item_ref, dict) else ""
                nilai_jarak = hitung_jarak_euclidean(vektor_wajah_input, vektor_tersimpan)
                daftar_jarak_terhitung.append(
                    {
                        "actor": nama_aktor,
                        "distance": nilai_jarak,
                        "file": nama_file_npy,
                    }
                )
        else:
            nilai_jarak = hitung_jarak_euclidean(vektor_wajah_input, daftar_item_embedding)
            daftar_jarak_terhitung.append(
                {
                    "actor": nama_aktor,
                    "distance": nilai_jarak,
                    "file": "",
                }
            )

    return daftar_jarak_terhitung


# Menyediakan alias fungsi untuk menjaga kompatibilitas pemanggilan lintas modul
calculate_distance = hitung_jarak_euclidean
calculate_all_distances = hitung_semua_jarak_ke_database
