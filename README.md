# IndoLens — Indonesian Actor Recognition System

<div align="center">

![IndoLens Logo](public/img/logo.png)

### Sistem Pengenalan Wajah Aktor Indonesia Berbasis Computer Vision & Web Real-Time
**Tugas Akhir / Skripsi Program Studi Teknik Informatika**

**Pengembang:** Aria Hansa Junior (**160423037**)  
**Teknologi Utama:** Laravel 11 · Python (YOLOv8 & FaceNet) · FastAPI · Vite · Node.js HTTPS Gateway

---

</div>

## 📌 Tentang IndoLens

**IndoLens** adalah sistem identifikasi dan pengenalan wajah aktor film Indonesia secara *real-time*. Sistem ini menggabungkan model *deep learning* state-of-the-art dengan arsitektur web modern yang dirancang khusus untuk pengujian akademis skripsi:
- **YOLOv8 (Face Detection):** Mendeteksi koordinat *bounding box* wajah pada frame video secara ultra-cepat dan akurat.
- **FaceNet (InceptionResnetV1):** Mengekstraksi representasi fitur wajah berdimensi 128 (*128-D facial embeddings*) dari crop wajah yang terdeteksi.
- **Euclidean Distance Matcher:** Mengklasifikasikan identitas aktor berdasarkan jarak vektor terhadap data referensi aktor dengan batas ambang (*threshold matching*) untuk membedakan wajah **Known** (terdaftar) vs **Unknown** (asing).
- **Laravel 11 Orchestrator:** Mengelola master data aktor, peran karakter film, biografi, antarmuka web responsif satu layar (*single-screen compact UI*), serta REST API.
- **Node.js HTTPS Reverse Proxy:** Menyediakan sertifikat SSL/TLS mandiri agar kamera smartphone atau laptop dapat diakses melalui jaringan lokal (LAN/Wi-Fi) sesuai standar keamanan WebRTC `getUserMedia()`.

---

## 🏗️ Arsitektur Sistem

Sistem IndoLens beroperasi secara *decoupled* (terpisah) melalui 4 lapisan layanan yang saling terhubung:

```
[ Browser Client (Desktop / Smartphone) ]
                  │
     HTTPS:8000   ▼
┌───────────────────────────────────────────────┐
│        Node.js HTTPS Gateway (Port 8000)      │
│  - SSL/TLS Termination (Root CA & Certs)      │
│  - WebRTC getUserMedia() Permission Enabler   │
└───────┬───────────────────────────────┬───────┘
        │ Proxy / HTTP                  │ Hot Reload / Assets
        ▼                               ▼
┌───────────────────────────────┐ ┌───────────────────────────────┐
│   Laravel Backend (Port 8001) │ │    Vite Dev Server (Port 5173)│
│  - MVC & Blade Templates      │ │  - CSS & Vanilla JS Bundler   │
│  - MySQL Master Data          │ └───────────────────────────────┘
│  - Active Actor Sync API      │
│  - Proxy Route to YOLO (/api) │
└───────┬───────────────────────┘
        │ Internal HTTP Proxy
        ▼
┌─────────────────────────────────────────────────────────────────┐
│         Python FastAPI AI Micro-Service (Port 8002)             │
│  - YOLOv8 Face Detector (Preloaded in RAM)                      │
│  - FaceNet InceptionResnetV1 (Preloaded in RAM)                 │
│  - Reference Embeddings Cache (python/embeddings/*.npy)         │
│  - Euclidean Distance & Threshold Classifier (<= 0.65)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Fitur & Modul Utama

### 1. 🎭 Direktori Aktor (`/actors`)
- Katalog aktor interaktif dengan grid kartu modern, status deteksi (*Known/Unknown*), dan pencarian instan sisi klien berdasarkan nama aktor maupun peran film.
- Tampilan satu layar *compact* tanpa pemotongan border saat di-hover.

### 2. 📋 Detail Aktor & Real-time Role Highlighting (`/actors/{id}`)
- Layout split proporsional: Foto aktor, metadata demografis (Gender, Usia, Tanggal Lahir, Tempat Lahir), daftar filmografi & peran, serta biografi lengkap.
- **Sinkronisasi Deteksi Real-Time:** Jika wajah aktor terdeteksi pada kamera, halaman detail secara otomatis menampilkan pill status peran aktif (*Active Character Role*).
- Tautan profil eksternal terintegrasi ke Instagram, Wikipedia, dan IMDb.

### 3. 📷 Live Camera Recognition (`/camera`)
- **Rasio Fokus 80/20 (Standar Skripsi):**
  - **80% Viewfinder Kamera:** Area streaming kamera responsif dengan *overlay canvas* kalkulasi koordinat bounding box YOLO, indikator state video (*Running* vs *Paused*), tombol ganti kamera (*Flip* kamera depan/belakang), dan snapshot instan.
  - **20% Panel Hasil Deteksi:** Daftar kartu aktor yang terdeteksi secara real-time, menampilkan nama, peran karakter film, nilai Euclidean distance, tautan profil, serta metrik latensi inferensi (*YOLO latency & FaceNet latency*).
- **Compact Viewport Guarantee:** Seluruh tata letak terkunci dalam batas 1 viewport layar desktop (`100vh`) tanpa *vertical scrollbar*.

### 4. 🏕️ Camp Administration Master Data (`/camp`)
- Modul administrasi master data aktor: Tambah, edit, dan hapus data aktor beserta filmografi dan tautan sosial media.
- **Manajemen Dataset Wajah (`/camp/{id}/faces`):** Unggah foto wajah latih untuk generate embedding FaceNet baru.

### 5. 📊 Python AI Pipeline & Evaluasi Model
- **Generate Embeddings:** Ekstraksi batch seluruh dataset wajah di folder `python/datasets/` menghasilkan vektor `.npy` di `python/embeddings/`.
- **Evaluasi Performa (Bab 4 Skripsi):** Pengujian metrik Precision, Recall, F1-Score, dan Confusion Matrix yang otomatis diekspor ke format JSON, CSV, serta grafik matriks `confusion_matrix.png`.

---

## 📁 Struktur Direktori Proyek

```text
IndoLens/
├── app/                          # Logika Utama Laravel Backend
│   ├── Http/Controllers/         # ActorController, CameraController, CampController, dll.
│   ├── Models/                   # Model Eloquent (Actor, Character, Movie, ActorAward, dll.)
│   └── Services/                 # Service Layer & Orchestrator
├── certs/                        # Sertifikat SSL/TLS Mandiri (Root CA & Server Certs)
├── config/                       # Konfigurasi Laravel
├── database/
│   ├── migrations/               # Skema Tabel Database MySQL
│   └── seeders/                  # Seeder Data Aktor & Karakter (ActorSeeder, MovieSeeder, dll.)
├── proxy-https.js                # Gateway HTTPS Node.js untuk akses kamera via LAN
├── python/                       # Core AI Processing Micro-Service & Tools
│   ├── config/                   # Hyperparameter (Ambang threshold, path dataset, resolusi)
│   ├── datasets/                 # Folder Dataset Foto Wajah Aktor (per nama aktor)
│   ├── embeddings/               # Simpanan Vektor Referensi 128-D (.npy)
│   ├── evaluation/               # Modul Evaluasi Skripsi (Confusion Matrix, Metrics, Performance)
│   ├── facenet/                  # Ekstraksi Feature Vector FaceNet InceptionResnetV1
│   ├── recognition/              # Modul Pencocokan Jarak Euclidean & Classifier
│   ├── tests/                    # Unit Test & Script Evaluasi Model
│   ├── weights/                  # Bobot Model YOLOv8 (yolov8n-face.pt)
│   ├── yolo/                     # Detektor Wajah YOLOv8
│   ├── generate_embeddings.py    # CLI Pembuatan File Embedding Aktor
│   └── yolo_service.py           # FastAPI Micro-Service Endpoint (/detect)
├── resources/
│   ├── css/                      # Custom Stylesheet per Halaman (app, actors, actor-detail, camera, camp)
│   ├── js/                       # Script Interaktif DOM & WebRTC Camera
│   └── views/                    # Blade Template Layout & Views
├── routes/                       # Definisi Rute Web & API (web.php)
└── storage/                      # File Upload, Foto Aktor, dan Symlink Public
```

---

## 🛠️ Kebutuhan Sistem & Dependensi

### Kebutuhan Perangkat Lunak:
- **PHP** >= 8.2 (dengan ekstensi `pdo_mysql`, `mbstring`, `fileinfo`)
- **Composer** >= 2.0
- **Node.js** >= 18.0 & **npm**
- **Python** >= 3.10
- **Database MySQL / MariaDB** (melalui Laragon / XAMPP)

### Dependensi Python Utama (`python/requirements.txt`):
```text
ultralytics         # YOLOv8 Object & Face Detection
facenet-pytorch     # FaceNet InceptionResnetV1 Pretrained Model
torch & torchvision # PyTorch Deep Learning Runtime
opencv-python       # Image Processing & Frame Manipulation
numpy               # Vector & Matrix Manipulations
scikit-learn        # Evaluation Metrics & Confusion Matrix
fastapi & uvicorn   # High Performance Micro-Service API
```

---

## 🚀 Panduan Instalasi & Setup

### 1. Kloning Repositori & Persiapan Environment
```bash
git clone https://github.com/your-repo/IndoLens.git
cd IndoLens

# Salin berkas environment
copy .env.example .env
```

### 2. Konfigurasi Database (.env)
Buka file `.env` dan sesuaikan konfigurasi database MySQL:
```env
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=indolens
DB_USERNAME=root
DB_PASSWORD=
```

### 3. Install Dependensi PHP & Node.js
```bash
composer install
npm install
```

### 4. Setup Database & Storage Symlink
```bash
php artisan key:generate
php artisan migrate:fresh --seed
php artisan storage:link
```

### 5. Install Dependensi Python
```bash
pip install -r python/requirements.txt
```

### 6. Generate Vektor Embedding Aktor
Pastikan dataset foto wajah telah diletakkan di `python/datasets/<Nama_Aktor>/`, lalu jalankan:
```bash
python python/generate_embeddings.py
```
*File embedding akan otomatis dihasilkan di direktori `python/embeddings/`.*

---

## 🎮 Cara Menjalankan Aplikasi

### Opsi A: Menjalankan Seluruh Service Sekaligus (Sangat Direkomendasikan)
Jalankan satu perintah berikut untuk mengaktifkan seluruh stack IndoLens secara otomatis (HTTPS Gateway, Laravel Backend, Vite, dan Python AI Service):
```bash
npm run dev:all
# Atau via batch script di Windows:
.\dev.bat
```

Setelah perintah dijalankan, akses antarmuka web melalui:
- **Laptop / PC Desktop (HTTP):** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Laptop / PC Desktop (HTTPS):** [https://localhost:8000](https://localhost:8000)
- **Smartphone / Perangkat LAN (Kamera HTTPS):** `https://<IP_KOMPUTER>:8000/camera`  
  *(Contoh: `https://192.168.1.10:8000/camera`)*

---

### Opsi B: Menjalankan Service Secara Terpisah (Manual Terminal)
Jika ingin memantau log masing-masing service di terminal terpisah:

```bash
# Terminal 1: Node.js HTTPS Gateway Proxy (Port 8000)
npm run gateway

# Terminal 2: Laravel Backend Server (Port 8001)
npm run laravel

# Terminal 3: Vite Asset Bundler
npm run dev

# Terminal 4: Python AI YOLOv8 + FaceNet Micro-Service (Port 8002)
npm run yolo
```

---

## 🧪 Pengujian & Evaluasi Model (Bab 4 Skripsi)

Untuk menjalankan benchmark pengujian akurasi, presisi, recall, F1-score, dan confusion matrix:
```bash
python python/tests/test_evaluation.py
```

Laporan hasil pengujian akan otomatis diekspor ke:
- `python/outputs/reports/evaluation.json` (Detail metrik per kelas)
- `python/outputs/reports/evaluation.csv` (Tabel matriks metrik)
- `python/outputs/reports/evaluation_summary.txt` (Ringkasan performa sistem)
- `python/outputs/evaluation/confusion_matrix.png` (Visualisasi Confusion Matrix)

---

## 👨‍🎓 Informasi Peneliti

- **Nama Peneliti:** Aria Hansa Junior
- **NIM:** 160423037
- **Fakultas / Program Studi:** Teknik Informatika
- **Topik Penelitian:** Sistem Identifikasi & Pengenalan Wajah Aktor Film Indonesia Menggunakan Kombinasi YOLOv8 dan FaceNet Berbasis Web Real-Time.

---

## 📜 Lisensi & Catatan Akademik
Proyek ini dikembangkan secara eksklusif untuk kepentingan penelitian skripsi dan pengembangan akademis. Hak cipta dataset wajah dan informasi film milik masing-masing pemegang hak cipta terkait.
