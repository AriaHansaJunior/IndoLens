"""
training_python package — IndoLens Training Pipeline for Jupyter Notebook
Menyediakan akses modular ke konfigurasi, database, loader, manifest,
dan fungsi eksekusi seluruh tahapan pipeline (Stage 01 s/d Stage 07).
"""

import importlib
from . import tp_config
from . import tp_database
from . import tp_dataset_loader
from . import tp_manifest_utils

def _get_stage(stage_file: str):
    return importlib.import_module(f".{stage_file}", package=__name__)

def run_stage_01(*args, **kwargs):
    """Stage 01: Ekstraksi Wajah (YOLOv8-Face). Contoh: run_stage_01(limit=1) atau run_stage_01()"""
    return _get_stage("01_ekstraksi_wajah").run_stage_01(*args, **kwargs)

def run_stage_02(*args, **kwargs):
    """Stage 02: Analisis Matematis Dataset & dHash"""
    return _get_stage("02_analisis_matematis").run_stage_02(*args, **kwargs)

def run_stage_03(*args, **kwargs):
    """Stage 03: Preprocessing Wajah 160x160 Tensor & Normalisasi VGGFace2"""
    return _get_stage("03_preprocessing_wajah").run_stage_03(*args, **kwargs)

def run_stage_04(*args, **kwargs):
    """Stage 04: Pembuatan Embedding 128-D FaceNet (Inception-ResNet-v1)"""
    return _get_stage("04_pembuatan_embedding").run_stage_04(*args, **kwargs)

def run_stage_05(*args, **kwargs):
    """Stage 05: Validasi Kualitas Embedding & Audit Matriks Jarak Euclidean"""
    return _get_stage("05_validasi_embedding").run_stage_05(*args, **kwargs)

def run_stage_06(*args, **kwargs):
    """Stage 06: Integrasi Reference Data ke Runtime (python/embeddings/)"""
    return _get_stage("06_integrasi_reference_data").run_stage_06(*args, **kwargs)

def run_stage_07(*args, **kwargs):
    """Stage 07: Evaluasi Akhir Dataset & Rekapitulasi Metrik Skripsi"""
    return _get_stage("07_evaluasi_dataset").run_stage_07(*args, **kwargs)

__all__ = [
    "tp_config",
    "tp_database",
    "tp_dataset_loader",
    "tp_manifest_utils",
    "run_stage_01",
    "run_stage_02",
    "run_stage_03",
    "run_stage_04",
    "run_stage_05",
    "run_stage_06",
    "run_stage_07",
]
