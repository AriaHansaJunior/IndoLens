# IndoLens — Indonesian Actor Recognition System

**IndoLens** adalah sistem pengenalan wajah aktor Indonesia berbasis kecerdasan buatan (*Computer Vision*) yang menggabungkan **YOLOv8** (Face Detection) dan **FaceNet** (128-D Facial Feature Embedding & Recognition) dengan antarmuka web **Laravel 11** modern.

---

## 🏗️ Architecture Overview

- **Single Orchestrator**: Laravel bertanggung jawab mengelola antarmuka pengguna (UI), database MySQL, validasi, dan alur aplikasi.
- **Pure AI Processing Engine**: Python bertugas murni untuk deteksi wajah (*YOLOv8*), ekstraksi fitur & klasifikasi identitas (*FaceNet*), serta rendering *Overlay*.
- **Master Data Independence**: Sistem dirancang agnostik terhadap jumlah data aktor di database (1 hingga 30+ aktor tanpa perubahan kode).

---

## 📁 Project Structure

```text
IndoLens/
├── app/                        # Logika Utama Laravel Backend
│   ├── Http/Controllers/       # Controller (HomeController, ActorController, RecognitionController)
│   ├── Models/                 # Model Eloquent (Actor, Movie, Character, ActorAward, dll)
│   └── Services/               # Orchestration & Service Layer
│       ├── ActorService.php    # Relasi Metadata Aktor & Karakter
│       ├── RecognitionService.php # Koordinasi Pipeline Upload & AI Process
│       ├── ResultParserService.php# Validasi & Parsing Output JSON Python
│       └── Python/             # Symfony Process wrapper untuk eksekusi Python
├── config/                     # Berkas Konfigurasi Aplikasi (recognition.php, dll)
├── database/
│   ├── migrations/             # Struktur Tabel Database MySQL
│   └── seeders/                # Seeder Data Master Aktor & Film
├── python/                     # Core Processing Engine (Python)
│   ├── config/                 # Konfigurasi Path & Hyperparameter (threshold, resolution)
│   ├── datasets/               # Dataset Wajah Aktor (FaceNet Training Data)
│   ├── embeddings/             # Simpanan Vektor 128-D (.npy)
│   ├── evaluation/             # Modul Evaluasi Performa Bab 4 (metrics, confusion_matrix, performance)
│   ├── facenet/                # Implementasi Modul Ekstraksi FaceNet
│   ├── recognition/            # Engine Pengenalan Wajah & Threshold Matching
│   ├── utils/                  # Utility Scripts (logger, exception, validator, image loader)
│   ├── yolo/                   # Detektor Wajah YOLOv8
│   └── main.py                 # CLI Orchestrator Utama Python Engine
├── resources/                  # Frontend Blade Templates, Modern CSS, dan Vanilla JavaScript
│   ├── css/                    # Custom Styling per Halaman (home, actors, actor-detail)
│   ├── js/                     # Client-Side DOM Search & Interaction Logic
│   └── views/                  # Blade Templates Layout & Views
├── routes/                     # Definition Endpoint Web Routes (web.php)
└── storage/                    # Simpanan Berkas Sementara & Storage Link Public
```

---

## 🛠️ Prerequisites & Requirements

### System Requirements:
- **PHP** >= 8.2
- **Composer** >= 2.0
- **Node.js** >= 18.0 & **npm**
- **Python** >= 3.10
- **MySQL / MariaDB**

### Python Packages (`python/requirements.txt`):
- `torch` & `torchvision`
- `facenet-pytorch`
- `ultralytics` (YOLOv8)
- `opencv-python`
- `scikit-learn`
- `matplotlib`
- `psutil`
- `numpy`

---

## 🚀 Installation & Setup Guide

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/your-repo/IndoLens.git
cd IndoLens

# Copy Environment File
cp .env.example .env
```

### 2. Install PHP & Node Dependencies
```bash
composer install
npm install
```

### 3. Generate App Key & Database Setup
Sesuaikan kredensial MySQL pada berkas `.env`, lalu jalankan:
```bash
php artisan key:generate
php artisan migrate:fresh --seed
php artisan storage:link
```

### 4. Install Python Dependencies
```bash
pip install -r python/requirements.txt
```

---

## 🎮 How to Run IndoLens

### 1. Jalankan Assets Bundler & Web Server
Buka terminal dan jalankan:
```bash
# Terminal 1: Vite Dev Server
npm run dev

# Terminal 2: Laravel Server
php artisan serve
```
Akses aplikasi melalui peramban di: `http://127.0.0.1:8000`

### 2. Generate FaceNet Embeddings (Python)
Untuk membuat ulang atau memperbarui file embedding `.npy` dari dataset:
```bash
python python/main.py generate-embeddings
```

### 3. Jalankan Pengenalan Wajah via CLI (Opsional)
```bash
python python/main.py recognize-video public/videos/demo.mp4
```

### 4. Menjalankan Modul Evaluasi (Bab 4 Skripsi)
Untuk menguji performa presisi, recall, F1-score, dan confusion matrix:
```bash
python python/tests/test_evaluation.py
```
Hasil evaluasi akan otomatis diekspor ke folder `python/outputs/reports/` (`evaluation.json`, `evaluation.csv`, `evaluation_summary.txt`) dan `python/outputs/evaluation/confusion_matrix.png`.

---

## 📜 License
Proyek IndoLens dikembangkan untuk keperluan akademik dan penelitian skripsi.
