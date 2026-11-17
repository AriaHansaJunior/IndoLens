"""Unit test otomatis untuk memverifikasi seluruh arsitektur mandiri (Zero Pre-Trained) IndoLens."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import torch

FOLDER_TESTS = Path(__file__).resolve().parent
FOLDER_PYTHON = FOLDER_TESTS.parent
FOLDER_ROOT = FOLDER_PYTHON.parent
FOLDER_TRAINING = FOLDER_ROOT / "training_python"

for path_item in [FOLDER_ROOT, FOLDER_PYTHON, FOLDER_TRAINING]:
    if str(path_item) not in sys.path:
        sys.path.insert(0, str(path_item))

import konfigurasi_training as konfig
from training_python import muat_arsitektur_yolov8_polos
from yolo.face_cropper import potong_kotak_wajah_dengan_margin, validasi_potongan_wajah
from utils.image_preprocessor import (
    ubah_ukuran_piksel_wajah,
    normalisasi_piksel_standar,
    buat_augmentasi_citra_wajah,
    proses_lengkap_citra_wajah_ke_tensor,
)
from facenet.arsitektur_facenet_manual import (
    JaringanFaceNetMandiri,
    FungsiTripletMarginLoss,
)
from facenet.embedding_generator import (
    ekstrak_vektor_embedding_wajah,
    simpan_vektor_embedding_ke_npy,
)
from recognition.euclidean_distance import hitung_jarak_euclidean
from recognition.embedding_matcher import (
    muat_semua_database_embedding_aktor,
    cari_kecocokan_aktor_terdekat,
)
from evaluation.confusion_matrix import bangun_matriks_konfusi
from evaluation.metrics import hitung_seluruh_metrik_evaluasi


class UjiArsitekturDanPipelineMandiri(unittest.TestCase):
    """Menguji arsitektur YOLOv8 polosan, preprocessing 160x160, FaceNet mandiri, Triplet Loss, dan evaluasi F1."""

    def setUp(self):
        self.folder_sementara = Path(tempfile.mkdtemp(prefix="indolens_uji_"))

    def tearDown(self):
        if self.folder_sementara.exists():
            shutil.rmtree(self.folder_sementara, ignore_errors=True)

    def test_01_penguncian_gpu_rtx_dan_arsitektur_yolov8_polos(self):
        """Memastikan arsitektur_yolov8_wajah.yaml memiliki 1 kelas (face) dan menolak file .pt pre-trained."""
        indeks_cuda, objek_device, info_gpu = konfig.pilih_perangkat_gpu_rtx_wajib(wajib_cuda=False)
        self.assertIn("nama_gpu", info_gpu)

        model_yolo = muat_arsitektur_yolov8_polos(konfig.FILE_ARSITEKTUR_YOLOV8_YAML)
        self.assertEqual(model_yolo.model.yaml["nc"], 1)
        self.assertEqual(model_yolo.model.model[-1].nc, 1)

        with self.assertRaises(ValueError):
            muat_arsitektur_yolov8_polos(Path("yolov8n.pt"))

    def test_02_potong_wajah_margin_dan_preprocessing_160x160(self):
        """Memastikan pemotongan margin 12%, penyekalaan 160x160, normalisasi piksel, dan 6 variasi augmentasi."""
        frame_dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        potongan_wajah = potong_kotak_wajah_dengan_margin(frame_dummy, [200, 100, 300, 200], rasio_margin=0.12)

        self.assertTrue(validasi_potongan_wajah(potongan_wajah))
        self.assertEqual(potongan_wajah.shape, (124, 124, 3))

        wajah_160 = ubah_ukuran_piksel_wajah(potongan_wajah)
        self.assertEqual(wajah_160.shape, (160, 160, 3))

        wajah_norm = normalisasi_piksel_standar(wajah_160)
        self.assertEqual(wajah_norm.dtype, np.float32)
        self.assertAlmostEqual(float(np.mean(wajah_norm)), 0.0, places=3)

        variasi_aug = buat_augmentasi_citra_wajah(wajah_160)
        self.assertEqual(len(variasi_aug), 6)

        tensor_chw = proses_lengkap_citra_wajah_ke_tensor(wajah_160)
        self.assertEqual(tuple(tensor_chw.shape), (1, 3, 160, 160))

    def test_03_jaringan_facenet_mandiri_dan_triplet_loss(self):
        """Memastikan JaringanFaceNetMandiri menghasilkan vektor 512-D L2-normalized dan Triplet Loss dapat di-backward."""
        jaringan = JaringanFaceNetMandiri(dimensi_embedding=512)
        tensor_a = torch.randn(4, 3, 160, 160)
        tensor_p = torch.randn(4, 3, 160, 160)
        tensor_n = torch.randn(4, 3, 160, 160)

        vektor_a = jaringan(tensor_a)
        vektor_p = jaringan(tensor_p)
        vektor_n = jaringan(tensor_n)

        self.assertEqual(tuple(vektor_a.shape), (4, 512))
        norma_l2 = torch.norm(vektor_a, p=2, dim=1).detach().numpy()
        for nilai_norm in norma_l2:
            self.assertAlmostEqual(float(nilai_norm), 1.0, places=4)

        fungsi_loss = FungsiTripletMarginLoss(batas_margin=0.50)
        nilai_loss, statistik = fungsi_loss(vektor_a, vektor_p, vektor_n)
        nilai_loss.backward()

        self.assertGreaterEqual(float(nilai_loss.item()), 0.0)
        self.assertIn("persentase_jarak_benar", statistik)

        citra_uji = np.random.randint(0, 255, (160, 160, 3), dtype=np.uint8)
        jaringan.eval()
        vektor_tunggal = ekstrak_vektor_embedding_wajah(citra_uji, model_facenet_aktif=jaringan)
        self.assertEqual(vektor_tunggal.shape, (512,))
        self.assertAlmostEqual(float(np.linalg.norm(vektor_tunggal)), 1.0, places=4)

    def test_04_pencocokan_euclidean_dan_evaluasi_matrix_f1(self):
        """Memastikan perhitungan jarak Euclidean, pencocokan threshold, Confusion Matrix, dan F1-Score akurat."""
        vektor_bayu = np.ones(512, dtype=np.float32)
        vektor_bayu /= np.linalg.norm(vektor_bayu)

        vektor_asing = -vektor_bayu
        jarak_sama = hitung_jarak_euclidean(vektor_bayu, vektor_bayu)
        jarak_beda = hitung_jarak_euclidean(vektor_bayu, vektor_asing)

        self.assertAlmostEqual(jarak_sama, 0.0, places=5)
        self.assertAlmostEqual(jarak_beda, 2.0, places=4)

        path_npy = self.folder_sementara / "bayu_eko_moektito" / "1.npy"
        simpan_vektor_embedding_ke_npy(vektor_bayu, path_npy)

        kamus_db = muat_semua_database_embedding_aktor(self.folder_sementara)
        hasil_known = cari_kecocokan_aktor_terdekat(vektor_bayu, kamus_db, batas_ambang_jarak=0.85)
        hasil_unknown = cari_kecocokan_aktor_terdekat(vektor_asing, kamus_db, batas_ambang_jarak=0.85)

        self.assertEqual(hasil_known["status"], "known")
        self.assertEqual(hasil_known["actor"], "Bayu Eko Moektito")
        self.assertEqual(hasil_unknown["status"], "unknown")

        label_asli = ["Bayu Eko Moektito", "Bayu Eko Moektito", "Tidak Dikenali", "Tidak Dikenali"]
        label_pred = ["Bayu Eko Moektito", "Tidak Dikenali", "Tidak Dikenali", "Tidak Dikenali"]

        matriks_cm, daftar_label = bangun_matriks_konfusi(label_asli, label_pred)
        metrik = hitung_seluruh_metrik_evaluasi(label_asli, label_pred, label_unknown="Tidak Dikenali")

        self.assertEqual(matriks_cm.shape, (2, 2))
        self.assertEqual(metrik["true_positives"], 1)
        self.assertEqual(metrik["true_negatives"], 2)
        self.assertEqual(metrik["false_positives"], 0)
        self.assertEqual(metrik["false_negatives"], 1)
        self.assertAlmostEqual(metrik["accuracy"], 0.75, places=4)
        self.assertAlmostEqual(metrik["precision"], 1.0, places=4)
        self.assertAlmostEqual(metrik["recall"], 0.5, places=4)
        self.assertAlmostEqual(metrik["f1_score"], 0.6667, places=4)


if __name__ == "__main__":
    unittest.main()
