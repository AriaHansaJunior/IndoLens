# IndoLens Project Guidelines

Aturan kerja untuk seluruh perubahan kode di repositori IndoLens agar konsisten di setiap sesi.

## 1. File Sementara & Kebersihan Workspace
- File sementara (`scratch/`, skrip ad-hoc, foto/video dummy, output uji di `python/temp/`) boleh dibuat selama proses pengujian atau verifikasi, tetapi **wajib dihapus sebelum mengakhiri sesi** begitu pengujian berhasil.
- Test otomatis permanen ditempatkan di `tests/` (PHPUnit) dan `python/tests/` (unittest) serta wajib membersihkan file sementara masing-masing (`tearDown` / `Storage::fake`).

## 2. Gaya Kode, Scope Skripsi, & Komentar
- Gunakan logika, pola, dan sintaks standar yang jelas serta sesuai scope penelitian skripsi (Laravel Eloquent, FormRequest, Blade, Vanilla JS, Python modular); hindari abstraksi berlebihan.
- **Hindari AI slop pada komentar:** tulis komentar secukupnya hanya pada blok logika atau integrasi penting (misal `# Python - YOLO`, `# Preprocessing`, `// Euclidean matching`), tanpa komentar panjang bertele-tele atau label histori sesi.
- Hindari duplikasi kode dan jaga ukuran file tetap ringkas (pecah file bila melebihi ~2000 baris).

## 3. Keamanan URL, Database, & Penyimpanan Aktor
- Gunakan **UUID** pada route URL (`HasUuid`) — jangan memakai integer ID biasa pada endpoint publik/Camp.
- Simpan seluruh data domain di MySQL (`indolens`); hindari data hardcoded atau state sementara di client saja.
- Standar penyimpanan media aktor di `storage/app/public/actor-images/{id}-{slug}/`:
  - Foto profil: `profile-{slug}.{ext}` (saat update boleh memakai suffix unik untuk cache-busting sambil menghapus file profil lama).
  - Foto wajah: `{slug}-{02d}.{ext}` dengan penomoran berurutan unik lintas semua ekstensi gambar (`jpg`, `jpeg`, `png`, `webp`, `avif`).
- Sinkronkan seluruh foto wajah aktif aktor ke `python/embeddings/{actor_slug}/{image_id}.npy` (vektor `512-D`, threshold `0.85`) dan `manifest.json`.

## 4. Antarmuka & Navigasi UI
- Jaga tampilan responsif pada ukuran layar mobile hingga desktop (`320`, `375`, `425`, `768`, `1024+`).
- Halaman Camp edit, faces, dan roles menggunakan layout vertikal full-width tanpa tombol back/subnav tambahan (kembali ke daftar Camp menggunakan tombol Back browser).
