"""Modul verifikasi batas ambang jarak Euclidean (threshold) dan penentuan status identitas aktor."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import BATAS_AMBANG_JARAK_EUCLIDEAN


def verifikasi_batas_ambang_jarak(
    jarak_euclidean_minimum: float | None,
    batas_ambang_jarak: float = BATAS_AMBANG_JARAK_EUCLIDEAN,
) -> bool:
    """
    Membandingkan jarak_euclidean_minimum terhadap batas_ambang_jarak (threshold).
    Mengembalikan nilai True apabila jarak <= batas_ambang_jarak (dikenali sebagai aktor terdaftar).
    """
    if jarak_euclidean_minimum is None:
        return False
    return bool(float(jarak_euclidean_minimum) <= float(batas_ambang_jarak))


def format_nama_tampilan_aktor(nama_aktor_mentah: str | None) -> str:
    """
    Mengubah nama slug folder aktor (misal 'bayu_eko_moektito') menjadi format huruf kapital ('Bayu Eko Moektito')
    atau mempertahankan nama lengkap asli dari database MySQL untuk ditampilkan pada layar kamera web.
    """
    if not nama_aktor_mentah or nama_aktor_mentah in {"Tidak Dikenali", "Unknown"}:
        return "Tidak Dikenali"
    if "_" not in nama_aktor_mentah and any(karakter.isupper() for karakter in nama_aktor_mentah):
        return nama_aktor_mentah
    return nama_aktor_mentah.replace("_", " ").title()


def klasifikasikan_hasil_pencocokan_wajah(
    nama_aktor_terdekat: str | None,
    jarak_euclidean_minimum: float,
    memenuhi_batas_ambang: bool,
) -> dict:
    """
    Menetapkan keputusan akhir pengenalan wajah:
    - Apabila memenuhi_batas_ambang bernilai True: status = 'known' beserta nama aktor dan nilai jarak.
    - Apabila memenuhi_batas_ambang bernilai False: status = 'unknown' dan nama aktor = 'Tidak Dikenali'.
    """
    if memenuhi_batas_ambang and nama_aktor_terdekat:
        return {
            "actor": format_nama_tampilan_aktor(nama_aktor_terdekat),
            "distance": round(float(jarak_euclidean_minimum), 2),
            "status": "known",
        }

    nilai_jarak_aman = (
        round(float(jarak_euclidean_minimum), 2)
        if jarak_euclidean_minimum != float("inf")
        else 999.0
    )
    return {
        "actor": "Tidak Dikenali",
        "distance": nilai_jarak_aman,
        "status": "unknown",
    }


# Menyediakan alias fungsi untuk menjaga kompatibilitas pemanggilan lintas modul
verify_threshold = verifikasi_batas_ambang_jarak
format_actor_name = format_nama_tampilan_aktor
classify_result = klasifikasikan_hasil_pencocokan_wajah
