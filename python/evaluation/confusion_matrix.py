"""Modul pembuatan dan ekspor Confusion Matrix secara manual menggunakan NumPy tanpa library pre-built."""

import os
from pathlib import Path
import cv2
import numpy as np


def bangun_matriks_konfusi(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    daftar_kelas_urut: list[str] | None = None,
) -> tuple[np.ndarray, list[str]]:
    """
    Menyusun matriks konfusi (Confusion Matrix) berukuran N x N secara manual dari pasangan
    daftar_label_asli (ground truth) dan daftar_label_prediksi hasil pengenalan wajah.
    Baris merepresentasikan kelas sebenarnya (True Label) dan kolom merepresentasikan kelas prediksi (Predicted Label).
    """
    if daftar_kelas_urut is None:
        daftar_kelas_urut = sorted(list(set(daftar_label_asli + daftar_label_prediksi)))

    jumlah_kelas = len(daftar_kelas_urut)
    peta_indeks_kelas = {nama_kelas: idx for idx, nama_kelas in enumerate(daftar_kelas_urut)}
    matriks_konfusi = np.zeros((jumlah_kelas, jumlah_kelas), dtype=np.int32)

    for label_benar, label_tebakan in zip(daftar_label_asli, daftar_label_prediksi):
        if label_benar in peta_indeks_kelas and label_tebakan in peta_indeks_kelas:
            baris = peta_indeks_kelas[label_benar]
            kolom = peta_indeks_kelas[label_tebakan]
            matriks_konfusi[baris, kolom] += 1

    return matriks_konfusi, daftar_kelas_urut


def ekspor_matriks_konfusi_ke_dict(
    matriks_konfusi: np.ndarray,
    daftar_kelas: list[str],
) -> dict:
    """
    Mengubah matriks konfusi NumPy beserta daftar nama kelasnya ke dalam format dictionary siap simpan ke JSON.
    """
    return {
        "labels": list(daftar_kelas),
        "matrix": matriks_konfusi.tolist(),
    }


def simpan_visualisasi_matriks_konfusi(
    matriks_konfusi: np.ndarray,
    daftar_kelas: list[str],
    path_file_output: str | Path,
    judul_grafik: str = "Confusion Matrix Pengenalan Wajah Aktor",
) -> str:
    """
    Menggambar tabel visualisasi Confusion Matrix ke dalam citra PNG menggunakan OpenCV
    dan menyimpannya ke path_file_output sebagai lampiran laporan evaluasi di Jupyter Notebook.
    """
    path_tujuan = Path(path_file_output)
    path_tujuan.parent.mkdir(parents=True, exist_ok=True)

    jumlah_kelas = max(1, len(daftar_kelas))
    ukuran_sel = 110
    margin_kiri = 240
    margin_atas = 110
    margin_kanan = 60
    margin_bawah = 80

    lebar_kanvas = margin_kiri + (jumlah_kelas * ukuran_sel) + margin_kanan
    tinggi_kanvas = margin_atas + (jumlah_kelas * ukuran_sel) + margin_bawah

    kanvas = np.full((tinggi_kanvas, lebar_kanvas, 3), 255, dtype=np.uint8)
    nilai_maksimum = max(1, int(np.max(matriks_konfusi))) if matriks_konfusi.size > 0 else 1

    cv2.putText(
        kanvas,
        judul_grafik,
        (25, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (20, 20, 20),
        2,
        cv2.LINE_AA,
    )

    for indeks_baris in range(jumlah_kelas):
        for indeks_kolom in range(jumlah_kelas):
            x1 = margin_kiri + (indeks_kolom * ukuran_sel)
            y1 = margin_atas + (indeks_baris * ukuran_sel)
            x2 = x1 + ukuran_sel
            y2 = y1 + ukuran_sel

            nilai_sel = int(matriks_konfusi[indeks_baris, indeks_kolom])
            intensitas = nilai_sel / float(nilai_maksimum)

            # Memberi gradasi warna biru muda ke biru tua sesuai proporsi jumlah sampel pada sel
            kanal_merah = int(240 - (180 * intensitas))
            kanal_hijau = int(245 - (130 * intensitas))
            kanal_biru = int(255 - (40 * intensitas))

            cv2.rectangle(kanvas, (x1, y1), (x2, y2), (kanal_biru, kanal_hijau, kanal_merah), -1)
            cv2.rectangle(kanvas, (x1, y1), (x2, y2), (180, 180, 180), 1)

            warna_angka = (255, 255, 255) if intensitas > 0.55 else (20, 20, 20)
            teks_angka = str(nilai_sel)
            cv2.putText(
                kanvas,
                teks_angka,
                (x1 + (ukuran_sel // 2) - 12, y1 + (ukuran_sel // 2) + 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                warna_angka,
                2,
                cv2.LINE_AA,
            )

    for idx, nama_label in enumerate(daftar_kelas):
        label_pendek = nama_label[:22]
        y_tengah = margin_atas + (idx * ukuran_sel) + (ukuran_sel // 2) + 5
        x_tengah = margin_kiri + (idx * ukuran_sel) + 12

        cv2.putText(
            kanvas,
            label_pendek,
            (15, y_tengah),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (30, 30, 30),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            kanvas,
            label_pendek[:12],
            (x_tengah, margin_atas - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (30, 30, 30),
            1,
            cv2.LINE_AA,
        )

    cv2.imwrite(str(path_tujuan), kanvas)
    return str(path_tujuan)


# Menyediakan alias fungsi untuk kompatibilitas pemanggilan lintas modul
build_matrix = bangun_matriks_konfusi
export_matrix = ekspor_matriks_konfusi_ke_dict
plot_matrix = simpan_visualisasi_matriks_konfusi
