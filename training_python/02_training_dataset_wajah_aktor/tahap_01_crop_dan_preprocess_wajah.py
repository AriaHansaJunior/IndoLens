"""Tahap 03: Deteksi kotak wajah dengan YOLOv8 mandiri, pemotongan margin 12%, augmentasi, dan normalisasi 160x160."""

import json
import re
import shutil
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Menambahkan root proyek, folder training_python, dan folder python ke sys.path untuk eksekusi Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig
from yolo.detector import muat_model_hasil_training_yolo, prediksi_wajah_pada_frame
from yolo.face_cropper import potong_kotak_wajah_dengan_margin
from utils.image_loader import baca_file_gambar_ke_array, ubah_format_bgr_ke_rgb
from utils.image_preprocessor import (
    ubah_ukuran_piksel_wajah,
    normalisasi_piksel_standar,
    buat_augmentasi_citra_wajah,
)


def bentuk_slug_nama_aktor(teks_nama: str) -> str:
    """
    Mengubah nama lengkap atau nama folder aktor menjadi format huruf kecil dengan garis bawah (snake_case).
    """
    teks_tanpa_id = re.sub(r"^\d+[-_]+", "", str(teks_nama).strip())
    return re.sub(r"[^a-zA-Z0-9]+", "_", teks_tanpa_id).lower().strip("_")


def baca_konfigurasi_env_mysql(path_file_env: Path = konfig.FILE_ENV_LARAVEL) -> dict:
    """
    Membaca parameter koneksi database MySQL dari file .env Laravel untuk sinkronisasi metadata aktor.
    """
    parameter_db = {
        "host": "127.0.0.1",
        "port": 3306,
        "database": "indolens",
        "user": "root",
        "password": "",
    }
    if not path_file_env.exists():
        return parameter_db

    for baris in path_file_env.read_text(encoding="utf-8", errors="ignore").splitlines():
        baris_bersih = baris.strip()
        if not baris_bersih or baris_bersih.startswith("#") or "=" not in baris_bersih:
            continue
        kunci, nilai = baris_bersih.split("=", 1)
        kunci = kunci.strip()
        nilai = nilai.strip().strip('"').strip("'")
        if kunci == "DB_HOST" and nilai:
            parameter_db["host"] = nilai
        elif kunci == "DB_PORT" and nilai.isdigit():
            parameter_db["port"] = int(nilai)
        elif kunci == "DB_DATABASE" and nilai:
            parameter_db["database"] = nilai
        elif kunci == "DB_USERNAME":
            parameter_db["user"] = nilai
        elif kunci == "DB_PASSWORD":
            parameter_db["password"] = nilai

    return parameter_db


def ambil_daftar_foto_aktor_dari_mysql_dan_folder() -> dict[str, dict]:
    """
    Mengumpulkan seluruh foto wajah aktor dari tabel actor_images MySQL, folder storage/app/public/actor-images,
    serta folder python/datasets/dataset_facenet_aktor/wajah_aktor_target untuk diproses pada Tahap 03.
    """
    peta_aktor: dict[str, dict] = {}
    path_sudah_terdaftar: set[str] = set()

    # 1. Mencoba mengambil daftar foto wajah resmi dari database MySQL jika layanan MySQL aktif
    try:
        import pymysql

        konfig_db = baca_konfigurasi_env_mysql()
        koneksi = pymysql.connect(
            host=konfig_db["host"],
            port=konfig_db["port"],
            user=konfig_db["user"],
            password=konfig_db["password"],
            database=konfig_db["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3,
        )
        with koneksi:
            with koneksi.cursor() as kursor:
                kursor.execute(
                    """
                    SELECT ai.id AS image_id, ai.actor_id, ai.image_path, a.full_name
                    FROM actor_images ai
                    INNER JOIN actors a ON a.id = ai.actor_id
                    ORDER BY a.id ASC, ai.id ASC
                    """
                )
                baris_mysql = kursor.fetchall()

        for rekaman in baris_mysql:
            rel_path = str(rekaman["image_path"]).lstrip("/\\")
            path_penuh = (konfig.FOLDER_ROOT_PROYEK / "storage" / "app" / "public" / rel_path).resolve()
            if not path_penuh.exists() or path_penuh.name.lower().startswith("profile-"):
                continue

            slug_aktor = bentuk_slug_nama_aktor(rekaman["full_name"])
            if slug_aktor not in peta_aktor:
                peta_aktor[slug_aktor] = {
                    "actor_id": int(rekaman["actor_id"]),
                    "full_name": str(rekaman["full_name"]),
                    "slug_aktor": slug_aktor,
                    "daftar_foto": [],
                }

            kunci_path = str(path_penuh).lower()
            if kunci_path not in path_sudah_terdaftar:
                path_sudah_terdaftar.add(kunci_path)
                peta_aktor[slug_aktor]["daftar_foto"].append(
                    {
                        "image_id": str(rekaman["image_id"]),
                        "path_file": path_penuh,
                        "sumber_data": "mysql_actor_images",
                    }
                )
    except Exception:
        pass

    # 2. Memindai folder storage/app/public/actor-images/{id}-{slug} untuk melengkapi foto yang belum tercatat
    if konfig.FOLDER_STORAGE_ACTOR_IMAGES_LARAVEL.exists():
        for folder_item in sorted(konfig.FOLDER_STORAGE_ACTOR_IMAGES_LARAVEL.iterdir()):
            if not folder_item.is_dir() or folder_item.name.startswith("."):
                continue

            cocok_id = re.match(r"^(\d+)[-_]+(.+)$", folder_item.name)
            id_aktor = int(cocok_id.group(1)) if cocok_id else 0
            slug_aktor = bentuk_slug_nama_aktor(folder_item.name)
            nama_lengkap = slug_aktor.replace("_", " ").title()

            if slug_aktor not in peta_aktor:
                peta_aktor[slug_aktor] = {
                    "actor_id": id_aktor,
                    "full_name": nama_lengkap,
                    "slug_aktor": slug_aktor,
                    "daftar_foto": [],
                }

            for file_gambar in sorted(folder_item.iterdir()):
                if not file_gambar.is_file() or file_gambar.suffix.lower() not in konfig.DAFTAR_EKSTENSI_GAMBAR_VALID:
                    continue
                if file_gambar.name.lower().startswith("profile-"):
                    continue

                kunci_path = str(file_gambar.resolve()).lower()
                if kunci_path not in path_sudah_terdaftar:
                    path_sudah_terdaftar.add(kunci_path)
                    peta_aktor[slug_aktor]["daftar_foto"].append(
                        {
                            "image_id": file_gambar.stem,
                            "path_file": file_gambar.resolve(),
                            "sumber_data": "storage_actor_images",
                        }
                    )

    # 3. Memindai folder python/datasets/dataset_facenet_aktor/wajah_aktor_target/<slug_aktor>
    if konfig.FOLDER_WAJAH_AKTOR_TARGET.exists():
        for folder_aktor in sorted(konfig.FOLDER_WAJAH_AKTOR_TARGET.iterdir()):
            if not folder_aktor.is_dir() or folder_aktor.name.startswith("."):
                continue

            slug_aktor = bentuk_slug_nama_aktor(folder_aktor.name)
            if slug_aktor not in peta_aktor:
                peta_aktor[slug_aktor] = {
                    "actor_id": len(peta_aktor) + 1,
                    "full_name": slug_aktor.replace("_", " ").title(),
                    "slug_aktor": slug_aktor,
                    "daftar_foto": [],
                }

            for file_gambar in sorted(folder_aktor.iterdir()):
                if not file_gambar.is_file() or file_gambar.suffix.lower() not in konfig.DAFTAR_EKSTENSI_GAMBAR_VALID:
                    continue

                kunci_path = str(file_gambar.resolve()).lower()
                if kunci_path not in path_sudah_terdaftar:
                    path_sudah_terdaftar.add(kunci_path)
                    peta_aktor[slug_aktor]["daftar_foto"].append(
                        {
                            "image_id": file_gambar.stem,
                            "path_file": file_gambar.resolve(),
                            "sumber_data": "dataset_wajah_aktor_target",
                        }
                    )

    return {slug: info for slug, info in peta_aktor.items() if info["daftar_foto"]}


def pilih_potongan_wajah_utama_dari_gambar(
    gambar_bgr: np.ndarray,
    rasio_margin: float = konfig.RASIO_MARGIN_CROP_WAJAH,
    izinkan_fallback_tengah: bool = False,
) -> tuple[np.ndarray | None, list[int] | None, float]:
    """
    Mendeteksi kotak wajah pada gambar_bgr menggunakan model YOLOv8 hasil training mandiri (Tahap 02)
    dan memilih satu wajah utama dengan skor (confidence * luas_kotak) tertinggi.
    """
    daftar_deteksi = prediksi_wajah_pada_frame(gambar_bgr, rasio_margin_crop=rasio_margin)
    if daftar_deteksi:
        deteksi_terbaik = max(
            daftar_deteksi,
            key=lambda item: float(item["confidence"])
            * max(1, (item["bbox"][2] - item["bbox"][0]) * (item["bbox"][3] - item["bbox"][1])),
        )
        return deteksi_terbaik["crop"], deteksi_terbaik["bbox"], float(deteksi_terbaik["confidence"])

    if izinkan_fallback_tengah:
        tinggi_img, lebar_img = gambar_bgr.shape[:2]
        bbox_tengah = [
            int(lebar_img * 0.08),
            int(tinggi_img * 0.08),
            int(lebar_img * 0.92),
            int(tinggi_img * 0.92),
        ]
        potongan_tengah = potong_kotak_wajah_dengan_margin(gambar_bgr, bbox_tengah, rasio_margin=0.0)
        return potongan_tengah, bbox_tengah, 0.0

    return None, None, 0.0


def simpan_citra_dan_tensor_wajah(
    citra_rgb_160x160: np.ndarray,
    path_file_jpg: Path,
    path_file_npy: Path,
) -> dict:
    """
    Menyimpan citra wajah RGB 160x160 ke dalam file .jpg (untuk inspeksi visual) dan menyimpan
    array piksel ternormalisasi (float32 160x160x3) ke dalam file .npy (untuk training FaceNet Tahap 04).
    """
    path_file_jpg.parent.mkdir(parents=True, exist_ok=True)
    path_file_npy.parent.mkdir(parents=True, exist_ok=True)

    citra_bgr_160x160 = cv2.cvtColor(citra_rgb_160x160, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path_file_jpg), citra_bgr_160x160)

    tensor_ternormalisasi = normalisasi_piksel_standar(citra_rgb_160x160)
    np.save(str(path_file_npy), tensor_ternormalisasi)

    return {
        "path_preview_jpg": str(path_file_jpg),
        "path_tensor_npy": str(path_file_npy),
        "resolusi": list(konfig.UKURAN_RESOLUSI_WAJAH_FACENET),
    }


def ekstrak_dan_preprocess_wajah_dataset(
    aktifkan_augmentasi_aktor: bool = True,
    rasio_margin_crop: float = konfig.RASIO_MARGIN_CROP_WAJAH,
) -> dict:
    """
    Memuat model YOLOv8 hasil training mandiri (hasil_training_yolov8_wajah.pt dari Tahap 02) di GPU RTX 4060,
    mendeteksi dan memotong wajah dari seluruh foto aktor serta foto orang random dengan margin 12%,
    mengubah ukuran piksel menjadi 160x160 RGB, membuat variasi augmentasi pose/cahaya,
    serta menyimpan tensor ternormalisasi ke folder crop_wajah_160x160 untuk dilatih oleh FaceNet pada Tahap 04.
    """
    konfig.pastikan_semua_folder_tersedia()
    _, _, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)

    print("=" * 78)
    print("  TAHAP 03: DETEKSI CROP WAJAH (YOLO MANDIRI) & PREPROCESSING 160x160 RGB")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']}")
    print(f"[*] Bobot Detektor YOLOv8       : {konfig.FILE_BOBOT_HASIL_TRAINING_YOLO}")
    print(f"[*] Resolusi Target FaceNet     : {konfig.UKURAN_RESOLUSI_WAJAH_FACENET[0]}x{konfig.UKURAN_RESOLUSI_WAJAH_FACENET[1]} piksel (Margin Crop = {int(rasio_margin_crop * 100)}%)")

    # Memuat model YOLOv8 hasil training mandiri dari Tahap 02
    muat_model_hasil_training_yolo(konfig.FILE_BOBOT_HASIL_TRAINING_YOLO)

    peta_data_aktor = ambil_daftar_foto_aktor_dari_mysql_dan_folder()
    if not peta_data_aktor:
        raise RuntimeError(
            "Tidak ditemukan foto wajah aktor pada database maupun di folder:\n"
            f"  {konfig.FOLDER_WAJAH_AKTOR_TARGET}"
        )

    # Membersihkan isi folder output crop_wajah_160x160 lama sebelum ekstraksi baru
    folder_output_aktor = konfig.FOLDER_CROP_WAJAH_160X160 / "aktor"
    folder_output_random = konfig.FOLDER_CROP_WAJAH_160X160 / "orang_random"
    for folder_target in [folder_output_aktor, folder_output_random]:
        if folder_target.exists():
            shutil.rmtree(folder_target, ignore_errors=True)
        folder_target.mkdir(parents=True, exist_ok=True)

    waktu_mulai = time.time()
    manifest_aktor_terproses: dict[str, dict] = {}
    daftar_sampel_orang_random: list[dict] = []

    total_foto_aktor_sumber = 0
    total_crop_aktor_asli = 0
    total_crop_aktor_augmentasi = 0
    total_gagal_deteksi_aktor = 0

    for slug_aktor, info_aktor in sorted(peta_data_aktor.items()):
        manifest_aktor_terproses[slug_aktor] = {
            "actor_id": info_aktor["actor_id"],
            "full_name": info_aktor["full_name"],
            "slug_aktor": slug_aktor,
            "sampel_asli": [],
            "sampel_augmentasi": [],
        }

        for indeks_foto, item_foto in enumerate(info_aktor["daftar_foto"], start=1):
            total_foto_aktor_sumber += 1
            path_sumber = item_foto["path_file"]
            id_gambar = str(item_foto["image_id"])

            try:
                gambar_bgr = baca_file_gambar_ke_array(path_sumber)
            except Exception:
                total_gagal_deteksi_aktor += 1
                continue

            potongan_bgr, koordinat_bbox, skor_conf = pilih_potongan_wajah_utama_dari_gambar(
                gambar_bgr,
                rasio_margin=rasio_margin_crop,
                izinkan_fallback_tengah=False,
            )
            if potongan_bgr is None or potongan_bgr.size == 0:
                total_gagal_deteksi_aktor += 1
                continue

            potongan_rgb = ubah_format_bgr_ke_rgb(potongan_bgr)
            wajah_rgb_160x160 = ubah_ukuran_piksel_wajah(
                potongan_rgb,
                ukuran_target=konfig.UKURAN_RESOLUSI_WAJAH_FACENET,
            )

            nama_dasar = f"{slug_aktor}_{indeks_foto:03d}_{id_gambar}"
            folder_aktor_tujuan = folder_output_aktor / slug_aktor

            if aktifkan_augmentasi_aktor:
                peta_variasi = buat_augmentasi_citra_wajah(wajah_rgb_160x160)
            else:
                peta_variasi = {"asli": wajah_rgb_160x160}

            for nama_variasi, citra_variasi in peta_variasi.items():
                path_jpg = folder_aktor_tujuan / "previews" / f"{nama_dasar}_{nama_variasi}.jpg"
                path_npy = folder_aktor_tujuan / "tensors" / f"{nama_dasar}_{nama_variasi}.npy"
                info_simpan = simpan_citra_dan_tensor_wajah(citra_variasi, path_jpg, path_npy)

                data_rekaman_crop = {
                    "image_id": id_gambar,
                    "nama_variasi": nama_variasi,
                    "path_sumber_asli": str(path_sumber),
                    "sumber_data": item_foto["sumber_data"],
                    "bbox_yolo": koordinat_bbox,
                    "confidence_yolo": round(skor_conf, 4),
                    "path_preview_jpg": info_simpan["path_preview_jpg"],
                    "path_tensor_npy": info_simpan["path_tensor_npy"],
                }

                if nama_variasi == "asli":
                    total_crop_aktor_asli += 1
                    manifest_aktor_terproses[slug_aktor]["sampel_asli"].append(data_rekaman_crop)
                else:
                    total_crop_aktor_augmentasi += 1
                    manifest_aktor_terproses[slug_aktor]["sampel_augmentasi"].append(data_rekaman_crop)

    # Memproses foto wajah orang random (Unknown / Negative sample untuk Triplet Loss dan Confusion Matrix)
    semua_file_random = sorted(
        [
            file_item
            for file_item in konfig.FOLDER_WAJAH_ORANG_RANDOM.rglob("*")
            if file_item.is_file() and file_item.suffix.lower() in konfig.DAFTAR_EKSTENSI_GAMBAR_VALID
        ]
    )

    for indeks_random, path_random in enumerate(semua_file_random, start=1):
        try:
            gambar_random_bgr = baca_file_gambar_ke_array(path_random)
        except Exception:
            continue

        potongan_random_bgr, bbox_random, conf_random = pilih_potongan_wajah_utama_dari_gambar(
            gambar_random_bgr,
            rasio_margin=rasio_margin_crop,
            izinkan_fallback_tengah=True,
        )
        if potongan_random_bgr is None or potongan_random_bgr.size == 0:
            continue

        potongan_random_rgb = ubah_format_bgr_ke_rgb(potongan_random_bgr)
        wajah_random_160x160 = ubah_ukuran_piksel_wajah(
            potongan_random_rgb,
            ukuran_target=konfig.UKURAN_RESOLUSI_WAJAH_FACENET,
        )

        nama_random = f"random_{indeks_random:04d}_{path_random.stem}"
        path_jpg_rand = folder_output_random / "previews" / f"{nama_random}.jpg"
        path_npy_rand = folder_output_random / "tensors" / f"{nama_random}.npy"
        info_simpan_rand = simpan_citra_dan_tensor_wajah(wajah_random_160x160, path_jpg_rand, path_npy_rand)

        daftar_sampel_orang_random.append(
            {
                "id_sampel": nama_random,
                "path_sumber_asli": str(path_random),
                "bbox_yolo": bbox_random,
                "confidence_yolo": round(conf_random, 4),
                "path_preview_jpg": info_simpan_rand["path_preview_jpg"],
                "path_tensor_npy": info_simpan_rand["path_tensor_npy"],
            }
        )

    durasi_detik = round(time.time() - waktu_mulai, 2)
    ringkasan_preprocessing = {
        "waktu_selesai": time.strftime("%Y-%m-%d %H:%M:%S"),
        "durasi_proses_detik": durasi_detik,
        "resolusi_wajah": list(konfig.UKURAN_RESOLUSI_WAJAH_FACENET),
        "rasio_margin_crop": rasio_margin_crop,
        "jumlah_aktor_terdaftar": len(manifest_aktor_terproses),
        "total_foto_aktor_sumber": total_foto_aktor_sumber,
        "total_crop_aktor_asli": total_crop_aktor_asli,
        "total_crop_aktor_augmentasi": total_crop_aktor_augmentasi,
        "total_gagal_deteksi_aktor": total_gagal_deteksi_aktor,
        "total_sampel_orang_random": len(daftar_sampel_orang_random),
        "aktor": manifest_aktor_terproses,
        "orang_random": daftar_sampel_orang_random,
    }

    path_manifest_utama = konfig.FOLDER_CROP_WAJAH_160X160 / "manifest_preprocessing_wajah.json"
    path_manifest_utama.write_text(json.dumps(ringkasan_preprocessing, indent=2), encoding="utf-8")

    path_salinan_artefak = konfig.FOLDER_HASIL_PREPROCESSING_WAJAH / "manifest_preprocessing_wajah.json"
    path_salinan_artefak.write_text(json.dumps(ringkasan_preprocessing, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("  TAHAP 03: PREPROCESSING & CROP WAJAH 160x160 SELESAI")
    print("=" * 78)
    print(f"[OK] Jumlah aktor terproses           : {len(manifest_aktor_terproses)} aktor")
    print(f"[OK] Crop wajah aktor asli            : {total_crop_aktor_asli} dari {total_foto_aktor_sumber} foto")
    print(f"[OK] Variasi augmentasi wajah aktor   : {total_crop_aktor_augmentasi} tensor")
    print(f"[OK] Sampel wajah orang random        : {len(daftar_sampel_orang_random)} tensor")
    print(f"[OK] Manifest disimpan ke             : {path_manifest_utama}")

    return ringkasan_preprocessing


if __name__ == "__main__":
    ekstrak_dan_preprocess_wajah_dataset()
