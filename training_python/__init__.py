"""Paket training_python — Pemisahan Modul Training Model YOLOv8 (Folder 01) dan Training Dataset Aktor (Folder 02)."""

import importlib
from . import konfigurasi_training

_modul_persiapan_yolo = importlib.import_module(".01_training_model_yolo.persiapan_dataset_yolo", package=__name__)
_modul_training_yolo = importlib.import_module(".01_training_model_yolo.training_dan_tuning_model_yolo", package=__name__)
_modul_crop_wajah = importlib.import_module(".02_training_dataset_wajah_aktor.tahap_01_crop_dan_preprocess_wajah", package=__name__)
_modul_training_facenet = importlib.import_module(".02_training_dataset_wajah_aktor.tahap_02_training_facenet_triplet", package=__name__)
_modul_ekstraksi_embedding = importlib.import_module(".02_training_dataset_wajah_aktor.tahap_03_ekstraksi_embedding_aktor", package=__name__)
_modul_evaluasi_f1 = importlib.import_module(".02_training_dataset_wajah_aktor.tahap_04_evaluasi_euclidean_dan_f1", package=__name__)

siapkan_dan_split_dataset_yolo = _modul_persiapan_yolo.siapkan_dan_split_dataset_yolo
muat_arsitektur_yolov8_polos = _modul_training_yolo.muat_arsitektur_yolov8_polos
latih_model_yolov8_dari_nol = _modul_training_yolo.latih_model_yolov8_dari_nol
jalankan_tuning_hyperparameter_yolo = _modul_training_yolo.jalankan_tuning_hyperparameter_yolo
evaluasi_model_yolo_pada_split_test = _modul_training_yolo.evaluasi_model_yolo_pada_split_test

ekstrak_dan_preprocess_wajah_dataset = _modul_crop_wajah.ekstrak_dan_preprocess_wajah_dataset
latih_model_facenet_triplet_loss = _modul_training_facenet.latih_model_facenet_triplet_loss
buat_database_embedding_referensi = _modul_ekstraksi_embedding.buat_database_embedding_referensi
kalibrasi_threshold_dan_evaluasi_matrix_f1 = _modul_evaluasi_f1.kalibrasi_threshold_dan_evaluasi_matrix_f1

__all__ = [
    "konfigurasi_training",
    "siapkan_dan_split_dataset_yolo",
    "muat_arsitektur_yolov8_polos",
    "latih_model_yolov8_dari_nol",
    "jalankan_tuning_hyperparameter_yolo",
    "evaluasi_model_yolo_pada_split_test",
    "ekstrak_dan_preprocess_wajah_dataset",
    "latih_model_facenet_triplet_loss",
    "buat_database_embedding_referensi",
    "kalibrasi_threshold_dan_evaluasi_matrix_f1",
]
