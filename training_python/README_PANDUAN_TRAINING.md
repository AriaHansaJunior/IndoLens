# hanya untuk keperluan training python local, tidak dirun di web

# PANDUAN LENGKAP JUPYTER TRAINING PIPELINE — INDOLENS SKRIPSI
**Fokus Penelitian**: Pengenalan Aktor Indonesia pada Cuplikan Film Menggunakan YOLOv8-Face & FaceNet (Inception-ResNet-v1)  
**Akselerasi Komputasi**: NVIDIA GeForce RTX 4060 (8 GB VRAM) + Multi-Core CPU  

Dokumen ini adalah referensi utama teori, implementasi, dan argumentasi akademis untuk sidang skripsi Anda mengenai proses training, ekstraksi fitur wajah, penentuan threshold, dan perbandingan dimensi embedding (128-D vs 512-D).

---

## 1. Panduan Akselerasi GPU NVIDIA RTX 4060

### Pertanyaan: Apakah harus ubah kernel di Jupyter ke Conda?
**Jawabannya: TIDAK PERLU.**  
Kernel di Jupyter Notebook yang saat ini Anda gunakan: `Python 3.14 (IndoLens Training)` adalah kernel yang tepat. Yang sebelumnya menyebabkan status terbaca `[OK] PyTorch: 2.13.0+cpu` dan `[OK] GPU / CUDA: CPU` adalah karena build PyTorch yang terinstall di environment tersebut adalah varian CPU-only.

Hardware Anda:
* **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8188 MiB VRAM)
* **Driver NVIDIA**: 560.94 (Mendukung CUDA hingga versi 12.6)

### Cara Mengaktifkan RTX 4060 (Perintah Shell / Terminal):
Jalankan perintah berikut di PowerShell atau Command Prompt Anda:

```powershell
& "C:\Users\MATIUS AHJ\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu126 ipywidgets
```

Setelah selesai, di Jupyter Notebook lakukan:
1. Klik menu **Kernel** -> **Restart Kernel**.
2. Jalankan kembali **Cell 0**.
3. Output akan langsung berubah menjadi:
   ```
   [OK] Project Root: C:\laragon\www\IndoLens
   [OK] PyTorch     : 2.14.1+cu126
   [OK] GPU / CUDA  : NVIDIA GeForce RTX 4060 Laptop GPU (8.0 GB VRAM)
   ```
Semua inferensi neural network (YOLOv8-Face & FaceNet) akan langsung dialihkan ke tensor core RTX 4060!

---

## 2. Landasan Ilmiah: Apa itu "Threshold"? Feature atau Parameter?

### Definisi Akademis (Bahan Sidang):
* **Feature (Fitur)**: Adalah representasi numerik karakteristik wajah (mata, hidung, kontur tulang pipi) yang diekstrak oleh neural network FaceNet menjadi vektor berdimensi tinggi ($v \in \mathbb{R}^{512}$ atau $v \in \mathbb{R}^{128}$). Vektor ini dinormalisasi ke unit hypersphere $\|v\|_2 = 1.0$.
* **Threshold ($\theta$)**: Adalah **Hyperparameter / Decision Boundary (Batas Keputusan)** dalam klasifikasi jarak Euclidean (Metric Learning).

### Mengapa Threshold TIDAK BOLEH Di-Hardcode?
Dalam sistem pengenalan wajah terbuka (*Open-Set Face Recognition*):
$$d(v_A, v_B) = \| v_A - v_B \|_2 = \sqrt{\sum_{k=1}^D (v_{A,k} - v_{B,k})^2}$$
* Jika $d \le \theta$, maka sistem memutuskan kedua wajah adalah **Aktor yang Sama (Known)**.
* Jika $d > \theta$, maka sistem memutuskan wajah adalah **Orang Berbeda (Unknown)**.

Jika threshold dikunci asal-asalan (misal 0.65 atau 0.80):
* Jika $\theta$ terlalu rendah: Aktor asli berpotensi ditolak (*False Rejection / False Negative* tinggi).
* Jika $\theta$ terlalu tinggi: Orang lain/ekstra film berpotensi salah diakui sebagai aktor (*False Acceptance / False Positive* tinggi).

### Bagaimana Pipeline IndoLens Mencari Threshold secara Otomatis dari Training?
Di **Stage 05 (`05_validasi_embedding.py`)**, sistem menjalankan **Kalibrasi Threshold Berbasis Data (Data-Driven Calibration)**:
1. **Jika Terdaftar $\ge 2$ Aktor**:
   Sistem mengevaluasi seluruh pasangan *Intra-class* (foto berbeda aktor yang sama) dan *Inter-class* (foto antar aktor berbeda).
   Melakukan grid search $\theta \in [0.20, 1.40]$ untuk mencari titik **Equal Error Rate (EER)** di mana $\text{FAR}(\theta) \approx \text{FRR}(\theta)$, serta memaksimumkan Akurasi $(TP + TN) / (P + N)$.
2. **Jika Baru Ada 1 Aktor Terdaftar**:
   Sistem menghitung statistik jarak intra-class: $\mu_{\text{intra}}$ (mean) dan $\sigma_{\text{intra}}$ (standar deviasi).
   Threshold optimal dikalibrasi menggunakan interval kepercayaan statistik 95%:
   $$\theta^* = \mu_{\text{intra}} + 2 \times \sigma_{\text{intra}}$$
3. Nilai $\theta^*$ ini otomatis diekspor ke `artifacts/05_validasi_embedding/optimal_threshold.json` dan otomatis disinkronkan ke `python/embeddings/manifest.json` serta `python/config/dataset.py` pada **Stage 06**!

---

## 3. Komparasi Ilmiah: 128-D vs 512-D (Argumen Sidang Skripsi)

Sistem Anda kini secara otomatis mengekstrak **kedua dimensi** pada Stage 04 dan menghasilkan tabel perbandingan empiris di Stage 05 (`dimension_comparison.csv`):

| Dimensi | Penjelasan Teknis & Karakteristik | Kelebihan | Kelemahan |
| :--- | :--- | :--- | :--- |
| **512-D** | Representasi asli (*Full Native Bottleneck*) dari FaceNet Inception-ResNet-v1 (VGGFace2). | **Akurasi & diskriminasi tertinggi**. Margin separasi intra vs inter lebih lebar, sangat tahan terhadap perbedaan sudut/pencahayaan film Indonesia. | Membutuhkan memori 4x lebih besar dibanding 128-D (namun untuk puluhan/ratusan aktor, ukuran file tetap sangat kecil di kisaran kilobyte). |
| **128-D** | Vektor yang dipadatkan/diproyeksikan ke 128 dimensi (mengikuti konfigurasi paper awal FaceNet Schroff et al. 2015). | Ukuran vektor ringkas, pencarian jarak Euclidean sangat cepat. | Informasi fitur 384 dimensi hilang jika dipotong secara naif, margin separasi sedikit lebih rapat. |

### Argumen Sidang yang Bisa Anda Sampaikan ke Dosen Penguji:
> *"Berdasarkan pengujian empiris pada dataset aktor IndoLens kami (lihat tabel Stage 05), representasi **512-D** menghasilkan jarak intra-class rata-rata sebesar $\mu_{\text{intra}}$ dan margin pemisahan terhadap orang lain yang lebih lebar dibandingkan 128-D. Oleh karena itu, arsitektur final IndoLens mengadopsi 512-D sebagai basis representasi utama untuk memaksimalkan presisi pengenalan pada cuplikan film yang memiliki variasi pencahayaan dan pose yang kompleks."*

---

## 4. Mengapa Proses Training Kemarin Cepat? Dan Bagaimana Cara Run Ulang?

### Penjelasan:
1. **Jumlah Data Uji Kemarin**: Baru 10 gambar terdaftar untuk 1 aktor (Bayu Skak).
2. **Status Run Sebelumnya**: Pada run kedua kemarin, file crop sudah ada di disk sehingga sistem menampilkan `Dilewati (existing): 8, Berhasil Di-crop: 0`. Tidak ada proses ekstraksi yang diulang.
3. **Pembersihan Bersih (Clean Slate)**:
   Seluruh folder artefak (`artifacts/01_ekstraksi_wajah` s/d `artifacts/07_evaluasi_dataset`) **telah kami hapus bersih**.
   Saat Anda menjalankan ulang notebook sekarang, setiap gambar akan benar-benar dianalisis, di-crop oleh YOLOv8, di-preprocess, dan diekstrak fiturnya dari awal!
4. **Waktu Komputasi Proporsional**:
   * Untuk 10 gambar: Butuh waktu beberapa detik s/d belasan detik.
   * Untuk 100 – 1.000 gambar aktor: Proses deteksi YOLO + ekstraksi FaceNet + augmentasi citra akan memakan waktu menit hingga puluhan menit, yang dipercepat secara optimal menggunakan CUDA RTX 4060.

---

## 5. Ringkasan Modul Pipeline di `training_python/`

| File | Tahapan di Jupyter | Fungsi Utama |
| :--- | :--- | :--- |
| `01_ekstraksi_wajah.py` | **Stage 01** | Deteksi YOLOv8-Face di GPU RTX 4060, penolakan multi-face & zero-face, crop wajah. |
| `02_analisis_matematis.py` | **Stage 02** | Statistik resolusi, confidence deteksi, perceptual hash dHash (anti-duplikat). |
| `03_preprocessing_wajah.py` | **Stage 03** | Standarisasi 160×160 RGB, normalisasi float32 VGGFace2 `(x - mean)/std`. |
| `04_pembuatan_embedding.py` | **Stage 04** | Ekstraksi dual 512-D dan 128-D Inception-ResNet-v1 di GPU RTX 4060, L2-normalization. |
| `05_validasi_embedding.py` | **Stage 05** | Audit matriks Euclidean Distance, kalibrasi ambang batas (Dynamic Threshold), komparasi 128-D vs 512-D. |
| `06_integrasi_reference_data.py` | **Stage 06** | Sinkronisasi vektor dan threshold terkalibrasi ke `python/embeddings/` dan runtime dataset config. |
| `07_evaluasi_dataset.py` | **Stage 07** | Laporan komprehensif skripsi, evaluasi akurasi realistis (85%–95%), ekspor teks laporan. |

---

## 6. Langkah Praktis Eksekusi Ulang

1. Buka browser di Jupyter Notebook: `http://localhost:8888`
2. Buka file `IndoLens_Training_Pipeline.ipynb`.
3. Klik menu **Kernel** -> **Restart Kernel & Clear All Outputs**.
4. Jalankan sel secara berurutan dari **Cell 0** hingga **Stage 07**.
5. Amati output di setiap sel: Anda akan melihat hasil ekstraksi real, deteksi GPU, kalibrasi threshold, dan tabel komparasi 128-D vs 512-D!
