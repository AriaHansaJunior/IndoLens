# hanya untuk keperluan training python local, tidak dirun di web

# PANDUAN LENGKAP JUPYTER TRAINING PIPELINE — INDOLENS SKRIPSI

Paket ini dirancang khusus untuk memproses dataset wajah aktor film Indonesia secara offline melalui **Jupyter Notebook (Anaconda)** menggunakan akselerasi GPU (NVIDIA RTX 4070) dan RAM 32 GB.

Sistem web Laravel + FastAPI murni bertindak sebagai **Inference Engine** yang memuat hasil reference embedding `.npy` secara langsung tanpa beban komputasi training.

---

## 1. Persiapan Lingkungan di Kernel Jupyter Notebook

Pastikan dependensi Python terpasang pada environment Jupyter (Anaconda):

```powershell
pip install ultralytics facenet-pytorch torch torchvision opencv-python pillow numpy mysql-connector-python
```

*(Catatan: PyTorch dengan dukungan CUDA untuk RTX 4070 dapat diinstal melalui: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`)*

---

## 2. Struktur Modul & Pemetaan Shell Jupyter

Setiap file di bawah ini dirancang utuh (self-contained) dan dapat langsung di-copy-paste ke dalam masing-masing cell/shell di Jupyter Notebook:

| Shell Notebook | File Sumber di `training_python/` | Deskripsi Komputasi | Artefak Output Utama |
| :---: | :--- | :--- | :--- |
| **Shell 01** | `01_ekstraksi_wajah.py` | Membaca MySQL (read-only), deteksi wajah YOLOv8 per-gambar, crop wajah presisi. | `artifacts/01_ekstraksi_wajah/crops/<actor_id>/<image_id>.png` & `extraction_manifest.json` |
| **Shell 02** | `02_analisis_matematis.py` | Analisis resolusi gambar, crop dimensions, confidence deteksi, dan deteksi duplikat (dHash). | `artifacts/02_analisis_matematis/analysis_report.json` & `.txt` |
| **Shell 03** | `03_preprocessing_wajah.py` | BGR -> RGB, resize 160×160, normalisasi float32 VGGFace2 `(x - mean)/std`. | `artifacts/03_preprocessing_wajah/tensors/<actor_id>/<image_id>.npy` & `previews/` |
| **Shell 04** | `04_pembuatan_embedding.py` | Inferensi FaceNet InceptionResnetV1 (vggface2), truncate 128-D, L2-normalization. | `artifacts/04_pembuatan_embedding/vectors/<actor_id>/<image_id>.npy` & `embedding_manifest.json` |
| **Shell 05** | `05_validasi_embedding.py` | Validasi bebas NaN/Inf, L2-norm == 1.0, audit matriks Euclidean Distance & flag anomali. | `artifacts/05_validasi_embedding/validation_report.json`, `.npy` matriks, & `flagged_pairs.csv` |
| **Shell 06** | `06_integrasi_reference_data.py` | Staging, backup aman runtime, dan promosi vektor ke `python/embeddings/<actor_slug>/`. | `python/embeddings/<actor_slug>/<image_id>.npy` & `manifest.json` |
| **Shell 07** | `07_evaluasi_dataset.py` | Rekapitulasi metrik menyeluruh skripsi dan evaluasi opsional probe set independen. | `artifacts/07_evaluasi_dataset/evaluation_report.json` & `.txt` |

### Modul Pendukung (Shared Helpers):
* `tp_config.py`: Sentral konfigurasi path dinamis (tidak bergantung `__file__`, aman di Jupyter).
* `tp_database.py`: Pembaca koneksi MySQL strictly read-only (`SET SESSION TRANSACTION READ ONLY`), membaca kredensial dari `.env` tanpa mencetak rahasia.
* `tp_dataset_loader.py`: Resolusi path Laravel storage anti path-traversal & image loader BGR/RGB.
* `tp_manifest_utils.py`: Atomic checkpointing (tulis file sementara lalu replace) agar terhindar dari korupsi data jika kernel dihentikan.

---

## 3. Urutan Eksekusi di Jupyter Notebook

1. **Buka Jupyter Notebook** (`http://localhost:8888`).
2. Buat notebook baru bernama `IndoLens_Training_Pipeline.ipynb`.
3. Buat cell secara berurutan:

### **Cell 0 (Opsional tapi Direkomendasikan): Setup & Pre-Flight Check**
Salin kode berikut untuk memverifikasi path, GPU, dependensi, dan koneksi MySQL read-only sebelum komputasi:
```python
import os, sys
from pathlib import Path
_ROOT = Path(os.environ.get("INDOLENS_ROOT", r"C:\laragon\www\IndoLens"))
for _p in [_ROOT, _ROOT / "training_python", _ROOT / "python"]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import tp_config as cfg
import tp_database as db
import torch

print("[✓] Project Root:", cfg.PROJECT_ROOT)
print("[✓] GPU / CUDA  :", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
records = db.fetch_actor_image_records()
print(f"[✓] MySQL Connected (Read-Only): Ditemukan {len(records)} record gambar aktor resmi.")
```

### **Cell 1: Ekstraksi Wajah (YOLOv8-Face)**
Salin seluruh isi `01_ekstraksi_wajah.py`.
- **Uji Coba 1 Gambar Aktual Pertama**:
  Ganti baris paling bawah menjadi:
  ```python
  run_stage_01(limit=1)
  ```
  Ini akan memproses tepat 1 gambar, menghasilkan crop wajah di `artifacts/01_ekstraksi_wajah/crops/`, dan menyimpan manifest. Anda dapat memeriksa hasil crop gambar tersebut.
- **Proses Keseluruhan**:
  Jalankan kembali dengan:
  ```python
  run_stage_01()
  ```
  Sistem otomatis mendeteksi checkpoint dan melanjutkan sisa gambar tanpa mengulang yang sudah berhasil (*safe resume*).

### **Cell 2 sampai Cell 7:**
- **Cell 2**: Salin seluruh isi `02_analisis_matematis.py`, lalu Run.
- **Cell 3**: Salin seluruh isi `03_preprocessing_wajah.py`, lalu Run.
- **Cell 4**: Salin seluruh isi `04_pembuatan_embedding.py`, lalu Run.
- **Cell 5**: Salin seluruh isi `05_validasi_embedding.py`, lalu Run.
- **Cell 6**: Salin seluruh isi `06_integrasi_reference_data.py`, lalu Run.
- **Cell 7**: Salin seluruh isi `07_evaluasi_dataset.py`, lalu Run.

Setiap shell mencetak log detail, metrik numerik, dan menyimpan checkpoint file. Jika proses dihentikan di tengah jalan, Anda cukup menjalankan ulang cell tersebut—sistem akan melanjutkan dari gambar terakhir yang belum selesai (*safe resume*).

---

## 4. Keamanan & Integritas Data

1. **Database MySQL**:
   * Sesi database dikunci dalam mode `READ ONLY`. Tidak ada perintah `INSERT`, `UPDATE`, `DELETE`, atau `ALTER` yang dikirim ke MySQL.
2. **Foto Asli di Storage**:
   * Foto asli di `storage/app/public/actor-images/` hanya dibaca (read-only), tidak pernah diubah atau dihapus.
3. **Reference Data Web**:
   * Sebelum mempromosikan hasil training ke `python/embeddings/`, Stage 06 secara otomatis membuat salinan cadangan (*backup*) bertanggal di `artifacts/06_integrasi_reference_data/backups/`.
   * Reference data aktor lain yang sudah ada tidak akan terhapus.
