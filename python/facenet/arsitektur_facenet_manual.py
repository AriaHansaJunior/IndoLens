"""Arsitektur Jaringan Saraf FaceNet Mandiri (torch.nn.Module) dan Fungsi Triplet Margin Loss dari nol."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BlokKonvolusiDasar(nn.Module):
    """
    Menjalankan operasi konvolusi 2 dimensi yang diikuti Batch Normalization dan fungsi aktivasi ReLU
    untuk mengekstrak fitur tepi, tekstur, dan pola lokal dari matriks piksel wajah.
    """

    def __init__(
        self,
        jumlah_kanal_masuk: int,
        jumlah_kanal_keluar: int,
        ukuran_kernel: int,
        langkah_stride: int = 1,
        ukuran_padding: int = 0,
    ):
        super().__init__()
        self.lapisan_konvolusi = nn.Conv2d(
            jumlah_kanal_masuk,
            jumlah_kanal_keluar,
            kernel_size=ukuran_kernel,
            stride=langkah_stride,
            padding=ukuran_padding,
            bias=False,
        )
        self.normalisasi_batch = nn.BatchNorm2d(jumlah_kanal_keluar, eps=0.001, momentum=0.1)
        self.aktivasi_relu = nn.ReLU(inplace=True)

    def forward(self, tensor_masukan: torch.Tensor) -> torch.Tensor:
        keluaran = self.lapisan_konvolusi(tensor_masukan)
        keluaran = self.normalisasi_batch(keluaran)
        return self.aktivasi_relu(keluaran)


class BlokInceptionResidual(nn.Module):
    """
    Menggabungkan 3 cabang konvolusi multi-skala secara paralel (Cabang 1x1, Cabang 1x1->3x3, dan Cabang 1x1->3x3->3x3)
    dengan jalur pintas residual (skip connection) agar jaringan mampu menangkap fitur wajah lokal maupun global
    tanpa mengalami peluruhan gradien (vanishing gradient) saat dilatih dari Epoch 0 di GPU RTX 4060.
    """

    def __init__(self, jumlah_kanal: int, kanal_cabang_dalam: int, skala_residual: float = 0.30):
        super().__init__()
        self.skala_residual = float(skala_residual)

        # Cabang 1: konvolusi 1x1 untuk menangkap korelasi antar-kanal pada satu titik piksel
        self.cabang_1x1 = BlokKonvolusiDasar(
            jumlah_kanal, kanal_cabang_dalam, ukuran_kernel=1, langkah_stride=1, ukuran_padding=0
        )

        # Cabang 2: konvolusi 1x1 diikuti 3x3 untuk menangkap proporsi fitur wajah lokal (mata/alis/bibir)
        self.cabang_3x3 = nn.Sequential(
            BlokKonvolusiDasar(
                jumlah_kanal, kanal_cabang_dalam, ukuran_kernel=1, langkah_stride=1, ukuran_padding=0
            ),
            BlokKonvolusiDasar(
                kanal_cabang_dalam, kanal_cabang_dalam, ukuran_kernel=3, langkah_stride=1, ukuran_padding=1
            ),
        )

        # Cabang 3: konvolusi 1x1 diikuti dua lapis 3x3 (setara bidang pandang 5x5) untuk struktur kontur wajah
        self.cabang_5x5_efektif = nn.Sequential(
            BlokKonvolusiDasar(
                jumlah_kanal, kanal_cabang_dalam, ukuran_kernel=1, langkah_stride=1, ukuran_padding=0
            ),
            BlokKonvolusiDasar(
                kanal_cabang_dalam, kanal_cabang_dalam, ukuran_kernel=3, langkah_stride=1, ukuran_padding=1
            ),
            BlokKonvolusiDasar(
                kanal_cabang_dalam, kanal_cabang_dalam, ukuran_kernel=3, langkah_stride=1, ukuran_padding=1
            ),
        )

        # Menggabungkan keluaran ketiga cabang kembali ke dimensi kanal semula sebelum dijumlahkan dengan jalur residual
        self.proyeksi_penggabung = nn.Sequential(
            nn.Conv2d(kanal_cabang_dalam * 3, jumlah_kanal, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(jumlah_kanal, eps=0.001, momentum=0.1),
        )
        self.aktivasi_akhir = nn.ReLU(inplace=True)

    def forward(self, tensor_masukan: torch.Tensor) -> torch.Tensor:
        hasil_cabang_1 = self.cabang_1x1(tensor_masukan)
        hasil_cabang_2 = self.cabang_3x3(tensor_masukan)
        hasil_cabang_3 = self.cabang_5x5_efektif(tensor_masukan)

        gabungan_cabang = torch.cat([hasil_cabang_1, hasil_cabang_2, hasil_cabang_3], dim=1)
        proyeksi_fitur = self.proyeksi_penggabung(gabungan_cabang)

        keluaran_residual = tensor_masukan + (proyeksi_fitur * self.skala_residual)
        return self.aktivasi_akhir(keluaran_residual)


class BlokReduksiSpasial(nn.Module):
    """
    Menyusutkan ukuran resolusi spasial peta fitur menjadi setengahnya (stride=2) sambil memperlebar jumlah kanal
    melalui penggabungan cabang konvolusi stride-2 dan cabang MaxPooling.
    """

    def __init__(self, jumlah_kanal_masuk: int, jumlah_kanal_keluar: int):
        super().__init__()
        kanal_separuh = jumlah_kanal_keluar // 2
        kanal_sisa = jumlah_kanal_keluar - kanal_separuh

        self.cabang_konvolusi_stride2 = BlokKonvolusiDasar(
            jumlah_kanal_masuk,
            kanal_separuh,
            ukuran_kernel=3,
            langkah_stride=2,
            ukuran_padding=1,
        )
        self.cabang_pool_dan_proyeksi = nn.Sequential(
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            BlokKonvolusiDasar(
                jumlah_kanal_masuk,
                kanal_sisa,
                ukuran_kernel=1,
                langkah_stride=1,
                ukuran_padding=0,
            ),
        )

    def forward(self, tensor_masukan: torch.Tensor) -> torch.Tensor:
        bagian_konvolusi = self.cabang_konvolusi_stride2(tensor_masukan)
        bagian_pooling = self.cabang_pool_dan_proyeksi(tensor_masukan)
        return torch.cat([bagian_konvolusi, bagian_pooling], dim=1)


class JaringanFaceNetMandiri(nn.Module):
    """
    Membangun arsitektur jaringan saraf FaceNet mandiri dari nol menggunakan PyTorch (tanpa bobot pre-trained)
    untuk memetakan citra wajah RGB berukuran 160x160 piksel menjadi vektor embedding 512-D ternormalisasi L2.

    Alur reduksi resolusi spasial dari input 160x160 piksel:
    - Tahap Reduksi 1 (Stem Stride 2)    : 160x160 -> 80x80   (64 kanal)
    - Tahap Reduksi 2 (Reduksi Spasial A): 80x80   -> 40x40   (128 kanal + 2 Blok Inception-Residual)
    - Tahap Reduksi 3 (Reduksi Spasial B): 40x40   -> 20x20   (256 kanal + 3 Blok Inception-Residual)
    - Tahap Reduksi 4 (Reduksi Spasial C): 20x20   -> 10x10   (384 kanal + 3 Blok Inception-Residual)
    - Tahap Reduksi 5 (Reduksi Spasial D): 10x10   -> 5x5     (512 kanal + 2 Blok Inception-Residual)
    - Global Average Pooling & Proyeksi  : 5x5     -> 1x1     -> Vektor 512-D -> L2 Normalization (||v||_2 = 1.0)
    """

    def __init__(
        self,
        dimensi_embedding: int = 512,
        peluang_dropout: float = 0.20,
    ):
        super().__init__()
        self.dimensi_embedding = int(dimensi_embedding)

        # Tahap 1: Stem konvolusi awal (mereduksi 160x160 menjadi 80x80 dengan 64 kanal fitur)
        self.tahap_1_stem_awal = nn.Sequential(
            BlokKonvolusiDasar(3, 32, ukuran_kernel=3, langkah_stride=2, ukuran_padding=1),
            BlokKonvolusiDasar(32, 64, ukuran_kernel=3, langkah_stride=1, ukuran_padding=1),
        )

        # Tahap 2: Reduksi spasial ke 40x40 (128 kanal) diikuti 2 blok Inception-Residual
        self.tahap_2_fitur_40x40 = nn.Sequential(
            BlokReduksiSpasial(64, 128),
            BlokInceptionResidual(128, kanal_cabang_dalam=32, skala_residual=0.30),
            BlokInceptionResidual(128, kanal_cabang_dalam=32, skala_residual=0.30),
        )

        # Tahap 3: Reduksi spasial ke 20x20 (256 kanal) diikuti 3 blok Inception-Residual
        self.tahap_3_fitur_20x20 = nn.Sequential(
            BlokReduksiSpasial(128, 256),
            BlokInceptionResidual(256, kanal_cabang_dalam=48, skala_residual=0.25),
            BlokInceptionResidual(256, kanal_cabang_dalam=48, skala_residual=0.25),
            BlokInceptionResidual(256, kanal_cabang_dalam=48, skala_residual=0.25),
        )

        # Tahap 4: Reduksi spasial ke 10x10 (384 kanal) diikuti 3 blok Inception-Residual
        self.tahap_4_fitur_10x10 = nn.Sequential(
            BlokReduksiSpasial(256, 384),
            BlokInceptionResidual(384, kanal_cabang_dalam=64, skala_residual=0.20),
            BlokInceptionResidual(384, kanal_cabang_dalam=64, skala_residual=0.20),
            BlokInceptionResidual(384, kanal_cabang_dalam=64, skala_residual=0.20),
        )

        # Tahap 5: Reduksi spasial ke 5x5 (512 kanal) diikuti 2 blok Inception-Residual
        self.tahap_5_fitur_5x5 = nn.Sequential(
            BlokReduksiSpasial(384, 512),
            BlokInceptionResidual(512, kanal_cabang_dalam=96, skala_residual=0.20),
            BlokInceptionResidual(512, kanal_cabang_dalam=96, skala_residual=0.20),
        )

        # Merangkum peta fitur 5x5 menjadi vektor 512-D dan menstabilkannya dengan BatchNorm1d
        self.perata_rata_global = nn.AdaptiveAvgPool2d((1, 1))
        self.lapisan_dropout = nn.Dropout(p=peluang_dropout)
        self.lapisan_linear_embedding = nn.Linear(512, self.dimensi_embedding, bias=False)
        self.normalisasi_batch_embedding = nn.BatchNorm1d(self.dimensi_embedding, eps=0.001, momentum=0.1)

        self.inisialisasi_bobot_kaiming()

    def inisialisasi_bobot_kaiming(self):
        """
        Menginisialisasi seluruh bobot konvolusi dan linear secara acak terukur menggunakan distribusi Kaiming He
        agar pelatihan dari Epoch 0 memiliki varians gradien yang stabil sejak iterasi pertama.
        """
        for modul in self.modules():
            if isinstance(modul, nn.Conv2d):
                nn.init.kaiming_normal_(modul.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(modul, (nn.BatchNorm2d, nn.BatchNorm1d)):
                nn.init.ones_(modul.weight)
                nn.init.zeros_(modul.bias)
            elif isinstance(modul, nn.Linear):
                nn.init.normal_(modul.weight, mean=0.0, std=0.01)

    def forward(self, tensor_wajah_chw: torch.Tensor) -> torch.Tensor:
        """
        Memproses tensor citra wajah [Batch, 3, 160, 160] melewati 5 tahap konvolusi dan menghasilkan
        vektor embedding [Batch, 512] yang telah dinormalisasi L2 (panjang vektor = 1.0).
        """
        peta_fitur = self.tahap_1_stem_awal(tensor_wajah_chw)
        peta_fitur = self.tahap_2_fitur_40x40(peta_fitur)
        peta_fitur = self.tahap_3_fitur_20x20(peta_fitur)
        peta_fitur = self.tahap_4_fitur_10x10(peta_fitur)
        peta_fitur = self.tahap_5_fitur_5x5(peta_fitur)

        vektor_rata_global = self.perata_rata_global(peta_fitur)
        vektor_datar = torch.flatten(vektor_rata_global, 1)
        vektor_datar = self.lapisan_dropout(vektor_datar)

        vektor_mentah = self.lapisan_linear_embedding(vektor_datar)
        if vektor_mentah.shape[0] > 1 or not self.training:
            vektor_mentah = self.normalisasi_batch_embedding(vektor_mentah)

        # Menormalisasi vektor dengan rumus L2 (v / ||v||_2) agar berada pada permukaan hypersphere satuan
        vektor_embedding_l2 = F.normalize(vektor_mentah, p=2, dim=1)
        return vektor_embedding_l2


def hitung_triplet_margin_loss(
    vektor_anchor: torch.Tensor,
    vektor_positive: torch.Tensor,
    vektor_negative: torch.Tensor,
    batas_margin: float = 0.50,
) -> tuple[torch.Tensor, dict]:
    """
    Menghitung nilai Triplet Margin Loss secara manual berdasarkan rumus:
    Loss = rata_rata( max(0, ||Anchor - Positive||_2 - ||Anchor - Negative||_2 + batas_margin) )
    Tujuan fungsi ini adalah menarik vektor wajah aktor yang sama (Anchor & Positive) agar berdekatan
    dan mendorong vektor wajah orang berbeda (Anchor & Negative) agar menjauh minimal sebesar batas_margin.
    """
    jarak_anchor_ke_positive = torch.norm(vektor_anchor - vektor_positive, p=2, dim=1)
    jarak_anchor_ke_negative = torch.norm(vektor_anchor - vektor_negative, p=2, dim=1)

    selisih_jarak_bermargin = jarak_anchor_ke_positive - jarak_anchor_ke_negative + float(batas_margin)
    loss_per_sampel = F.relu(selisih_jarak_bermargin)
    nilai_loss_rata_rata = torch.mean(loss_per_sampel)

    with torch.no_grad():
        jumlah_triplet_benar = torch.sum(jarak_anchor_ke_positive < jarak_anchor_ke_negative).item()
        jumlah_triplet_aktif = torch.sum(loss_per_sampel > 1e-6).item()
        total_batch = max(1, int(vektor_anchor.shape[0]))

        statistik_batch_triplet = {
            "rata_jarak_positif": float(torch.mean(jarak_anchor_ke_positive).item()),
            "rata_jarak_negatif": float(torch.mean(jarak_anchor_ke_negative).item()),
            "persentase_jarak_benar": round((jumlah_triplet_benar / total_batch) * 100.0, 2),
            "persentase_triplet_aktif": round((jumlah_triplet_aktif / total_batch) * 100.0, 2),
        }

    return nilai_loss_rata_rata, statistik_batch_triplet


class FungsiTripletMarginLoss(nn.Module):
    """
    Membungkus fungsi hitung_triplet_margin_loss ke dalam modul PyTorch nn.Module
    untuk digunakan pada loop pelatihan epoch di training_python/02_training_dataset_wajah_aktor.
    """

    def __init__(self, batas_margin: float = 0.50):
        super().__init__()
        self.batas_margin = float(batas_margin)

    def forward(
        self,
        vektor_anchor: torch.Tensor,
        vektor_positive: torch.Tensor,
        vektor_negative: torch.Tensor,
    ) -> tuple[torch.Tensor, dict]:
        return hitung_triplet_margin_loss(
            vektor_anchor=vektor_anchor,
            vektor_positive=vektor_positive,
            vektor_negative=vektor_negative,
            batas_margin=self.batas_margin,
        )
