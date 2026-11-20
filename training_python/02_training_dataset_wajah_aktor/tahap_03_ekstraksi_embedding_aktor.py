"""Tahap 03 (Dataset Aktor): Ekstraksi vektor reference embedding 512-D (.npy) memakai FaceNet."""

import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np

# Menambahkan root proyek, folder training_python, dan folder python ke sys.path untuk eksekusi Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig
from facenet.embedding_generator import (
    muat_model_hasil_training_facenet,
    ekstrak_vektor_embedding_wajah,
    simpan_vektor_embedding_ke_npy,
)


def kirim_sinyal_reload_ke_yolo_service(url_dasar_service: str = "http://127.0.0.1:8002") -> tuple[bool, str]:
    """
    Mengirim permintaan HTTP POST ke endpoint /reload-embeddings pada python/yolo_service.py
    apabila layanan kamera web sedang berjalan, agar vektor .npy terbaru langsung dimuat ke memori.
    """
    url_target = f"{url_dasar_service.rstrip('/')}/reload-embeddings"
    try:
        permintaan = urllib.request.Request(
            url_target,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(permintaan, timeout=3) as respons:
            if respons.status == 200:
                return True, "Layanan runtime berhasil memuat ulang database embedding."
            return False, f"Status HTTP {respons.status}"
    except (urllib.error.URLError, ConnectionRefusedError, TimeoutError):
        return (
            False,
            "Layanan yolo_service (port 8002) sedang tidak dijalankan (vektor .npy di disk akan dimuat otomatis saat web dinyalakan).",
        )
    except Exception as galat:
        return False, f"Gagal menghubungi layanan runtime: {galat}"


def buat_database_embedding_referensi(
    path_bobot_facenet: Path = konfig.FILE_BOBOT_HASIL_TRAINING_FACENET,
) -> dict:
    """
    Memuat model hasil_training_facenet_aktor.pth (hasil Tahap 02) di GPU RTX 4060,
    menghitung vektor embedding 512-D ternormalisasi L2 untuk setiap foto wajah asli aktor,
    serta menyimpannya ke folder python/embeddings/<slug_aktor>/<image_id>.npy dan manifest.json
    untuk digunakan oleh evaluasi Tahap 04 maupun pengenalan kamera real-time.
    """
    # Mengaktifkan mode output Jupyter unlimited sebelum mengekstrak seluruh vektor embedding referensi 512-D
    konfig.aktifkan_output_notebook_unlimited()
    konfig.pastikan_semua_folder_tersedia()
    path_manifest_crop = konfig.FOLDER_CROP_WAJAH_160X160 / "manifest_preprocessing_wajah.json"
    if not path_manifest_crop.exists():
        raise FileNotFoundError(
            f"Manifest preprocessing wajah belum ditemukan di: {path_manifest_crop}\n"
            "Jalankan Tahap 01 (ekstrak_dan_preprocess_wajah_dataset) terlebih dahulu."
        )

    _, _, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)
    model_facenet = muat_model_hasil_training_facenet(path_bobot_facenet)
    manifest_crop = json.loads(path_manifest_crop.read_text(encoding="utf-8"))

    print("=" * 78)
    print("  TAHAP 03: EKSTRAKSI DATABASE EMBEDDING REFERENSI 512-D (FACENET)")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']}")
    print(f"[*] Bobot FaceNet Digunakan     : {path_bobot_facenet}")
    print(f"[*] Folder Tujuan Embedding     : {konfig.FOLDER_EMBEDDING_PRODUKSI}")

    # Membersihkan folder embedding lama (kecuali .gitkeep) sebelum menulis vektor hasil model baru
    for item_lama in konfig.FOLDER_EMBEDDING_PRODUKSI.iterdir():
        if item_lama.name == ".gitkeep":
            continue
        if item_lama.is_dir():
            shutil.rmtree(item_lama, ignore_errors=True)
        else:
            item_lama.unlink(missing_ok=True)

    waktu_mulai = time.time()
    peta_manifest_produksi: dict[str, dict] = {}
    total_vektor_tersimpan = 0

    for slug_aktor, info_aktor in sorted(manifest_crop.get("aktor", {}).items()):
        daftar_file_npy_aktor = []
        folder_aktor_embedding = konfig.FOLDER_EMBEDDING_PRODUKSI / slug_aktor
        folder_aktor_embedding.mkdir(parents=True, exist_ok=True)

        for indeks_sampel, item_sampel in enumerate(info_aktor.get("sampel_asli", []), start=1):
            path_tensor_npy = Path(item_sampel["path_tensor_npy"])
            if not path_tensor_npy.exists():
                continue

            array_ternormalisasi = np.load(str(path_tensor_npy)).astype(np.float32)
            vektor_embedding_512d = ekstrak_vektor_embedding_wajah(
                array_ternormalisasi,
                model_facenet_aktif=model_facenet,
                sudah_ternormalisasi=True,
            )

            # Memvalidasi integritas matematis vektor 512-D sebelum disimpan ke penyimpanan produksi
            if vektor_embedding_512d.shape != (konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,):
                raise ValueError(f"Dimensi vektor tidak sesuai: {vektor_embedding_512d.shape}")
            if np.isnan(vektor_embedding_512d).any() or np.isinf(vektor_embedding_512d).any():
                raise ValueError(f"Vektor mengandung NaN/Inf pada sampel {path_tensor_npy.name}")

            id_gambar = str(item_sampel.get("image_id") or indeks_sampel)
            nama_file_npy = f"{id_gambar}.npy"
            path_tujuan_npy = folder_aktor_embedding / nama_file_npy
            simpan_vektor_embedding_ke_npy(vektor_embedding_512d, path_tujuan_npy)

            daftar_file_npy_aktor.append(nama_file_npy)
            total_vektor_tersimpan += 1

        if daftar_file_npy_aktor:
            peta_manifest_produksi[slug_aktor] = {
                "actor_id": info_aktor.get("actor_id", 0),
                "full_name": info_aktor.get("full_name", slug_aktor.replace("_", " ").title()),
                "slug": slug_aktor,
                "files": sorted(daftar_file_npy_aktor),
            }

    isi_manifest_produksi = {
        "actors": peta_manifest_produksi,
        "embedding_dim": konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
        "model_source": str(path_bobot_facenet),
        "pretrained_used": False,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    konfig.FILE_MANIFEST_EMBEDDING_PRODUKSI.write_text(
        json.dumps(isi_manifest_produksi, indent=2),
        encoding="utf-8",
    )

    berhasil_reload, pesan_reload = kirim_sinyal_reload_ke_yolo_service()
    durasi_detik = round(time.time() - waktu_mulai, 2)

    ringkasan_ekstraksi_embedding = {
        "status": "berhasil",
        "jumlah_aktor_terdaftar": len(peta_manifest_produksi),
        "total_vektor_embedding_512d": total_vektor_tersimpan,
        "path_folder_embedding": str(konfig.FOLDER_EMBEDDING_PRODUKSI),
        "path_manifest_json": str(konfig.FILE_MANIFEST_EMBEDDING_PRODUKSI),
        "service_reload_aktif": berhasil_reload,
        "catatan_service_reload": pesan_reload,
        "durasi_proses_detik": durasi_detik,
    }

    print(f"[OK] Total aktor memiliki embedding : {len(peta_manifest_produksi)} aktor")
    print(f"[OK] Total file .npy 512-D disimpan : {total_vektor_tersimpan} file")
    print(f"[OK] File manifest.json ditulis ke  : {konfig.FILE_MANIFEST_EMBEDDING_PRODUKSI}")
    print(f"[*] Status sinkronisasi runtime     : {pesan_reload}")

    return ringkasan_ekstraksi_embedding


if __name__ == "__main__":
    buat_database_embedding_referensi()
