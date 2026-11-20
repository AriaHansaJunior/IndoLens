"""
Layanan Micro-Service FastAPI Deteksi Wajah YOLOv8 & Pengenalan Aktor FaceNet.
Memuat bobot hasil_training_yolov8_wajah.pt dan hasil_training_facenet_aktor.pth di GPU RTX 4060
serta mencocokkan vektor embedding 512-D menggunakan jarak Euclidean dan batas ambang terkalibrasi.
"""

import io
import json
import re
import shutil
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Menambahkan direktori modul python ke sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.config import (
    FILE_BOBOT_HASIL_TRAINING_YOLO,
    FILE_BOBOT_HASIL_TRAINING_FACENET,
    BATAS_CONFIDENCE_DETEKSI_YOLO,
    BATAS_AMBANG_JARAK_EUCLIDEAN,
)
from config.dataset import DIMENSI_EMBEDDING_FACENET
from yolo.detector import (
    muat_model_hasil_training_yolo,
    prediksi_wajah_pada_frame,
    pilih_perangkat_komputasi_yolo,
)
from facenet.embedding_generator import (
    muat_model_hasil_training_facenet,
    ekstrak_vektor_embedding_wajah,
    pilih_perangkat_komputasi_facenet,
)
from recognition.embedding_matcher import (
    muat_semua_database_embedding_aktor,
    muat_embedding_satu_aktor,
    cari_kecocokan_aktor_terdekat,
)

# Menyimpan instance model hasil training dan database embedding referensi di memori
MODEL_YOLO_AKTIF = None
MODEL_FACENET_AKTIF = None
KAMUS_EMBEDDING_AKTOR_AKTIF: dict = {}

PATH_MANIFEST_EMBEDDING = BASE_DIR / "embeddings" / "manifest.json"
PATH_LAPORAN_KALIBRASI_THRESHOLD = (
    BASE_DIR.parent
    / "training_python"
    / "artefak_hasil_training"
    / "04_hasil_evaluasi_dan_matrix_score"
    / "laporan_evaluasi_matrix_dan_f1.json"
)


def ambil_batas_ambang_jarak_aktif() -> float:
    """
    Membaca nilai batas_ambang_jarak_optimal hasil kalibrasi F1-Score dari laporan evaluasi Tahap 04
    apabila tersedia, atau menggunakan nilai standar BATAS_AMBANG_JARAK_EUCLIDEAN (0.85).
    """
    if PATH_LAPORAN_KALIBRASI_THRESHOLD.exists():
        try:
            isi_laporan = json.loads(PATH_LAPORAN_KALIBRASI_THRESHOLD.read_text(encoding="utf-8"))
            ambang_kalibrasi = isi_laporan.get("batas_ambang_jarak_optimal")
            if ambang_kalibrasi is not None:
                return float(ambang_kalibrasi)
        except Exception:
            pass
    return float(BATAS_AMBANG_JARAK_EUCLIDEAN)


def pastikan_model_hasil_training_siap() -> tuple[bool, str]:
    """
    Memeriksa dan memuat bobot hasil_training_yolov8_wajah.pt serta hasil_training_facenet_aktor.pth
    ke memori GPU RTX 4060 apabila file bobot hasil pelatihan dari Jupyter Notebook sudah tersedia.
    """
    global MODEL_YOLO_AKTIF, MODEL_FACENET_AKTIF

    if not FILE_BOBOT_HASIL_TRAINING_YOLO.exists():
        return (
            False,
            f"Bobot YOLOv8 belum ditraining ({FILE_BOBOT_HASIL_TRAINING_YOLO.name} belum tersedia). "
            "Jalankan Notebook_01_Training_Model_YOLOv8.ipynb terlebih dahulu.",
        )

    if not FILE_BOBOT_HASIL_TRAINING_FACENET.exists():
        return (
            False,
            f"Bobot FaceNet belum ditraining ({FILE_BOBOT_HASIL_TRAINING_FACENET.name} belum tersedia). "
            "Jalankan Notebook_02_Training_Dataset_Wajah_Aktor.ipynb terlebih dahulu.",
        )

    try:
        if MODEL_YOLO_AKTIF is None:
            MODEL_YOLO_AKTIF = muat_model_hasil_training_yolo(FILE_BOBOT_HASIL_TRAINING_YOLO)
        if MODEL_FACENET_AKTIF is None:
            MODEL_FACENET_AKTIF = muat_model_hasil_training_facenet(FILE_BOBOT_HASIL_TRAINING_FACENET)
        return True, "Model YOLOv8 dan FaceNet aktif di GPU."
    except Exception as galat_muat:
        return False, f"Gagal memuat bobot model: {galat_muat}"


def ekstrak_embedding_wajah_tahan_tolehan(potongan_wajah_bgr: np.ndarray) -> np.ndarray:
    """
    Mengekstrak vektor embedding 512-D dari potongan wajah asli dan bayangan cermin horizontalnya (flip),
    lalu menggabungkan dan menormalisasi L2 keduanya agar pengenalan aktor tetap akurat saat wajah agak menoleh.
    """
    vektor_asli = ekstrak_vektor_embedding_wajah(
        potongan_wajah_bgr,
        model_facenet_aktif=MODEL_FACENET_AKTIF,
    )
    potongan_cermin = cv2.flip(potongan_wajah_bgr, 1)
    vektor_cermin = ekstrak_vektor_embedding_wajah(
        potongan_cermin,
        model_facenet_aktif=MODEL_FACENET_AKTIF,
    )

    vektor_gabungan = vektor_asli + vektor_cermin
    norma_gabungan = float(np.linalg.norm(vektor_gabungan))
    if norma_gabungan > 0.0:
        return (vektor_gabungan / norma_gabungan).astype(np.float32)
    return vektor_asli


@asynccontextmanager
async def siklus_hidup_service(aplikasi: FastAPI):
    """
    Memuat model YOLOv8, FaceNet, dan database embedding referensi (.npy)
    saat server dinyalakan agar inferensi kamera real-time berjalan tanpa jeda inisialisasi.
    """
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    perangkat_yolo = pilih_perangkat_komputasi_yolo()
    perangkat_facenet = pilih_perangkat_komputasi_facenet()
    print(f"[YOLO Service] Perangkat Komputasi Aktif: YOLO={perangkat_yolo} | FaceNet={perangkat_facenet}")

    siap, pesan_status = pastikan_model_hasil_training_siap()
    print(f"[Pipeline Service] Status Model: {pesan_status}")

    KAMUS_EMBEDDING_AKTOR_AKTIF = muat_semua_database_embedding_aktor()
    print(
        f"[Recognition Service] Database embedding dimuat untuk {len(KAMUS_EMBEDDING_AKTOR_AKTIF)} aktor: "
        f"{list(KAMUS_EMBEDDING_AKTOR_AKTIF.keys())}"
    )

    if siap:
        frame_pemanasan = np.zeros((384, 384, 3), dtype=np.uint8)
        _ = prediksi_wajah_pada_frame(frame_pemanasan)
        crop_pemanasan = np.zeros((160, 160, 3), dtype=np.uint8)
        _ = ekstrak_vektor_embedding_wajah(crop_pemanasan, model_facenet_aktif=MODEL_FACENET_AKTIF)
        print("[Pipeline Service] Pemanasan GPU RTX 4060 selesai. Siap melayani pengenalan real-time.")

    yield
    print("[Pipeline Service] Layanan dimatikan.")


app = FastAPI(
    title="IndoLens YOLOv8 & FaceNet Recognition Service",
    description="Real-time face detection, 512-D FaceNet embedding, and Euclidean matching",
    version="2.0.0",
    lifespan=siklus_hidup_service,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def periksa_kesehatan_service():
    """Mengembalikan status kesiapan model dan jumlah aktor yang dimuat."""
    siap, pesan_status = pastikan_model_hasil_training_siap()
    return {
        "status": "ready",
        "models_trained": siap,
        "models_message": pesan_status,
        "service": "IndoLens YOLOv8 + FaceNet Recognition Service",
        "yolo_loaded": MODEL_YOLO_AKTIF is not None,
        "facenet_loaded": MODEL_FACENET_AKTIF is not None,
        "actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
        "actors_list": list(KAMUS_EMBEDDING_AKTOR_AKTIF.keys()),
        "distance_threshold": ambil_batas_ambang_jarak_aktif(),
        "confidence_threshold": BATAS_CONFIDENCE_DETEKSI_YOLO,
        "embedding_dim": DIMENSI_EMBEDDING_FACENET,
    }


def baca_file_gambar_bgr(path_atau_str: str | Path) -> np.ndarray | None:
    """Membaca file gambar dari penyimpanan lokal menjadi array BGR OpenCV."""
    teks_path = str(path_atau_str)
    try:
        gambar_bgr = cv2.imread(teks_path)
        if gambar_bgr is not None:
            return gambar_bgr
    except Exception:
        pass

    try:
        with Image.open(teks_path) as gambar_pil:
            array_rgb = np.array(gambar_pil.convert("RGB"))
            return cv2.cvtColor(array_rgb, cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def muat_manifest_embedding() -> dict:
    """Membaca file manifest.json dari folder python/embeddings/."""
    if PATH_MANIFEST_EMBEDDING.exists():
        try:
            return json.loads(PATH_MANIFEST_EMBEDDING.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"actors": {}, "updated_at": 0}


def simpan_manifest_embedding(data_manifest: dict):
    """Menyimpan pembaruan manifest.json ke folder python/embeddings/."""
    data_manifest["updated_at"] = time.time()
    PATH_MANIFEST_EMBEDDING.parent.mkdir(parents=True, exist_ok=True)
    PATH_MANIFEST_EMBEDDING.write_text(json.dumps(data_manifest, indent=2), encoding="utf-8")


@app.post("/prune-orphaned-actors")
async def bersihkan_aktor_yatim_endpoint(request: Request):
    """Menghapus folder embedding aktor yang sudah tidak terdaftar aktif di database MySQL."""
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    try:
        isi_body = await request.json()
    except Exception:
        return {"status": "error", "message": "Body JSON tidak valid"}

    daftar_aktor_aktif = isi_body.get("active_actors", [])
    set_slug_aktif = set()
    for item_aktor in daftar_aktor_aktif:
        slug = item_aktor.get("actor_slug")
        if not slug and item_aktor.get("full_name"):
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", item_aktor["full_name"]).lower().strip("_")
        if slug:
            set_slug_aktif.add(slug)

    folder_embedding = BASE_DIR / "embeddings"
    daftar_dihapus = []
    if folder_embedding.exists():
        for item_folder in list(folder_embedding.iterdir()):
            if item_folder.is_dir() and not item_folder.name.startswith("."):
                if item_folder.name not in set_slug_aktif:
                    shutil.rmtree(str(item_folder), ignore_errors=True)
                    daftar_dihapus.append(item_folder.name)
                    KAMUS_EMBEDDING_AKTOR_AKTIF.pop(item_folder.name, None)

    manifest = muat_manifest_embedding()
    peta_aktor = manifest.get("actors", {})
    berubah = False
    for slug_lama in list(peta_aktor.keys()):
        if slug_lama not in set_slug_aktif:
            del peta_aktor[slug_lama]
            berubah = True
    if berubah:
        manifest["actors"] = peta_aktor
        simpan_manifest_embedding(manifest)

    return {
        "status": "success",
        "pruned_orphans": daftar_dihapus,
        "active_actors_count": len(set_slug_aktif),
        "total_actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
    }


@app.post("/sync-actor-embedding")
async def sinkronkan_embedding_aktor_endpoint(request: Request):
    """
    Menyinkronkan foto wajah aktor yang diunggah melalui halaman web Camp menjadi file .npy (512-D)
    menggunakan model YOLOv8 dan FaceNet.
    """
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    try:
        isi_body = await request.json()
    except Exception:
        return {"status": "error", "message": "Body JSON tidak valid"}

    id_aktor = isi_body.get("actor_id")
    nama_lengkap = str(isi_body.get("full_name", "")).strip()
    paksa_hitung_ulang = bool(isi_body.get("force", False))
    if not nama_lengkap:
        return {"status": "error", "message": "Field full_name wajib diisi"}

    siap, pesan_model = pastikan_model_hasil_training_siap()
    if not siap:
        return {"status": "error", "message": pesan_model}

    daftar_gambar = isi_body.get("images", [])
    if not daftar_gambar and "image_id" in isi_body and "image_path" in isi_body:
        daftar_gambar = [{"image_id": isi_body["image_id"], "image_path": isi_body["image_path"]}]

    slug_aktor = re.sub(r"[^a-zA-Z0-9]+", "_", nama_lengkap).lower().strip("_")
    folder_aktor = BASE_DIR / "embeddings" / slug_aktor
    folder_aktor.mkdir(parents=True, exist_ok=True)

    daftar_berhasil = []
    daftar_tanpa_wajah = []
    daftar_tidak_ditemukan = []
    set_nama_file_aktif = set()

    for item_gbr in daftar_gambar:
        id_gambar = item_gbr.get("image_id")
        path_gbr_str = item_gbr.get("image_path")
        if not path_gbr_str or id_gambar is None:
            continue

        file_npy_target = folder_aktor / f"{id_gambar}.npy"
        set_nama_file_aktif.add(f"{id_gambar}.npy")

        if not paksa_hitung_ulang and file_npy_target.exists():
            try:
                emb_lama = np.load(str(file_npy_target))
                if len(emb_lama) == DIMENSI_EMBEDDING_FACENET:
                    daftar_berhasil.append(id_gambar)
                    continue
            except Exception:
                pass

        path_gbr = Path(path_gbr_str)
        if not path_gbr.exists():
            daftar_tidak_ditemukan.append(id_gambar)
            continue

        gambar_bgr = baca_file_gambar_bgr(path_gbr)
        if gambar_bgr is None:
            daftar_tidak_ditemukan.append(id_gambar)
            continue

        deteksi_wajah = prediksi_wajah_pada_frame(gambar_bgr, rasio_margin_crop=0.04)
        if not deteksi_wajah:
            daftar_tanpa_wajah.append(id_gambar)
            continue

        deteksi_utama = max(deteksi_wajah, key=lambda d: d.get("confidence", 0.0))
        potongan_wajah = deteksi_utama.get("crop")
        if potongan_wajah is None or getattr(potongan_wajah, "size", 0) == 0:
            daftar_tanpa_wajah.append(id_gambar)
            continue

        vektor_512d = ekstrak_embedding_wajah_tahan_tolehan(potongan_wajah)
        if vektor_512d is not None and len(vektor_512d) == DIMENSI_EMBEDDING_FACENET:
            np.save(str(file_npy_target), vektor_512d.astype(np.float32))
            daftar_berhasil.append(id_gambar)
        else:
            daftar_tanpa_wajah.append(id_gambar)

    file_terhapus = []
    if daftar_gambar:
        for file_lama in list(folder_aktor.glob("*.npy")):
            if file_lama.name not in set_nama_file_aktif:
                file_lama.unlink(missing_ok=True)
                file_terhapus.append(file_lama.name)

    manifest = muat_manifest_embedding()
    manifest.setdefault("actors", {})[slug_aktor] = {
        "actor_id": id_aktor,
        "full_name": nama_lengkap,
        "slug": slug_aktor,
        "files": sorted([f.name for f in folder_aktor.glob("*.npy")]),
    }
    simpan_manifest_embedding(manifest)

    KAMUS_EMBEDDING_AKTOR_AKTIF[slug_aktor] = muat_embedding_satu_aktor(
        slug_aktor,
        folder_dasar_embedding=BASE_DIR / "embeddings",
        nama_lengkap_aktor=nama_lengkap,
    )

    return {
        "status": "success",
        "actor_id": id_aktor,
        "full_name": nama_lengkap,
        "actor_slug": slug_aktor,
        "generated_count": len(daftar_berhasil),
        "generated_image_ids": daftar_berhasil,
        "pruned_files": file_terhapus,
        "skipped_no_face": daftar_tanpa_wajah,
        "skipped_not_found": daftar_tidak_ditemukan,
        "total_embeddings_for_actor": len(KAMUS_EMBEDDING_AKTOR_AKTIF.get(slug_aktor, [])),
        "total_actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
    }


@app.delete("/delete-actor-embedding")
async def hapus_satu_embedding_aktor_endpoint(request: Request):
    """Menghapus satu file .npy referensi ketika foto wajah dihapus pada halaman Camp."""
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    try:
        isi_body = await request.json()
    except Exception:
        return {"status": "error", "message": "Body JSON tidak valid"}

    nama_lengkap = str(isi_body.get("full_name", "")).strip()
    id_gambar = isi_body.get("image_id")
    if not nama_lengkap or id_gambar is None:
        return {"status": "error", "message": "Field full_name dan image_id wajib diisi"}

    slug_aktor = re.sub(r"[^a-zA-Z0-9]+", "_", nama_lengkap).lower().strip("_")
    file_target = BASE_DIR / "embeddings" / slug_aktor / f"{id_gambar}.npy"

    berhasil_hapus = False
    if file_target.exists():
        file_target.unlink()
        berhasil_hapus = True

    manifest = muat_manifest_embedding()
    if slug_aktor in manifest.get("actors", {}):
        daftar_file = manifest["actors"][slug_aktor].get("files", [])
        nama_npy = f"{id_gambar}.npy"
        if nama_npy in daftar_file:
            daftar_file.remove(nama_npy)
            manifest["actors"][slug_aktor]["files"] = daftar_file
            simpan_manifest_embedding(manifest)

    koleksi_baru = muat_embedding_satu_aktor(
        slug_aktor,
        folder_dasar_embedding=BASE_DIR / "embeddings",
        nama_lengkap_aktor=nama_lengkap,
    )
    if koleksi_baru:
        KAMUS_EMBEDDING_AKTOR_AKTIF[slug_aktor] = koleksi_baru
    else:
        KAMUS_EMBEDDING_AKTOR_AKTIF.pop(slug_aktor, None)

    return {
        "status": "success",
        "deleted": berhasil_hapus,
        "actor_slug": slug_aktor,
        "remaining_embeddings": len(KAMUS_EMBEDDING_AKTOR_AKTIF.get(slug_aktor, [])),
        "total_actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
    }


@app.delete("/delete-actor")
async def hapus_seluruh_aktor_endpoint(request: Request):
    """Menghapus seluruh folder embedding referensi milik aktor yang dihapus dari Camp."""
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    try:
        isi_body = await request.json()
    except Exception:
        return {"status": "error", "message": "Body JSON tidak valid"}

    nama_lengkap = str(isi_body.get("full_name", "")).strip()
    if not nama_lengkap:
        return {"status": "error", "message": "Field full_name wajib diisi"}

    slug_aktor = re.sub(r"[^a-zA-Z0-9]+", "_", nama_lengkap).lower().strip("_")
    folder_aktor = BASE_DIR / "embeddings" / slug_aktor

    berhasil_hapus = False
    if folder_aktor.exists():
        shutil.rmtree(str(folder_aktor), ignore_errors=True)
        berhasil_hapus = True

    manifest = muat_manifest_embedding()
    if slug_aktor in manifest.get("actors", {}):
        del manifest["actors"][slug_aktor]
        simpan_manifest_embedding(manifest)

    KAMUS_EMBEDDING_AKTOR_AKTIF.pop(slug_aktor, None)

    return {
        "status": "success",
        "deleted": berhasil_hapus,
        "actor_slug": slug_aktor,
        "total_actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
    }


@app.post("/reload-embeddings")
def muat_ulang_semua_embedding_endpoint():
    """Memuat ulang seluruh file .npy dari python/embeddings/ serta memastikan model terbaru aktif."""
    global KAMUS_EMBEDDING_AKTOR_AKTIF
    pastikan_model_hasil_training_siap()
    KAMUS_EMBEDDING_AKTOR_AKTIF = muat_semua_database_embedding_aktor(
        folder_dasar_embedding=BASE_DIR / "embeddings"
    )
    return {
        "status": "success",
        "actors_loaded": len(KAMUS_EMBEDDING_AKTOR_AKTIF),
        "actors_list": list(KAMUS_EMBEDDING_AKTOR_AKTIF.keys()),
    }


@app.post("/detect")
async def deteksi_dan_kenali_wajah_endpoint(request: Request):
    """
    Menerima frame kamera dari browser, mendeteksi kotak wajah dengan YOLOv8 (margin 12%),
    mengekstrak vektor embedding 512-D tahan-tolehan dengan FaceNet di GPU RTX 4060,
    dan mencari kecocokan aktor terdekat menggunakan Euclidean Distance.
    """
    waktu_mulai_total = time.perf_counter()

    bytes_frame = await request.body()
    if not bytes_frame:
        return {
            "status": "error",
            "message": "Data frame kosong.",
            "faces_count": 0,
            "faces": [],
        }

    siap, pesan_model = pastikan_model_hasil_training_siap()
    if not siap:
        return {
            "status": "success",
            "models_trained": False,
            "message": pesan_model,
            "faces_count": 0,
            "facenet_processed_count": 0,
            "known_faces_count": 0,
            "unknown_faces_count": 0,
            "faces": [],
            "frame_dimensions": [640, 480],
            "inference_time_ms": 0.0,
            "yolo_time_ms": 0.0,
            "facenet_time_ms": 0.0,
            "recognition_time_ms": 0.0,
        }

    array_buffer = np.frombuffer(bytes_frame, np.uint8)
    gambar_bgr = cv2.imdecode(array_buffer, cv2.IMREAD_COLOR)

    if gambar_bgr is None:
        try:
            with Image.open(io.BytesIO(bytes_frame)) as gambar_pil:
                array_rgb = np.array(gambar_pil.convert("RGB"))
                gambar_bgr = cv2.cvtColor(array_rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            gambar_bgr = None

    if gambar_bgr is None:
        return {
            "status": "error",
            "message": "Gagal mendekode frame gambar.",
            "faces_count": 0,
            "faces": [],
        }

    tinggi_frame, lebar_frame = gambar_bgr.shape[:2]
    batas_ambang_aktif = ambil_batas_ambang_jarak_aktif()

    waktu_mulai_yolo = time.perf_counter()
    daftar_deteksi_yolo = prediksi_wajah_pada_frame(gambar_bgr, rasio_margin_crop=0.04)
    durasi_yolo_ms = round((time.perf_counter() - waktu_mulai_yolo) * 1000, 2)

    daftar_wajah_keluaran = []
    waktu_mulai_facenet = time.perf_counter()
    total_durasi_matching_ms = 0.0

    for indeks_wajah, item_deteksi in enumerate(daftar_deteksi_yolo):
        koordinat_bbox = item_deteksi["bbox"]
        skor_confidence = float(item_deteksi["confidence"])
        potongan_wajah = item_deteksi.get("crop")

        data_satu_wajah = {
            "bbox": koordinat_bbox,
            "confidence": round(skor_confidence, 4),
            "embedding_dim": 0,
            "embedding": None,
            "facenet_status": "no_crop",
            "actor": "Unknown",
            "distance": 999.0,
            "status": "unknown",
        }

        if potongan_wajah is not None and getattr(potongan_wajah, "size", 0) > 0:
            try:
                vektor_embedding_wajah = ekstrak_embedding_wajah_tahan_tolehan(potongan_wajah)
                if vektor_embedding_wajah is not None and len(vektor_embedding_wajah) == DIMENSI_EMBEDDING_FACENET:
                    data_satu_wajah["embedding_dim"] = int(len(vektor_embedding_wajah))
                    data_satu_wajah["facenet_status"] = "success"

                    waktu_mulai_cocok = time.perf_counter()
                    hasil_pencocokan = cari_kecocokan_aktor_terdekat(
                        vektor_embedding_wajah,
                        KAMUS_EMBEDDING_AKTOR_AKTIF,
                        batas_ambang_jarak=batas_ambang_aktif,
                    )
                    total_durasi_matching_ms += (time.perf_counter() - waktu_mulai_cocok) * 1000

                    data_satu_wajah["actor"] = (
                        hasil_pencocokan["actor"] if hasil_pencocokan["status"] == "known" else "Unknown"
                    )
                    data_satu_wajah["distance"] = hasil_pencocokan["distance"]
                    data_satu_wajah["status"] = hasil_pencocokan["status"]
                else:
                    data_satu_wajah["facenet_status"] = "invalid_dimension"
            except Exception as galat_fn:
                data_satu_wajah["facenet_status"] = f"error: {galat_fn}"

        daftar_wajah_keluaran.append(data_satu_wajah)

    durasi_facenet_ms = round((time.perf_counter() - waktu_mulai_facenet) * 1000, 2)
    durasi_total_ms = round((time.perf_counter() - waktu_mulai_total) * 1000, 2)
    jumlah_terproses = sum(1 for f in daftar_wajah_keluaran if f["facenet_status"] == "success")
    jumlah_dikenali = sum(1 for f in daftar_wajah_keluaran if f.get("status") == "known")
    jumlah_tidak_dikenali = sum(1 for f in daftar_wajah_keluaran if f.get("status") == "unknown")

    return {
        "status": "success",
        "models_trained": True,
        "faces_count": len(daftar_wajah_keluaran),
        "facenet_processed_count": jumlah_terproses,
        "known_faces_count": jumlah_dikenali,
        "unknown_faces_count": jumlah_tidak_dikenali,
        "faces": daftar_wajah_keluaran,
        "frame_dimensions": [lebar_frame, tinggi_frame],
        "inference_time_ms": durasi_total_ms,
        "yolo_time_ms": durasi_yolo_ms,
        "facenet_time_ms": durasi_facenet_ms,
        "recognition_time_ms": round(total_durasi_matching_ms, 2),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")
