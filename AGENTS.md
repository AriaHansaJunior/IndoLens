# IndoLens Project Guidelines

Aturan kerja permanen untuk seluruh perubahan kode di repositori IndoLens agar konsisten di setiap sesi. Wajib dibaca dan dipatuhi sebelum menulis atau mengubah kode apa pun.

## 1. Larangan Mutlak Model Pre-Trained (Zero Pre-Trained Policy)
- **Dilarang keras** menggunakan bobot (*weights*) atau model *pre-trained* instan dalam bentuk apa pun (seperti `yolov8n.pt`, `yolov8s.pt`, `yolov8n-face.pt`, `InceptionResnetV1(pretrained='vggface2')`, `pretrained=True`, atau mengimpor langsung model jadi dari `facenet_pytorch`).
- **YOLOv8 Deteksi Wajah:** Wajib menggunakan konfigurasi arsitektur YAML mandiri (`python/config/arsitektur_yolov8_wajah.yaml`, 1 kelas: `face`) dengan `pretrained=False` dan dilatih dari **Epoch 0** menggunakan dataset penelitian sendiri hingga menghasilkan file bobot mandiri (`storage/app/ai/weights/hasil_training_yolov8_wajah.pt`).
- **FaceNet & Triplet Loss:** Wajib ditulis sendiri struktur jaringan sarafnya dari nol menggunakan `torch.nn.Module` (blok *Convolutional*, *BatchNorm*, *ReLU*, *Residual/Inception Block* yang disesuaikan untuk GPU RTX 4060, *Fully Connected Embedding 512-D*, dan *L2-Normalization*), serta fungsi **Triplet Margin Loss (`Anchor`, `Positive`, `Negative`)** dan loop iterasi `epoch` manual hingga menghasilkan file bobot mandiri (`storage/app/ai/weights/hasil_training_facenet_aktor.pth`).
- Metode inti sistem wajib selaras dengan Landasan Teori Skripsi: **YOLOv8, FaceNet, Triplet Loss, Euclidean Distance, dan Confusion Matrix / Metrik Evaluasi (Accuracy, Precision, Recall, F1-Score)**.

## 2. Eksekusi Training Eksklusif di Jupyter Notebook Lokal & Force GPU RTX 4060
- Seluruh proses **training, tuning parameter, preprocessing dataset, pembuatan embedding referensi, kalibrasi threshold, dan evaluasi metrik (Confusion Matrix, F1-Score, dll.)** wajib ditulis dalam bahasa **Python** dan **hanya dijalankan oleh pengguna secara lokal melalui Jupyter Notebook** (`training_python/IndoLens_Training_Pipeline.ipynb`).
- **Dilarang keras** menjalankan proses training, tuning, atau evaluasi berat melalui halaman web, controller Laravel, atau dieksekusi langsung oleh agent di background/terminal. Agent hanya menyiapkan kode Python/Notebook, memverifikasi sintaks/import ringan, dan menjalankan server inferensi runtime saat diminta.
- Seluruh kode training dan inferensi wajib **memaksa penggunaan GPU `NVIDIA GeForce RTX 4060 Laptop GPU`** (terlihat sebagai **GPU 1** di Windows Task Manager karena GPU 0 adalah Intel UHD Graphics, dan terindeks sebagai `cuda:0` / `device=0` pada PyTorch CUDA karena CUDA hanya menghitung GPU NVIDIA). Kode wajib memverifikasi nama perangkat `NVIDIA GeForce RTX 4060` secara otomatis agar beban komputasi tidak jatuh ke CPU/iGPU.
- Jumlah iterasi (`epoch`) wajib ditentukan secara **proporsional dan efektif sesuai kebutuhan konvergensi sistem** (misalnya `50–100 epoch` dilengkapi mekanisme **Early Stopping / Patience** saat *validation loss* sudah stabil), bukan jumlah epoch berlebihan yang membuang waktu berhari-hari tanpa peningkatan akurasi.
- Seluruh path file (`Path`) di modul `training_python/` dan `python/` wajib menggunakan resolusi path absolut berbasis root proyek agar selalu terbaca dengan benar saat dikompilasi/dijalankan dari dalam Jupyter Notebook lokal.

## 3. Penamaan Variabel, Method, & Gaya Komentar (Tanpa Kata Ganti Orang)
- **Nama Variabel & Method Jelas (Tidak Disingkat):** Gunakan penamaan deskriptif yang mudah dipahami pada Python, JavaScript, maupun PHP/Laravel (contoh variabel: `data_hasil_training_yolo`, `foto_ekstraksi_wajah`, `vektor_embedding_wajah`, `jarak_euclidean_minimum`, `batas_ambang_jarak`; contoh method: `muat_model_hasil_training_yolo()`, `potong_kotak_wajah_dengan_margin()`, `hitung_jarak_euclidean()`, `cari_kecocokan_aktor_terdekat()`).
- **Komentar Alur Menggunakan Kata Kerja Langsung (Tanpa Kata Ganti):**
  - Tulis komentar penjelasan alur yang menerangkan dari folder/file mana data diambil, proses apa yang dilakukan method tersebut, dan ke file/method mana hasilnya dikirimkan.
  - **Dilarang menggunakan kata ganti orang** (`saya`, `aku`, `kamu`, `anda`, `dia`, `kita`, dll.). Gunakan awalan kata kerja langsung, contoh:
    - `# Mengambil gambar mentah dari folder dataset untuk diubah menjadi array piksel RGB 160x160`
    - `# Memotong area wajah berdasarkan koordinat bounding box sebelum dikirim ke modul FaceNet`
    - `# Menghitung jarak Euclidean antara vektor input dan vektor referensi lalu membandingkan terhadap batas ambang`

## 4. Struktur Folder Dataset Penelitian (`python/datasets/`)
- Dataset deteksi wajah YOLOv8:
  - `python/datasets/dataset_yolo_wajah/raw_wajah_manusia/` (gambar wajah manusia + label `.txt` format YOLO)
  - `python/datasets/dataset_yolo_wajah/raw_negatif_bukan_wajah/` (gambar hewan/kera, benda, pemandangan tanpa wajah manusia sebagai *background negative sample*)
  - `python/datasets/dataset_yolo_wajah/split_yolo/` (`images/train`, `images/val`, `images/test`, `labels/train`, `labels/val`, `labels/test`, dan `data_yolo_wajah.yaml`)
- Dataset pengenalan aktor FaceNet (Triplet Loss):
  - `python/datasets/dataset_facenet_aktor/wajah_aktor_target/<slug_aktor>/` (serta terintegrasi dengan `storage/app/public/actor-images/{id}-{slug}/`)
  - `python/datasets/dataset_facenet_aktor/wajah_orang_random/` (wajah non-aktor untuk sampel *Negative* Triplet Loss dan uji kelas `Unknown` pada Confusion Matrix)
  - `python/datasets/dataset_facenet_aktor/crop_wajah_160x160/` (hasil crop & preprocessing siap training FaceNet)

## 5. File Sementara & Kebersihan Workspace
- File sementara (`scratch/`, skrip ad-hoc, foto/video dummy, output uji di `python/temp/`) boleh dibuat selama proses verifikasi ringan, tetapi **wajib dihapus sebelum mengakhiri sesi** begitu pengujian berhasil.
- Test otomatis ditempatkan di `tests/` (PHPUnit) dan `python/tests/` (unittest) serta wajib membersihkan file sementara masing-masing (`tearDown` / `Storage::fake`).

## 6. Keamanan URL, Database, Penyimpanan Aktor, & UI Web
- Gunakan **UUID** pada route URL (`HasUuid`) — jangan memakai integer ID biasa pada endpoint publik/Camp.
- Simpan seluruh data domain di MySQL (`indolens`); hindari data hardcoded di client.
- Standar penyimpanan media aktor di `storage/app/public/actor-images/{id}-{slug}/`:
  - Foto profil: `profile-{slug}.{ext}`
  - Foto wajah: `{slug}-{02d}.{ext}`
- Sinkronkan seluruh foto wajah aktif aktor ke `python/embeddings/{actor_slug}/{image_id}.npy` (vektor `512-D` hasil model FaceNet training mandiri) dan `manifest.json`.
- Jaga tampilan responsif pada ukuran layar mobile hingga desktop (`320`, `375`, `425`, `768`, `1024+`).

## 7. Pembagian Sesi Perombakan Sistem (Roadmap Eksekusi Bertahap)
- **Sesi 1:** Pembersihan total file/bobot/artefak *pre-trained* lama, perapian struktur folder `python/` & `training_python/`, serta pembuatan struktur folder dataset kosong beserta panduan.
- **Sesi 2:** Pembangunan modul konfigurasi & arsitektur **YOLOv8 Polosan (`arsitektur_yolov8_wajah.yaml`)** + skrip persiapan dataset YOLO (`split train/val/test`, *negative background*, `data_yolo_wajah.yaml`) + modul training YOLOv8 dari Epoch 0 (Force GPU RTX 4060).
- **Sesi 3:** Pembangunan modul **Preprocessing Wajah Manual** (konversi piksel, *crop bounding box* dengan margin, augmentasi data, normalisasi tensor `160x160`) + ekstraksi crop wajah dari dataset aktor & orang random.
- **Sesi 4:** Pembangunan arsitektur **FaceNet Manual (`torch.nn.Module`)** + fungsi **Triplet Margin Loss (`Anchor`, `Positive`, `Negative`)** + loop training epoch manual di GPU RTX 4060 + ekstraksi `.npy` *reference embedding* (`512-D`).
- **Sesi 5:** Pembangunan modul **Euclidean Distance, Kalibrasi Threshold, & Evaluasi Metrik Lengkap** (*Confusion Matrix, Accuracy, Precision, Recall, F1-Score*) + penyusunan penuh Jupyter Notebook `training_python/IndoLens_Training_Pipeline.ipynb`.
- **Sesi 6:** Penyambungan kembali (*rewiring*) runtime [python/yolo_service.py](file:///c:/laragon/www/IndoLens/python/yolo_service.py), modul `python/yolo/`, `python/facenet/`, `python/recognition/`, serta integrasi Laravel (`CampController`, kamera web) ke model hasil training mandiri + pembaruan unit test + **troubleshooting 3 masalah kamera web**:
  1. Perbaikan *lag / bounding box nyantol* saat pergantian *scene/angle* agar update kotak deteksi benar-benar *real-time* mengikuti posisi aktor.
  2. Peningkatan akurasi pengenalan wajah saat aktor agak menoleh (*side-angle*) melalui integrasi *margin crop*, augmentasi pose, dan threshold terkalibrasi.
  3. Pelebaran ukuran *preview / viewfinder* kamera pada tampilan web HP (`camera.css` & Blade) agar tangkapan layar kamera lebih luas dan leluasa.
