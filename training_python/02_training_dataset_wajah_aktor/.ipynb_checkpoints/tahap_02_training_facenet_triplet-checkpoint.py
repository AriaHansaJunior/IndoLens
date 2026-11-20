"""Tahap 02 (Dataset Aktor): Pelatihan JaringanFaceNet dari Epoch 0 dengan Online Semi-Hard/Hard Triplet Loss, Cosine Margin, dan Dekorasi Dimensi di GPU RTX 4060."""

import json
import random
import sys
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Menambahkan root proyek, folder training_python, dan folder python ke sys.path untuk eksekusi Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig
from facenet.arsitektur_facenet_manual import (
    JaringanFaceNet,
    FungsiTripletMarginLoss,
)


def muat_kelas_progress_bar_training():
    """
    Memuat kelas progress bar Ultralytics TQDM agar tampilan epoch dan progres x/y (%)
    FaceNet seragam dengan tampilan pelatihan YOLOv8 serta tetap mematuhi batas IOPub Jupyter.
    """
    try:
        from ultralytics.utils import TQDM as KelasProgressBar

        konfig.aktifkan_output_notebook_unlimited()
        return KelasProgressBar
    except Exception:
        from tqdm.std import tqdm as KelasProgressBarFallback

        konfig.aktifkan_output_notebook_unlimited()
        return KelasProgressBarFallback


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


class LapisanKlasifikasiCosine(nn.Module):
    """
    Menyediakan kepala klasifikasi berbasis CosFace (additive cosine margin) khusus selama pelatihan
    agar klaster identitas antar-aktor terpisah lebar pada permukaan hypersphere 512-D.
    """

    def __init__(
        self,
        dimensi_embedding: int,
        jumlah_kelas_aktor: int,
        skala_logit: float = 16.0,
        margin_kosine: float = 0.20,
    ):
        super().__init__()
        self.skala_logit = float(skala_logit)
        self.margin_kosine = float(margin_kosine)
        self.bobot_kelas = nn.Parameter(torch.empty(jumlah_kelas_aktor, dimensi_embedding))
        nn.init.xavier_uniform_(self.bobot_kelas)

    def forward(self, vektor_embedding_l2: torch.Tensor, label_kelas: torch.Tensor) -> torch.Tensor:
        bobot_ternormalisasi = F.normalize(self.bobot_kelas, p=2, dim=1)
        kosine_mentah = F.linear(vektor_embedding_l2, bobot_ternormalisasi).clamp(-1.0 + 1e-6, 1.0 - 1e-6)
        masker_one_hot = F.one_hot(label_kelas, num_classes=self.bobot_kelas.size(0)).float()
        kosine_bermargin = kosine_mentah - (masker_one_hot * self.margin_kosine)
        return kosine_bermargin * self.skala_logit


def hitung_penalti_dekorasi_dimensi(vektor_batch: torch.Tensor) -> torch.Tensor:
    """
    Menghitung penalti kovariansi off-diagonal dan batas minimum varians per dimensi
    pada vektor embedding 512-D agar mencegah dimensional collapse (menciut menjadi 2-3 sumbu).
    """
    jumlah_sampel, dimensi_fitur = vektor_batch.shape
    if jumlah_sampel <= 2:
        return vektor_batch.new_tensor(0.0)

    vektor_terpusat = vektor_batch - vektor_batch.mean(dim=0, keepdim=True)
    matriks_kovariansi = (vektor_terpusat.T @ vektor_terpusat) / float(jumlah_sampel - 1)

    # Menekan korelasi antar-dimensi yang berbeda agar seluruh fitur biometrik tetap ortogonal
    elemen_diagonal = torch.diag(matriks_kovariansi)
    matriks_off_diagonal = matriks_kovariansi - torch.diag(elemen_diagonal)
    penalti_kovariansi = (matriks_off_diagonal.pow(2).sum()) / float(dimensi_fitur)

    # Menjaga simpangan baku tiap dimensi tidak runtuh ke nol
    std_per_dimensi = torch.sqrt(elemen_diagonal.clamp(min=1e-6))
    target_std_minimum = 1.0 / float(np.sqrt(dimensi_fitur))
    penalti_variansi = F.relu(target_std_minimum - std_per_dimensi).mean()

    return (penalti_kovariansi * 15.0) + (penalti_variansi * 2.0)


def augmentasi_tensor_wajah_realtime(tensor_batch_chw: torch.Tensor) -> torch.Tensor:
    """
    Menerapkan augmentasi ringan langsung di GPU (flip horizontal, variasi kontras/cahaya,
    derau sensor webcam, dan cutout kecil) agar embedding konsisten pada kamera laptop dan HP.
    """
    hasil_aug = tensor_batch_chw.clone()
    jumlah_batch, _, tinggi_gbr, lebar_gbr = hasil_aug.shape
    perangkat = hasil_aug.device

    # Membalik horizontal secara acak pada 50% sampel
    masker_flip = torch.rand(jumlah_batch, device=perangkat) < 0.50
    if masker_flip.any():
        hasil_aug[masker_flip] = torch.flip(hasil_aug[masker_flip], dims=[3])

    # Mengacak skala kontras dan offset kecerahan ringan untuk mensimulasikan lampu ruangan
    skala_kontras = torch.empty((jumlah_batch, 1, 1, 1), device=perangkat).uniform_(0.84, 1.16)
    geser_cahaya = torch.empty((jumlah_batch, 1, 1, 1), device=perangkat).uniform_(-0.12, 0.12)
    hasil_aug = (hasil_aug * skala_kontras) + geser_cahaya

    # Menambahkan derau Gaussian tipis untuk mensimulasikan kompresi JPEG frame kamera web
    derau_webcam = torch.randn_like(hasil_aug) * 0.04
    hasil_aug = hasil_aug + derau_webcam

    # Menutup kotak kecil secara acak pada 25% sampel untuk melatih ketahanan pantulan kacamata/pose
    for indeks_item in range(jumlah_batch):
        if torch.rand(1, device=perangkat).item() < 0.25:
            ukuran_kotak = int(torch.randint(14, 34, (1,), device=perangkat).item())
            posisi_y = int(torch.randint(0, max(1, tinggi_gbr - ukuran_kotak), (1,), device=perangkat).item())
            posisi_x = int(torch.randint(0, max(1, lebar_gbr - ukuran_kotak), (1,), device=perangkat).item())
            hasil_aug[indeks_item, :, posisi_y : posisi_y + ukuran_kotak, posisi_x : posisi_x + ukuran_kotak] = 0.0

    return hasil_aug


def tambang_triplet_online_semihard_dan_unknown(
    vektor_batch: torch.Tensor,
    label_batch: torch.Tensor,
    fungsi_loss_triplet_aktor: FungsiTripletMarginLoss,
    fungsi_loss_triplet_unknown: FungsiTripletMarginLoss,
    batas_margin_aktor: float,
) -> tuple[torch.Tensor, torch.Tensor, dict]:
    """
    Menjalankan Online Batch-Hard & Semi-Hard Triplet Mining pada satu batch PK+Random:
    - Menarik pasangan positif tersulit (Hardest Positive) dari aktor yang sama.
    - Mendorong pasangan negatif tersulit/semi-hard dari aktor lain maupun wajah orang random.
    - Menambahkan triplet khusus penolakan wajah orang random agar Unknown berada jauh dari seluruh klaster aktor.
    """
    matriks_jarak = torch.cdist(vektor_batch, vektor_batch, p=2.0)
    indeks_aktor = torch.where(label_batch >= 0)[0]
    indeks_random = torch.where(label_batch < 0)[0]

    daftar_anchor_idx: list[int] = []
    daftar_pos_idx: list[int] = []
    daftar_neg_idx: list[int] = []

    daftar_anchor_unk_idx: list[int] = []
    daftar_pos_unk_idx: list[int] = []
    daftar_neg_unk_idx: list[int] = []

    for idx_a_tensor in indeks_aktor:
        idx_a = int(idx_a_tensor.item())
        label_a = int(label_batch[idx_a].item())

        # Mencari sampel positif tersulit (jarak paling jauh) dari aktor yang sama
        masker_pos = (label_batch == label_a)
        masker_pos[idx_a] = False
        kandidat_pos = torch.where(masker_pos)[0]
        if kandidat_pos.numel() == 0:
            continue

        jarak_ke_pos = matriks_jarak[idx_a, kandidat_pos]
        pos_rel = int(torch.argmax(jarak_ke_pos).item())
        idx_p = int(kandidat_pos[pos_rel].item())
        nilai_d_pos = float(jarak_ke_pos[pos_rel].item())

        # Mencari sampel negatif semi-hard atau terkeras dari seluruh aktor lain dan orang random
        masker_neg = (label_batch != label_a)
        kandidat_neg = torch.where(masker_neg)[0]
        if kandidat_neg.numel() == 0:
            continue

        jarak_ke_neg = matriks_jarak[idx_a, kandidat_neg]
        masker_semihard = (jarak_ke_neg > nilai_d_pos) & (jarak_ke_neg < (nilai_d_pos + batas_margin_aktor))
        if masker_semihard.any():
            kandidat_sh = kandidat_neg[masker_semihard]
            jarak_sh = jarak_ke_neg[masker_semihard]
            idx_n = int(kandidat_sh[int(torch.argmin(jarak_sh).item())].item())
        else:
            idx_n = int(kandidat_neg[int(torch.argmin(jarak_ke_neg).item())].item())

        daftar_anchor_idx.append(idx_a)
        daftar_pos_idx.append(idx_p)
        daftar_neg_idx.append(idx_n)

        # Menambang negatif terdekat khusus dari wajah orang random (label == -1) untuk penolakan Unknown
        if indeks_random.numel() > 0:
            jarak_ke_random = matriks_jarak[idx_a, indeks_random]
            idx_rand_terdekat = int(indeks_random[int(torch.argmin(jarak_ke_random).item())].item())
            daftar_anchor_unk_idx.append(idx_a)
            daftar_pos_unk_idx.append(idx_p)
            daftar_neg_unk_idx.append(idx_rand_terdekat)

    if not daftar_anchor_idx:
        nol_tensor = vektor_batch.new_tensor(0.0)
        return nol_tensor, nol_tensor, {
            "rata_jarak_positif": 0.0,
            "rata_jarak_negatif": 0.0,
            "rata_jarak_random": 0.0,
            "persentase_jarak_benar": 0.0,
            "jumlah_triplet": 0,
        }

    loss_triplet_aktor, stat_aktor = fungsi_loss_triplet_aktor(
        vektor_batch[daftar_anchor_idx],
        vektor_batch[daftar_pos_idx],
        vektor_batch[daftar_neg_idx],
    )

    if daftar_anchor_unk_idx:
        loss_triplet_unknown, stat_unknown = fungsi_loss_triplet_unknown(
            vektor_batch[daftar_anchor_unk_idx],
            vektor_batch[daftar_pos_unk_idx],
            vektor_batch[daftar_neg_unk_idx],
        )
        rata_jarak_random = float(stat_unknown["rata_jarak_negatif"])
    else:
        loss_triplet_unknown = vektor_batch.new_tensor(0.0)
        rata_jarak_random = float(stat_aktor["rata_jarak_negatif"])

    statistik_gabungan = {
        "rata_jarak_positif": float(stat_aktor["rata_jarak_positif"]),
        "rata_jarak_negatif": float(stat_aktor["rata_jarak_negatif"]),
        "rata_jarak_random": rata_jarak_random,
        "persentase_jarak_benar": float(stat_aktor["persentase_jarak_benar"]),
        "jumlah_triplet": len(daftar_anchor_idx),
    }
    return loss_triplet_aktor, loss_triplet_unknown, statistik_gabungan


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

    if len(semua_random) >= 2:
        batas_rand = max(1, int(round(len(semua_random) * rasio_train)))
        if batas_rand >= len(semua_random):
            batas_rand = len(semua_random) - 1
        random_train = semua_random[:batas_rand]
        random_val = semua_random[batas_rand:]
    else:
        random_train = semua_random
        random_val = semua_random

    return peta_train_aktor, peta_val_aktor, random_train, random_val


def bentuk_satu_batch_pk_dan_random(
    peta_sampel_aktor: dict[str, list[str]],
    daftar_slug_terurut: list[str],
    daftar_random: list[str],
    jumlah_foto_per_aktor: int,
    jumlah_sampel_random: int,
    generator_acak: random.Random,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Menyusun satu batch seimbang berisi K citra wajah untuk setiap aktor terdaftar
    ditambah M citra wajah orang random (label -1) untuk Online Triplet Mining.
    """
    daftar_tensor: list[torch.Tensor] = []
    daftar_label: list[int] = []

    for id_kelas, slug_aktor in enumerate(daftar_slug_terurut):
        koleksi_aktor = peta_sampel_aktor.get(slug_aktor, [])
        if not koleksi_aktor:
            continue

        if len(koleksi_aktor) >= jumlah_foto_per_aktor:
            terpilih = generator_acak.sample(koleksi_aktor, jumlah_foto_per_aktor)
        else:
            terpilih = [generator_acak.choice(koleksi_aktor) for _ in range(jumlah_foto_per_aktor)]

        for path_npy in terpilih:
            daftar_tensor.append(muat_tensor_npy_ke_chw(path_npy))
            daftar_label.append(id_kelas)

    if daftar_random:
        jumlah_ambil_random = min(jumlah_sampel_random, len(daftar_random))
        terpilih_random = (
            generator_acak.sample(daftar_random, jumlah_ambil_random)
            if len(daftar_random) >= jumlah_ambil_random
            else [generator_acak.choice(daftar_random) for _ in range(jumlah_sampel_random)]
        )
        for path_rand in terpilih_random:
            daftar_tensor.append(muat_tensor_npy_ke_chw(path_rand))
            daftar_label.append(-1)
    elif len(daftar_slug_terurut) < 2 and daftar_tensor:
        for indeks_sintetis in range(min(4, len(daftar_tensor))):
            daftar_tensor.append(buat_sampel_negatif_sintetis(daftar_tensor[indeks_sintetis], generator_acak))
            daftar_label.append(-1)

    tensor_batch = torch.stack(daftar_tensor, dim=0)
    label_batch = torch.tensor(daftar_label, dtype=torch.long)
    return tensor_batch, label_batch


def hitung_dimensi_efektif_svd(kumpulan_vektor: list[np.ndarray]) -> dict:
    """
    Menganalisis sebaran varians ruang vektor 512-D menggunakan SVD untuk memastikan
    embedding tidak mengalami dimensional collapse.
    """
    if len(kumpulan_vektor) < 4:
        return {"dimensi_efektif_95_persen": 0, "rasio_variansi_top3": 0.0}

    matriks = np.stack(kumpulan_vektor, axis=0).astype(np.float32)
    matriks_pusat = matriks - np.mean(matriks, axis=0, keepdims=True)
    _, nilai_singular, _ = np.linalg.svd(matriks_pusat, full_matrices=False)
    total_variansi = float(np.sum(nilai_singular ** 2))
    if total_variansi <= 1e-12:
        return {"dimensi_efektif_95_persen": 0, "rasio_variansi_top3": 1.0}

    rasio_variansi = (nilai_singular ** 2) / total_variansi
    kumulatif = np.cumsum(rasio_variansi)
    dimensi_95 = int(np.searchsorted(kumulatif, 0.95) + 1)
    top3 = float(np.sum(rasio_variansi[:3]))
    return {
        "dimensi_efektif_95_persen": dimensi_95,
        "rasio_variansi_top3": round(top3, 4),
    }


def latih_model_facenet_triplet_loss(
    jumlah_epoch: int = konfig.JUMLAH_EPOCH_TRAINING_FACENET,
    batas_patience: int = konfig.BATAS_PATIENCE_EARLY_STOPPING_FACENET,
    ukuran_batch: int = konfig.UKURAN_BATCH_TRIPLET_FACENET,
    laju_belajar_awal: float = konfig.LAJU_BELAJAR_AWAL_FACENET,
    batas_margin_triplet: float = konfig.BATAS_MARGIN_TRIPLET_LOSS,
) -> dict:
    """
    Mengambil tensor wajah 160x160 dari manifest_preprocessing_wajah.json (hasil Tahap 01),
    menginisialisasi JaringanFaceNet dari bobot acak (Epoch 0), dan menjalankan pelatihan
    Online Semi-Hard/Hard Triplet Loss + CosFace Auxiliary Head + Decorrelation di GPU RTX 4060.
    Menyimpan bobot terbaik ke storage/app/ai/weights/hasil_training_facenet_aktor.pth.
    """
    # Mengaktifkan mode output Jupyter unlimited agar log epoch Triplet Loss tampil lengkap
    konfig.aktifkan_output_notebook_unlimited()
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
    daftar_slug_aktor = sorted(peta_train_aktor.keys())
    if not daftar_slug_aktor:
        raise RuntimeError("Tidak ditemukan tensor wajah aktor untuk dilatih pada manifest preprocessing.")

    jumlah_foto_per_aktor = 4
    jumlah_random_per_batch = 20 if random_train else 0
    jumlah_langkah_train_per_epoch = max(24, min(40, int(round(640 / max(1, ukuran_batch)))))
    jumlah_langkah_val_per_epoch = 10

    print("=" * 78)
    print("  TAHAP 02: PELATIHAN FACENET ONLINE HARD-TRIPLET & DEKORASI DIMENSI (RTX 4060)")
    print("=" * 78)
    print(f"[*] Perangkat Komputasi GPU     : {info_perangkat_gpu['nama_gpu']} ({info_perangkat_gpu['vram_gb']} GB VRAM)")
    print(f"[*] Indeks Perangkat            : {info_perangkat_gpu['device_pytorch']} ({info_perangkat_gpu['catatan_task_manager']})")
    print(f"[*] Jumlah Aktor & Orang Random : {len(daftar_slug_aktor)} aktor | {len(random_train) + len(random_val)} wajah orang random")
    print(f"[*] Target Epoch & Patience     : Maks {jumlah_epoch} Epoch (Early Stopping Patience = {batas_patience})")
    print(f"[*] Komposisi Batch PK + Random : {len(daftar_slug_aktor)}x{jumlah_foto_per_aktor} aktor + {jumlah_random_per_batch} random / step")
    print(f"[*] Dimensi Vektor & Margin     : {konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET}-D | Margin Aktor={batas_margin_triplet}, Unknown={round(batas_margin_triplet + 0.20, 2)}")

    jaringan_facenet = JaringanFaceNet(
        dimensi_embedding=konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
        peluang_dropout=0.25,
    ).to(objek_device_gpu)

    kepala_klasifikasi = (
        LapisanKlasifikasiCosine(
            dimensi_embedding=konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
            jumlah_kelas_aktor=len(daftar_slug_aktor),
            skala_logit=16.0,
            margin_kosine=0.20,
        ).to(objek_device_gpu)
        if len(daftar_slug_aktor) >= 2
        else None
    )

    fungsi_loss_triplet_aktor = FungsiTripletMarginLoss(batas_margin=batas_margin_triplet)
    fungsi_loss_triplet_unknown = FungsiTripletMarginLoss(batas_margin=batas_margin_triplet + 0.20)
    fungsi_loss_klasifikasi = nn.CrossEntropyLoss(label_smoothing=0.05)

    daftar_parameter_dilatih = list(jaringan_facenet.parameters())
    if kepala_klasifikasi is not None:
        daftar_parameter_dilatih += list(kepala_klasifikasi.parameters())

    optimizer_adamw = torch.optim.AdamW(
        daftar_parameter_dilatih,
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
    kelas_progress_bar = muat_kelas_progress_bar_training()
    ukuran_wajah_input = int(konfig.UKURAN_RESOLUSI_WAJAH_FACENET[0])
    info_dimensi_akhir = {"dimensi_efektif_95_persen": 0, "rasio_variansi_top3": 0.0}

    for nomor_epoch in range(1, jumlah_epoch + 1):
        generator_train = random.Random(konfig.NILAI_SEED_ACAK + (nomor_epoch * 1009))
        generator_val = random.Random(konfig.NILAI_SEED_ACAK + 77777 + (nomor_epoch * 31))

        jaringan_facenet.train()
        if kepala_klasifikasi is not None:
            kepala_klasifikasi.train()

        # Mencetak header kolom bergaya YOLOv8 sebelum progress bar batch train dijalankan
        print(
            f"\n{'Epoch':>11} {'GPU_mem':>10} {'TrainLoss':>10} "
            f"{'TrainAcc':>10} {'Triplets':>10} {'Size':>10}"
        )

        akumulasi_loss_train = 0.0
        akumulasi_benar_train = 0.0
        jumlah_batch_train = 0

        progress_train = kelas_progress_bar(
            range(jumlah_langkah_train_per_epoch),
            desc=(
                f"{f'{nomor_epoch}/{jumlah_epoch}':>11} {'0.00G':>10} "
                f"{'0.0000':>10} {'0.0%':>10} {0:>10} {ukuran_wajah_input:>10}"
            ),
            total=jumlah_langkah_train_per_epoch,
            file=sys.stdout,
        )

        for _ in progress_train:
            tensor_batch, label_batch = bentuk_satu_batch_pk_dan_random(
                peta_sampel_aktor=peta_train_aktor,
                daftar_slug_terurut=daftar_slug_aktor,
                daftar_random=random_train,
                jumlah_foto_per_aktor=jumlah_foto_per_aktor,
                jumlah_sampel_random=jumlah_random_per_batch,
                generator_acak=generator_train,
            )
            tensor_batch = augmentasi_tensor_wajah_realtime(tensor_batch.to(objek_device_gpu))
            label_batch = label_batch.to(objek_device_gpu)

            optimizer_adamw.zero_grad()
            vektor_batch = jaringan_facenet(tensor_batch)

            loss_triplet_aktor, loss_triplet_unknown, stat_batch = tambang_triplet_online_semihard_dan_unknown(
                vektor_batch=vektor_batch,
                label_batch=label_batch,
                fungsi_loss_triplet_aktor=fungsi_loss_triplet_aktor,
                fungsi_loss_triplet_unknown=fungsi_loss_triplet_unknown,
                batas_margin_aktor=batas_margin_triplet,
            )
            loss_dekorasi = hitung_penalti_dekorasi_dimensi(vektor_batch)

            loss_klasifikasi = vektor_batch.new_tensor(0.0)
            if kepala_klasifikasi is not None:
                masker_aktor_batch = label_batch >= 0
                if masker_aktor_batch.any():
                    logit_aktor = kepala_klasifikasi(
                        vektor_batch[masker_aktor_batch],
                        label_batch[masker_aktor_batch],
                    )
                    loss_klasifikasi = fungsi_loss_klasifikasi(logit_aktor, label_batch[masker_aktor_batch])

            loss_total = (
                loss_triplet_aktor
                + (0.60 * loss_triplet_unknown)
                + (0.35 * loss_klasifikasi)
                + (0.25 * loss_dekorasi)
            )
            loss_total.backward()
            torch.nn.utils.clip_grad_norm_(daftar_parameter_dilatih, max_norm=2.0)
            optimizer_adamw.step()

            akumulasi_loss_train += float(loss_total.item())
            akumulasi_benar_train += stat_batch["persentase_jarak_benar"]
            jumlah_batch_train += 1

            # Memperbarui teks progress bar batch berjalan dengan pemakaian VRAM GPU dan loss kumulatif
            memori_gpu_gb = (
                torch.cuda.memory_reserved(objek_device_gpu) / (1024 ** 3)
                if objek_device_gpu.type == "cuda"
                else 0.0
            )
            rata_loss_sementara = akumulasi_loss_train / jumlah_batch_train
            rata_acc_sementara = akumulasi_benar_train / jumlah_batch_train
            progress_train.set_description(
                f"{f'{nomor_epoch}/{jumlah_epoch}':>11} "
                f"{f'{memori_gpu_gb:.2f}G':>10} "
                f"{rata_loss_sementara:>10.4f} "
                f"{f'{rata_acc_sementara:.1f}%':>10} "
                f"{int(stat_batch['jumlah_triplet']):>10} "
                f"{ukuran_wajah_input:>10}"
            )

        penjadwal_lr.step()

        # Mengevaluasi performa pemisahan jarak positif vs negatif & random pada split validasi
        jaringan_facenet.eval()
        if kepala_klasifikasi is not None:
            kepala_klasifikasi.eval()

        akumulasi_loss_val = 0.0
        akumulasi_jarak_pos_val = 0.0
        akumulasi_jarak_neg_val = 0.0
        akumulasi_jarak_rand_val = 0.0
        akumulasi_benar_val = 0.0
        jumlah_batch_val = 0
        total_sampel_val = 0
        kumpulan_vektor_val_epoch: list[np.ndarray] = []

        progress_val = kelas_progress_bar(
            range(jumlah_langkah_val_per_epoch),
            desc=(
                f"{'':>11} {'Split':>10} {'Triplets':>10} "
                f"{'ValLoss':>10} {'Dist(+)':>10} {'Dist(-)':>10} {'ValAcc':>10}"
            ),
            total=jumlah_langkah_val_per_epoch,
            file=sys.stdout,
        )

        with torch.no_grad():
            for _ in progress_val:
                tensor_val, label_val = bentuk_satu_batch_pk_dan_random(
                    peta_sampel_aktor=peta_val_aktor,
                    daftar_slug_terurut=daftar_slug_aktor,
                    daftar_random=random_val,
                    jumlah_foto_per_aktor=jumlah_foto_per_aktor,
                    jumlah_sampel_random=min(20, len(random_val)) if random_val else 0,
                    generator_acak=generator_val,
                )
                tensor_val = tensor_val.to(objek_device_gpu)
                label_val = label_val.to(objek_device_gpu)

                vektor_val = jaringan_facenet(tensor_val)
                loss_val_aktor, loss_val_unk, stat_val = tambang_triplet_online_semihard_dan_unknown(
                    vektor_batch=vektor_val,
                    label_batch=label_val,
                    fungsi_loss_triplet_aktor=fungsi_loss_triplet_aktor,
                    fungsi_loss_triplet_unknown=fungsi_loss_triplet_unknown,
                    batas_margin_aktor=batas_margin_triplet,
                )
                loss_val_gabungan = loss_val_aktor + (0.60 * loss_val_unk)

                akumulasi_loss_val += float(loss_val_gabungan.item())
                akumulasi_jarak_pos_val += stat_val["rata_jarak_positif"]
                akumulasi_jarak_neg_val += stat_val["rata_jarak_negatif"]
                akumulasi_jarak_rand_val += stat_val["rata_jarak_random"]
                akumulasi_benar_val += stat_val["persentase_jarak_benar"]
                jumlah_batch_val += 1
                total_sampel_val += int(stat_val["jumlah_triplet"])

                if len(kumpulan_vektor_val_epoch) < 400:
                    for baris_v in vektor_val.detach().cpu().numpy():
                        kumpulan_vektor_val_epoch.append(baris_v)

        rata_loss_train = round(akumulasi_loss_train / max(1, jumlah_batch_train), 4)
        rata_benar_train = round(akumulasi_benar_train / max(1, jumlah_batch_train), 2)
        rata_loss_val = round(akumulasi_loss_val / max(1, jumlah_batch_val), 4)
        rata_jarak_pos = round(akumulasi_jarak_pos_val / max(1, jumlah_batch_val), 4)
        rata_jarak_neg = round(akumulasi_jarak_neg_val / max(1, jumlah_batch_val), 4)
        rata_jarak_rand = round(akumulasi_jarak_rand_val / max(1, jumlah_batch_val), 4)
        rata_benar_val = round(akumulasi_benar_val / max(1, jumlah_batch_val), 2)
        info_dimensi_akhir = hitung_dimensi_efektif_svd(kumpulan_vektor_val_epoch)

        data_satu_epoch = {
            "epoch": nomor_epoch,
            "train_total_loss": rata_loss_train,
            "train_triplet_accuracy_persen": rata_benar_train,
            "val_triplet_loss": rata_loss_val,
            "val_jarak_positif": rata_jarak_pos,
            "val_jarak_negatif": rata_jarak_neg,
            "val_jarak_random": rata_jarak_rand,
            "val_triplet_accuracy_persen": rata_benar_val,
            "dimensi_efektif_95_persen": info_dimensi_akhir["dimensi_efektif_95_persen"],
            "learning_rate": round(float(optimizer_adamw.param_groups[0]["lr"]), 6),
        }
        riwayat_epoch.append(data_satu_epoch)

        # Mencetak baris ringkasan metrik validasi sejajar di bawah header validasi
        print(
            f"{'':>11} {'val':>10} {total_sampel_val:>10} "
            f"{rata_loss_val:>10.4f} {rata_jarak_pos:>10.3f} "
            f"{rata_jarak_neg:>10.3f} {f'{rata_benar_val:.1f}%':>10}"
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
                    "arsitektur": "JaringanFaceNet",
                    "pretrained_digunakan": False,
                    "dimensi_embedding": konfig.DIMENSI_VEKTOR_EMBEDDING_FACENET,
                    "resolusi_input": list(konfig.UKURAN_RESOLUSI_WAJAH_FACENET),
                    "epoch_terbaik": epoch_terbaik,
                    "val_triplet_loss_terbaik": val_loss_terbaik,
                    "val_triplet_accuracy_persen": akurasi_triplet_terbaik,
                    "dimensi_efektif_95_persen": info_dimensi_akhir["dimensi_efektif_95_persen"],
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
        "arsitektur_model": "JaringanFaceNet (torch.nn.Module + Online Hard-Triplet + CosFace + Decorrelation)",
        "info_perangkat_gpu": info_perangkat_gpu,
        "path_bobot_hasil_training_facenet": str(konfig.FILE_BOBOT_HASIL_TRAINING_FACENET),
        "jumlah_epoch_dijalankan": len(riwayat_epoch),
        "epoch_terbaik": epoch_terbaik,
        "val_triplet_loss_terbaik": val_loss_terbaik,
        "val_triplet_accuracy_terbaik_persen": akurasi_triplet_terbaik,
        "kesehatan_dimensi_embedding": info_dimensi_akhir,
        "durasi_training_detik": durasi_detik,
        "riwayat_epoch": riwayat_epoch,
    }

    path_laporan_facenet = konfig.FOLDER_HASIL_TRAINING_FACENET / "ringkasan_hasil_training_facenet.json"
    path_laporan_facenet.write_text(json.dumps(data_hasil_training_facenet, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("  PELATIHAN FACENET TRIPLET LOSS SELESAI")
    print("=" * 78)
    print(f"[OK] Bobot terbaik disimpan ke : {konfig.FILE_BOBOT_HASIL_TRAINING_FACENET}")
    print(f"[OK] Epoch terbaik             : Epoch {epoch_terbaik} (Val Loss = {val_loss_terbaik}, Acc = {akurasi_triplet_terbaik}%)")
    print(f"[OK] Dimensi efektif 95% (SVD) : {info_dimensi_akhir['dimensi_efektif_95_persen']} dimensi (Top-3 var = {info_dimensi_akhir['rasio_variansi_top3'] * 100:.1f}%)")
    print(f"[OK] Durasi pelatihan          : {durasi_detik} detik")

    return data_hasil_training_facenet


if __name__ == "__main__":
    latih_model_facenet_triplet_loss()
