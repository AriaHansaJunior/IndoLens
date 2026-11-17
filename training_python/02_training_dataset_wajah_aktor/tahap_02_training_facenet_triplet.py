"""Tahap 02 (Dataset Aktor): Pelatihan JaringanFaceNetMandiri dari Epoch 0 dengan Triplet Margin Loss di GPU RTX 4060."""

import json
import random
import sys
import time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

# Menambahkan root proyek, folder training_python, dan folder python ke sys.path untuk eksekusi Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig
from facenet.arsitektur_facenet_manual import (
    JaringanFaceNetMandiri,
    FungsiTripletMarginLoss,
)


def muat_tensor_npy_ke_chw(path_file_npy: str | Path) -> torch.Tensor:
    """
    Membaca file array piksel wajah 160x160x3 ternormalisasi (.npy) dari folder crop_wajah_160x160
    dan mengubah dimensinya menjadi tensor PyTorch [3, 160, 160].
    """
    array_hwc = np.load(str(path_file_npy)).astype(np.float32)
    if array_hwc.ndim == 3 and array_hwc.shape[2] == 3:
        return torch.from_numpy(array_hwc).permute(2, 0, 1).float()
    return torch.from_numpy(array_hwc).float()


def buat_sampel_negatif_sintetis(tensor_anchor_chw: torch.Tensor, generator_acak: random.Random) -> torch.Tensor:
    """
    Membentuk tensor negatif pembanding secara matematis (rotasi 180 derajat, inversi kontras, dan pengacakan blok)
    hanya apabila di dalam folder dataset baru tersedia 1 aktor dan folder wajah_orang_random masih kosong.
    """
    tensor_neg = torch.flip(tensor_anchor_chw, dims=[1, 2]).clone()
    tensor_neg = -tensor_neg
    shift_piksel = generator_acak.randint(25, 80)
    tensor_neg = torch.roll(tensor_neg, shifts=(shift_piksel, shift_piksel), dims=(1, 2))
    return tensor_neg


class DatasetPasanganTripletWajah(Dataset):
    """
    Menyusun pasangan tiga citra wajah (Anchor, Positive, Negative) dari hasil preprocessing 160x160:
    - Anchor   : citra wajah milik Aktor A
    - Positive : citra wajah lain / pose lain milik Aktor A yang sama
    - Negative : citra wajah milik Aktor B yang berbeda atau citra dari folder wajah_orang_random
    """

    def __init__(
        self,
        peta_sampel_per_aktor: dict[str, list[str]],
        daftar_path_orang_random: list[str],
        jumlah_triplet_per_epoch: int = 256,
        seed_acak: int = 42,
    ):
        super().__init__()
        self.peta_sampel_per_aktor = {
            slug: daftar for slug, daftar in peta_sampel_per_aktor.items() if len(daftar) >= 1
        }
        self.daftar_slug_aktor = sorted(self.peta_sampel_per_aktor.keys())
        self.daftar_path_orang_random = list(daftar_path_orang_random)
        self.jumlah_triplet_per_epoch = max(16, int(jumlah_triplet_per_epoch))
        self.seed_dasar = int(seed_acak)

    def __len__(self) -> int:
        return self.jumlah_triplet_per_epoch

    def __getitem__(self, indeks_item: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        generator_acak = random.Random(self.seed_dasar + indeks_item)

        slug_anchor = generator_acak.choice(self.daftar_slug_aktor)
        koleksi_positif = self.peta_sampel_per_aktor[slug_anchor]

        if len(koleksi_positif) >= 2:
            path_anchor, path_positive = generator_acak.sample(koleksi_positif, 2)
        else:
            path_anchor = koleksi_positif[0]
            path_positive = koleksi_positif[0]

        tensor_anchor = muat_tensor_npy_ke_chw(path_anchor)
        tensor_positive = muat_tensor_npy_ke_chw(path_positive)

        # Memilih sampel Negative dari aktor lain atau dari kumpulan wajah_orang_random
        kandidat_aktor_lain = [slug for slug in self.daftar_slug_aktor if slug != slug_anchor]
        gunakan_aktor_lain = bool(kandidat_aktor_lain) and (
            not self.daftar_path_orang_random or generator_acak.random() < 0.60
        )

        if gunakan_aktor_lain:
            slug_negatif = generator_acak.choice(kandidat_aktor_lain)
            path_negative = generator_acak.choice(self.peta_sampel_per_aktor[slug_negatif])
            tensor_negative = muat_tensor_npy_ke_chw(path_negative)
        elif self.daftar_path_orang_random:
            path_negative = generator_acak.choice(self.daftar_path_orang_random)
            tensor_negative = muat_tensor_npy_ke_chw(path_negative)
        else:
            tensor_negative = buat_sampel_negatif_sintetis(tensor_anchor, generator_acak)

        return tensor_anchor, tensor_positive, tensor_negative


def pisahkan_tensor_aktor_train_dan_val(
    manifest_preprocessing: dict,
    rasio_train: float = 0.80,
    seed_acak: int = konfig.NILAI_SEED_ACAK,
) -> tuple[dict[str, list[str]], dict[str, list[str]], list[str], list[str]]:
    """
    Membagi daftar file tensor .npy 160x160 milik setiap aktor dan orang random ke dalam kelompok
    train (80%) dan val (20%) berdasarkan image_id agar tidak terjadi kebocoran data uji.
    """
    generator_acak = random.Random(seed_acak)
    peta_train_aktor: dict[str, list[str]] = {}
    peta_val_aktor: dict[str, list[str]] = {}

    data_aktor_manifest = manifest_preprocessing.get("aktor", {})
    for slug_aktor, info_aktor in sorted(data_aktor_manifest.items()):
        kelompok_per_id_gambar: dict[str, list[str]] = {}
        for item_rekaman in info_aktor.get("sampel_asli", []) + info_aktor.get("sampel_augmentasi", []):
            path_npy = item_rekaman.get("path_tensor_npy")
            if not path_npy or not Path(path_npy).exists():
                continue
            id_gambar = str(item_rekaman.get("image_id", "0"))
            kelompok_per_id_gambar.setdefault(id_gambar, []).append(path_npy)

        daftar_id_unik = sorted(kelompok_per_id_gambar.keys())
        generator_acak.shuffle(daftar_id_unik)

        if len(daftar_id_unik) <= 1:
            id_train = daftar_id_unik
            id_val = daftar_id_unik
        else:
            batas_train = max(1, int(round(len(daftar_id_unik) * rasio_train)))
            if batas_train >= len(daftar_id_unik):
                batas_train = len(daftar_id_unik) - 1
            id_train = daftar_id_unik[:batas_train]
            id_val = daftar_id_unik[batas_train:]

        peta_train_aktor[slug_aktor] = [p for id_g in id_train for p in kelompok_per_id_gambar[id_g]]
        peta_val_aktor[slug_aktor] = [p for id_g in id_val for p in kelompok_per_id_gambar[id_g]]

    semua_random = [
        item["path_tensor_npy"]
        for item in manifest_preprocessing.get("orang_random", [])
        if item.get("path_tensor_npy") and Path(item["path_tensor_npy"]).exists()
    ]
    generator_acak.shuffle(semua_random)

    if len(semua_random) <= 1:
        random_train = list(semua_random)
        random_val = list(semua_random)
    else:
        batas_rand = max(1, int(round(len(semua_random) * rasio_train)))
        if batas_rand >= len(semua_random):
            batas_rand = len(semua_random) - 1
        random_train = semua_random[:batas_rand]
        random_val = semua_random[batas_rand:]

    return peta_train_aktor, peta_val_aktor, random_train, random_val


def latih_model_facenet_triplet_loss(
    jumlah_epoch: int = konfig.JUMLAH_EPOCH_TRAINING_FACENET,
    batas_patience: int = konfig.BATAS_PATIENCE_EARLY_STOPPING_FACENET,
    ukuran_batch: int = konfig.UKURAN_BATCH_TRIPLET_FACENET,
    laju_belajar_awal: float = konfig.LAJU_BELAJAR_AWAL_FACENET,
    batas_margin_triplet: float = konfig.BATAS_MARGIN_TRIPLET_LOSS,
) -> dict:
    """
    Mengambil tensor wajah 160x160 dari manifest_preprocessing_wajah.json (hasil Tahap 01),
    menginisialisasi JaringanFaceNetMandiri dari bobot acak (Epoch 0), dan menjalankan loop pelatihan
    menggunakan fungsi Triplet Margin Loss (Anchor, Positive, Negative) di GPU NVIDIA GeForce RTX 4060.
    Menyimpan bobot terbaik ke storage/app/ai/weights/hasil_training_facenet_aktor.pth untuk dipakai pada
    Tahap 03 (ekstraksi embedding .npy) dan layanan kamera real-time python/yolo_service.py.
    """
    konfig.pastikan_semua_folder_tersedia()
    path_manifest_crop = konfig.FOLDER_CROP_WAJAH_160X160 / "manifest_preprocessing_wajah.json"
    if not path_manifest_crop.exists():
        raise FileNotFoundError(
            f"Manifest preprocessing wajah belum ditemukan di: {path_manifest_crop}\n"
            "Jalankan Tahap 01 (ekstrak_dan_preprocess_wajah_dataset) terlebih dahulu."
        )

    manifest_crop = json.loads(path_manifest_crop.read_text(encoding="utf-8"))
    _, objek_device_gpu, info_perangkat_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=True)

    peta_train_aktor, peta_val_aktor, random_train, random_val = pisahkan_tensor_aktor_train_dan_val(
        manifest_crop
    )
    if not peta_train_aktor:
        raise RuntimeError("Tidak ditemukan tensor wajah aktor untuk dilatih pada manifest preprocessing.")

    total_tensor_train = sum(len(v) for v in peta_train_aktor.values())
    jumlah_triplet_train = max(64, min(512, total_tensor_train * 4))
    jumlah_triplet_val = max(32, min(160, total_tensor_train * 2))

    dataset_train = DatasetPasanganTripletWajah(
        peta_train_aktor,
        random_train,
        jumlah_triplet_per_epoch=jumlah_triplet_train,
        seed_acak=konfig.NILAI_SEED_ACAK,
    )
    dataset_val = DatasetPasanganTripletWajah(
        peta_val_aktor,
        random_val,
        jumlah_triplet_per_epoch=jumlah_triplet_val,
        seed_acak=konfig.NILAI_SEED_ACAK + 999,
    )

    loader_train = DataLoader(dataset_train, batch_size=ukuran_batch, shuffle=True, drop_last=False)
    loader_val = DataLoader(dataset_val, batch_size=ukuran_batch, shuffle=False, drop_last=False)

    print("=" * 78)
    print("  TAHAP 02: PELATIHAN FACENET MANDIRI & TRIPLET LOSS DARI EPOCH 0 (GPU RTX 4060)")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']} ({info_perangkat_gpu['vram_gb']} GB VRAM)")
    print(f"[*] Indeks Perangkat            : {info_perangkat_gpu['device_pytorch']} ({info_perangkat_gpu['catatan_task_manager']})")
    print(f"[*] Jumlah Aktor & Orang Random : {len(peta_train_aktor)} aktor | {len(random_train) + len(random_val)} wajah orang random")
    print(f"[*] Target Epoch & Patience     : Maks {jumlah_epoch} Epoch (Early Stopping Patience = {batas_patience})")
    print(f"[*] Dimensi Vektor & Margin     : {konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET}-D | Triplet Margin = {batas_margin_triplet}")

    if len(peta_train_aktor) < 2 and len(random_train) == 0:
        print(
            "[!] Catatan Dataset: Saat ini baru terdeteksi 1 aktor dan 0 foto di wajah_orang_random. "
            "Tambahkan foto di wajah_orang_random/ atau aktor ke-2 agar pemisahan antar-identitas optimal."
        )

    jaringan_facenet = JaringanFaceNetMandiri(
        dimensi_embedding=konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
        peluang_dropout=0.20,
    ).to(objek_device_gpu)

    fungsi_loss_triplet = FungsiTripletMarginLoss(batas_margin=batas_margin_triplet)
    optimizer_adamw = torch.optim.AdamW(
        jaringan_facenet.parameters(),
        lr=laju_belajar_awal,
        weight_decay=konfig.WEIGHT_DECAY_FACENET,
    )
    penjadwal_lr = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer_adamw,
        T_max=max(1, jumlah_epoch),
        eta_min=laju_belajar_awal * 0.05,
    )

    waktu_mulai = time.time()
    riwayat_epoch = []
    val_loss_terbaik = float("inf")
    akurasi_triplet_terbaik = -1.0
    epoch_terbaik = 0
    hitung_tanpa_perbaikan = 0

    for nomor_epoch in range(1, jumlah_epoch + 1):
        dataset_train.seed_dasar = konfig.NILAI_SEED_ACAK + (nomor_epoch * 1000)
        jaringan_facenet.train()

        akumulasi_loss_train = 0.0
        akumulasi_benar_train = 0.0
        jumlah_batch_train = 0

        for tensor_a, tensor_p, tensor_n in loader_train:
            tensor_a = tensor_a.to(objek_device_gpu)
            tensor_p = tensor_p.to(objek_device_gpu)
            tensor_n = tensor_n.to(objek_device_gpu)

            optimizer_adamw.zero_grad()

            vektor_a = jaringan_facenet(tensor_a)
            vektor_p = jaringan_facenet(tensor_p)
            vektor_n = jaringan_facenet(tensor_n)

            nilai_loss, stat_batch = fungsi_loss_triplet(vektor_a, vektor_p, vektor_n)
            nilai_loss.backward()
            torch.nn.utils.clip_grad_norm_(jaringan_facenet.parameters(), max_norm=2.0)
            optimizer_adamw.step()

            akumulasi_loss_train += float(nilai_loss.item())
            akumulasi_benar_train += stat_batch["persentase_jarak_benar"]
            jumlah_batch_train += 1

        penjadwal_lr.step()

        # Mengevaluasi performa pemisahan jarak positif vs negatif pada split validasi
        jaringan_facenet.eval()
        akumulasi_loss_val = 0.0
        akumulasi_jarak_pos_val = 0.0
        akumulasi_jarak_neg_val = 0.0
        akumulasi_benar_val = 0.0
        jumlah_batch_val = 0

        with torch.no_grad():
            for tensor_a_val, tensor_p_val, tensor_n_val in loader_val:
                tensor_a_val = tensor_a_val.to(objek_device_gpu)
                tensor_p_val = tensor_p_val.to(objek_device_gpu)
                tensor_n_val = tensor_n_val.to(objek_device_gpu)

                vektor_a_val = jaringan_facenet(tensor_a_val)
                vektor_p_val = jaringan_facenet(tensor_p_val)
                vektor_n_val = jaringan_facenet(tensor_n_val)

                loss_val, stat_val = fungsi_loss_triplet(vektor_a_val, vektor_p_val, vektor_n_val)
                akumulasi_loss_val += float(loss_val.item())
                akumulasi_jarak_pos_val += stat_val["rata_jarak_positif"]
                akumulasi_jarak_neg_val += stat_val["rata_jarak_negatif"]
                akumulasi_benar_val += stat_val["persentase_jarak_benar"]
                jumlah_batch_val += 1

        rata_loss_train = round(akumulasi_loss_train / max(1, jumlah_batch_train), 4)
        rata_benar_train = round(akumulasi_benar_train / max(1, jumlah_batch_train), 2)
        rata_loss_val = round(akumulasi_loss_val / max(1, jumlah_batch_val), 4)
        rata_jarak_pos = round(akumulasi_jarak_pos_val / max(1, jumlah_batch_val), 4)
        rata_jarak_neg = round(akumulasi_jarak_neg_val / max(1, jumlah_batch_val), 4)
        rata_benar_val = round(akumulasi_benar_val / max(1, jumlah_batch_val), 2)

        data_satu_epoch = {
            "epoch": nomor_epoch,
            "train_triplet_loss": rata_loss_train,
            "train_triplet_accuracy_persen": rata_benar_train,
            "val_triplet_loss": rata_loss_val,
            "val_jarak_positif": rata_jarak_pos,
            "val_jarak_negatif": rata_jarak_neg,
            "val_triplet_accuracy_persen": rata_benar_val,
            "learning_rate": round(float(optimizer_adamw.param_groups[0]["lr"]), 6),
        }
        riwayat_epoch.append(data_satu_epoch)

        print(
            f"Epoch [{nomor_epoch:03d}/{jumlah_epoch:03d}] "
            f"Train Loss: {rata_loss_train:.4f} ({rata_benar_train:.1f}%) | "
            f"Val Loss: {rata_loss_val:.4f} | "
            f"Dist(+): {rata_jarak_pos:.3f} vs Dist(-): {rata_jarak_neg:.3f} | "
            f"Val Triplet Acc: {rata_benar_val:.1f}%"
        )

        # Menyimpan checkpoint terbaik apabila val_loss menurun atau akurasi triplet validasi meningkat
        membaik = (rata_loss_val < val_loss_terbaik - 1e-4) or (
            abs(rata_loss_val - val_loss_terbaik) <= 1e-4 and rata_benar_val > akurasi_triplet_terbaik
        )
        if membaik:
            val_loss_terbaik = rata_loss_val
            akurasi_triplet_terbaik = rata_benar_val
            epoch_terbaik = nomor_epoch
            hitung_tanpa_perbaikan = 0

            konfig.FILE_BOBOT_HASIL_TRAINING_FACENET.parent.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "arsitektur": "JaringanFaceNetMandiri",
                    "pretrained_digunakan": False,
                    "dimensi_embedding": konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
                    "resolusi_input": list(konfig.UKURAN_RESOLUSI_WAJAH_FACENET),
                    "epoch_terbaik": epoch_terbaik,
                    "val_triplet_loss_terbaik": val_loss_terbaik,
                    "val_triplet_accuracy_persen": akurasi_triplet_terbaik,
                    "state_dict_model": jaringan_facenet.state_dict(),
                },
                str(konfig.FILE_BOBOT_HASIL_TRAINING_FACENET),
            )
        else:
            hitung_tanpa_perbaikan += 1
            if hitung_tanpa_perbaikan >= batas_patience:
                print(
                    f"\n[Early Stopping] Val loss sudah stabil selama {batas_patience} epoch berturut-turut. "
                    f"Pelatihan dihentikan pada Epoch {nomor_epoch} (Epoch terbaik: {epoch_terbaik})."
                )
                break

    durasi_detik = round(time.time() - waktu_mulai, 2)
    data_hasil_training_facenet = {
        "status_training": "berhasil",
        "pretrained_digunakan": False,
        "arsitektur_model": "JaringanFaceNetMandiri (torch.nn.Module + Triplet Margin Loss)",
        "info_perangkat_gpu": info_perangkat_gpu,
        "path_bobot_hasil_training_facenet": str(konfig.FILE_BOBOT_HASIL_TRAINING_FACENET),
        "jumlah_epoch_dijalankan": len(riwayat_epoch),
        "epoch_terbaik": epoch_terbaik,
        "val_triplet_loss_terbaik": val_loss_terbaik,
        "val_triplet_accuracy_terbaik_persen": akurasi_triplet_terbaik,
        "durasi_training_detik": durasi_detik,
        "riwayat_epoch": riwayat_epoch,
    }

    path_laporan_facenet = konfig.FOLDER_HASIL_TRAINING_FACENET / "ringkasan_hasil_training_facenet.json"
    path_laporan_facenet.write_text(json.dumps(data_hasil_training_facenet, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("  PELATIHAN MANDIRI FACENET TRIPLET LOSS SELESAI")
    print("=" * 78)
    print(f"[OK] Bobot terbaik disimpan ke : {konfig.FILE_BOBOT_HASIL_TRAINING_FACENET}")
    print(f"[OK] Epoch terbaik             : Epoch {epoch_terbaik} (Val Loss = {val_loss_terbaik}, Acc = {akurasi_triplet_terbaik}%)")
    print(f"[OK] Durasi pelatihan          : {durasi_detik} detik")

    return data_hasil_training_facenet


if __name__ == "__main__":
    latih_model_facenet_triplet_loss()
