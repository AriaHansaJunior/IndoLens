import json
import time
from pathlib import Path
from typing import Any
import torch
from ultralytics import YOLO

from config.config import (
    FILE_BOBOT_HASIL_TRAINING_YOLO,
    BATAS_CONFIDENCE_DETEKSI_YOLO,
    BATAS_IOU_NMS_YOLO,
    UKURAN_GAMBAR_INFERENSI_YOLO,
)
from yolo.video_processor import open_video, read_frame, release_video
from yolo.frame_extractor import get_total_frame, get_fps, get_resolution
from yolo.face_cropper import (
    potong_kotak_wajah_dengan_margin,
    validasi_potongan_wajah,
)

# Menyimpan instance model YOLOv8 hasil training mandiri di memori agar tidak dimuat berulang kali
_MODEL_YOLO_TERLATIH: Any = None
_PERANGKAT_KOMPUTASI_YOLO: Any = None


def pilih_perangkat_komputasi_yolo():
    """
    Memilih perangkat GPU NVIDIA GeForce RTX 4060 (indeks cuda:0 pada PyTorch / GPU 1 pada Task Manager)
    untuk menjalankan inferensi deteksi wajah YOLOv8 secara cepat.
    """
    global _PERANGKAT_KOMPUTASI_YOLO
    if _PERANGKAT_KOMPUTASI_YOLO is not None:
        return _PERANGKAT_KOMPUTASI_YOLO

    if torch.cuda.is_available() and torch.cuda.device_count() > 0:
        indeks_gpu = 0
        for indeks_uji in range(torch.cuda.device_count()):
            nama_gpu = torch.cuda.get_device_name(indeks_uji).upper()
            if "RTX" in nama_gpu or "NVIDIA" in nama_gpu:
                indeks_gpu = indeks_uji
                break
        _PERANGKAT_KOMPUTASI_YOLO = indeks_gpu
    else:
        _PERANGKAT_KOMPUTASI_YOLO = "cpu"

    return _PERANGKAT_KOMPUTASI_YOLO


def muat_model_hasil_training_yolo(path_bobot_yolo: Path | str | None = None) -> YOLO:
    """
    Memuat file bobot hasil_training_yolov8_wajah.pt dari folder storage/app/ai/weights/
    yang dihasilkan oleh proses pelatihan mandiri pada training_python/tahap_02_training_yolo_wajah.py.
    Menolak pemakaian model pre-trained bawaan luar apabila file hasil training sendiri belum tersedia.
    """
    global _MODEL_YOLO_TERLATIH

    path_target = Path(path_bobot_yolo) if path_bobot_yolo else Path(FILE_BOBOT_HASIL_TRAINING_YOLO)
    if not path_target.exists():
        raise FileNotFoundError(
            f"Bobot hasil training mandiri YOLOv8 belum ditemukan di: {path_target}\n"
            "Jalankan Tahap 01 dan Tahap 02 pada Jupyter Notebook (IndoLens_Training_Pipeline.ipynb) "
            "terlebih dahulu untuk melatih model YOLOv8 dari Epoch 0."
        )

    _MODEL_YOLO_TERLATIH = YOLO(str(path_target))
    return _MODEL_YOLO_TERLATIH


def deteksi_kotak_wajah_pada_frame(frame_gambar) -> list[Any]:
    """
    Menjalankan prediksi jaringan YOLOv8 hasil training mandiri pada satu frame gambar
    menggunakan GPU RTX 4060 untuk menemukan kandidat koordinat kotak wajah.
    """
    global _MODEL_YOLO_TERLATIH
    if _MODEL_YOLO_TERLATIH is None:
        _MODEL_YOLO_TERLATIH = muat_model_hasil_training_yolo()

    perangkat_aktif = pilih_perangkat_komputasi_yolo()
    daftar_hasil_mentah: Any = _MODEL_YOLO_TERLATIH(
        frame_gambar,
        conf=BATAS_CONFIDENCE_DETEKSI_YOLO,
        iou=BATAS_IOU_NMS_YOLO,
        imgsz=UKURAN_GAMBAR_INFERENSI_YOLO,
        device=perangkat_aktif,
        verbose=False,
    )
    return list(daftar_hasil_mentah)


def prediksi_wajah_pada_frame(
    frame_gambar,
    rasio_margin_crop: float = 0.12,
) -> list[dict]:
    """
    Mendeteksi seluruh wajah pada frame_gambar, memotong area kotak wajah dengan margin 12%
    melalui python/yolo/face_cropper.py, lalu mengembalikan daftar koordinat bbox, skor confidence,
    dan array piksel wajah untuk dikirim ke modul preprocessing dan FaceNet.
    """
    if frame_gambar is None:
        return []

    daftar_hasil_yolo = deteksi_kotak_wajah_pada_frame(frame_gambar)
    daftar_wajah_terdeteksi = []

    for hasil_item in daftar_hasil_yolo:
        kumpulan_kotak: Any = getattr(hasil_item, "boxes", None)
        if kumpulan_kotak is None:
            continue

        for kotak_deteksi in kumpulan_kotak:
            koordinat_xyxy = kotak_deteksi.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = [int(round(nilai)) for nilai in koordinat_xyxy]
            skor_confidence = float(kotak_deteksi.conf[0].cpu().numpy().item())

            koordinat_bbox = [x1, y1, x2, y2]
            foto_ekstraksi_wajah = potong_kotak_wajah_dengan_margin(
                frame_gambar,
                koordinat_bbox,
                rasio_margin=rasio_margin_crop,
            )

            if validasi_potongan_wajah(foto_ekstraksi_wajah):
                daftar_wajah_terdeteksi.append(
                    {
                        "bbox": koordinat_bbox,
                        "confidence": round(skor_confidence, 4),
                        "crop": foto_ekstraksi_wajah,
                    }
                )

    return daftar_wajah_terdeteksi


def prediksi_wajah_pada_video(path_file_video: str | Path) -> dict:
    """
    Memproses file video frame demi frame menggunakan model YOLOv8 hasil training mandiri
    dan merangkum seluruh koordinat wajah yang ditemukan ke dalam struktur dictionary.
    """
    waktu_mulai = time.time()
    muat_model_hasil_training_yolo()

    objek_video = open_video(path_file_video)
    total_frame_video = get_total_frame(objek_video)
    nilai_fps_video = get_fps(objek_video)
    resolusi_video = get_resolution(objek_video)

    indeks_frame = 0
    semua_deteksi_frame = []
    total_potongan_wajah = 0

    try:
        while True:
            berhasil_baca, frame_saat_ini = read_frame(objek_video)
            if not berhasil_baca or frame_saat_ini is None:
                break

            deteksi_frame_ini = prediksi_wajah_pada_frame(frame_saat_ini)
            if deteksi_frame_ini:
                daftar_wajah_serializable = []
                for item_deteksi in deteksi_frame_ini:
                    total_potongan_wajah += 1
                    daftar_wajah_serializable.append(
                        {
                            "bbox": item_deteksi["bbox"],
                            "confidence": item_deteksi["confidence"],
                        }
                    )

                semua_deteksi_frame.append(
                    {
                        "frame_index": indeks_frame,
                        "faces_count": len(daftar_wajah_serializable),
                        "faces": daftar_wajah_serializable,
                    }
                )

            indeks_frame += 1
    finally:
        release_video(objek_video)

    durasi_proses = round(time.time() - waktu_mulai, 2)
    return {
        "video_path": str(path_file_video),
        "total_frames": total_frame_video,
        "processed_frames": indeks_frame,
        "fps": nilai_fps_video,
        "resolution": resolusi_video,
        "total_faces_detected": total_potongan_wajah,
        "processing_time_seconds": durasi_proses,
        "detections": semua_deteksi_frame,
    }


def ekspor_hasil_deteksi_ke_json(data_deteksi: dict, path_file_output: str | Path) -> str:
    """
    Menyimpan hasil deteksi wajah ke dalam file berformat JSON pada path_file_output.
    """
    path_tujuan = Path(path_file_output)
    path_tujuan.parent.mkdir(parents=True, exist_ok=True)
    with open(path_tujuan, "w", encoding="utf-8") as file_json:
        json.dump(data_deteksi, file_json, indent=2)
    return str(path_tujuan)


# Menyediakan alias fungsi untuk kompatibilitas pemanggilan di python/yolo/__init__.py dan yolo_service.py
load_model = muat_model_hasil_training_yolo
detect_faces = deteksi_kotak_wajah_pada_frame
predict_frame = prediksi_wajah_pada_frame
predict_video = prediksi_wajah_pada_video
export_detection = ekspor_hasil_deteksi_ke_json
