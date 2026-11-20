"""Tahap 01: Persiapan, validasi label bounding box, dan pembagian dataset YOLOv8 (train/val/test)."""

import os
import random
import shutil
import stat
import sys
from pathlib import Path

# Menambahkan root proyek dan folder training_python ke sys.path agar modul dapat diimpor dari Jupyter Notebook
FOLDER_SUBMODUL_INI = Path(__file__).resolve().parent
FOLDER_TRAINING_PYTHON = FOLDER_SUBMODUL_INI.parent
FOLDER_ROOT = FOLDER_TRAINING_PYTHON.parent
for path_tambahan in [FOLDER_ROOT, FOLDER_TRAINING_PYTHON, FOLDER_SUBMODUL_INI, FOLDER_ROOT / "python"]:
    if str(path_tambahan) not in sys.path:
        sys.path.insert(0, str(path_tambahan))

import konfigurasi_training as konfig


def validasi_dan_normalisasi_label_yolo(isi_teks_label: str) -> list[str]:
    """
    Memvalidasi baris koordinat bounding box format YOLO (class x_center y_center width height)
    dan menyeragamkan indeks kelas menjadi 0 (face) sebelum ditulis ke folder split_yolo.
    """
    daftar_baris_valid = []
    for baris_mentah in isi_teks_label.splitlines():
        baris_bersih = baris_mentah.strip()
        if not baris_bersih:
            continue

        bagian_angka = baris_bersih.split()
        if len(bagian_angka) < 5:
            continue

        try:
            x_tengah = float(bagian_angka[1])
            y_tengah = float(bagian_angka[2])
            lebar_kotak = float(bagian_angka[3])
            tinggi_kotak = float(bagian_angka[4])
        except ValueError:
            continue

        # Memastikan koordinat ternormalisasi berada pada rentang (0.0, 1.0] sesuai standar YOLOv8
        if not (0.0 <= x_tengah <= 1.0 and 0.0 <= y_tengah <= 1.0):
            continue
        if not (0.0 < lebar_kotak <= 1.0 and 0.0 < tinggi_kotak <= 1.0):
            continue

        daftar_baris_valid.append(
            f"0 {x_tengah:.6f} {y_tengah:.6f} {lebar_kotak:.6f} {tinggi_kotak:.6f}"
        )

    return daftar_baris_valid


def kumpulkan_pasangan_data_wajah_positif(folder_raw_wajah: Path) -> list[dict]:
    """
    Mengambil seluruh file gambar wajah manusia beserta pasangan file anotasi .txt dari folder raw_wajah_manusia
    untuk disiapkan sebagai sampel positif deteksi wajah YOLOv8.
    """
    daftar_sampel_positif = []
    if not folder_raw_wajah.exists():
        return daftar_sampel_positif

    # Memindai seluruh file gambar secara rekursif agar mendukung struktur folder datar maupun subfolder Kaggle
    semua_file_gambar = sorted(
        [
            file_item
            for file_item in folder_raw_wajah.rglob("*")
            if file_item.is_file() and file_item.suffix.lower() in konfig.DAFTAR_EKSTENSI_GAMBAR_VALID
        ]
    )

    for path_gambar in semua_file_gambar:
        # Mencari file label .txt pendamping di folder yang sama atau di subfolder sejajar bernama labels
        kandidat_label_1 = path_gambar.with_suffix(".txt")
        kandidat_label_2 = None
        if "images" in path_gambar.parts:
            indeks_bagian = list(path_gambar.parts)
            posisi_images = len(indeks_bagian) - 1 - indeks_bagian[::-1].index("images")
            indeks_bagian[posisi_images] = "labels"
            kandidat_label_2 = Path(*indeks_bagian).with_suffix(".txt")

        path_label_ditemukan = None
        if kandidat_label_1.exists():
            path_label_ditemukan = kandidat_label_1
        elif kandidat_label_2 is not None and kandidat_label_2.exists():
            path_label_ditemukan = kandidat_label_2

        if path_label_ditemukan is None:
            continue

        try:
            isi_label = path_label_ditemukan.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        baris_tervalidasi = validasi_dan_normalisasi_label_yolo(isi_label)
        if not baris_tervalidasi:
            continue

        daftar_sampel_positif.append(
            {
                "path_gambar_asal": path_gambar,
                "isi_label_yolo": "\n".join(baris_tervalidasi) + "\n",
                "jumlah_kotak_wajah": len(baris_tervalidasi),
                "tipe_sampel": "positif_wajah",
            }
        )

    return daftar_sampel_positif


def kumpulkan_data_negatif_bukan_wajah(folder_raw_negatif: Path) -> list[dict]:
    """
    Mengambil gambar tanpa wajah manusia (hewan/kera, benda, pemandangan) dari folder raw_negatif_bukan_wajah
    dan memasangkannya dengan label .txt kosong sebagai sampel negatif (background) untuk menekan False Positive.
    """
    daftar_sampel_negatif = []
    if not folder_raw_negatif.exists():
        return daftar_sampel_negatif

    semua_file_negatif = sorted(
        [
            file_item
            for file_item in folder_raw_negatif.rglob("*")
            if file_item.is_file() and file_item.suffix.lower() in konfig.DAFTAR_EKSTENSI_GAMBAR_VALID
        ]
    )

    for path_gambar in semua_file_negatif:
        daftar_sampel_negatif.append(
            {
                "path_gambar_asal": path_gambar,
                "isi_label_yolo": "",
                "jumlah_kotak_wajah": 0,
                "tipe_sampel": "negatif_bukan_wajah",
            }
        )

    return daftar_sampel_negatif


def pastikan_file_dapat_ditulis(path_target: Path):
    """Melepas atribut read-only pada file agar dapat disalin, ditimpa, atau dihapus di Windows."""
    if path_target.exists():
        try:
            os.chmod(path_target, stat.S_IWRITE | stat.S_IREAD)
        except Exception:
            pass


def bersihkan_dan_buat_folder_split_yolo(folder_split_yolo: Path):
    """
    Melepas atribut read-only bila ada, menghapus isi folder split_yolo lama secara tuntas,
    lalu membentuk ulang struktur folder images/{train,val,test} dan labels/{train,val,test}.
    """
    for nama_subfolder in ["images", "labels"]:
        target_subfolder = folder_split_yolo / nama_subfolder
        if target_subfolder.exists():
            for item_path in target_subfolder.rglob("*"):
                if item_path.is_file():
                    pastikan_file_dapat_ditulis(item_path)
            shutil.rmtree(target_subfolder)

    for nama_split in ["train", "val", "test"]:
        (folder_split_yolo / "images" / nama_split).mkdir(parents=True, exist_ok=True)
        (folder_split_yolo / "labels" / nama_split).mkdir(parents=True, exist_ok=True)


def bagi_daftar_sampel_ke_train_val_test(
    daftar_sampel: list[dict],
    rasio_train: float,
    rasio_val: float,
    generator_acak: random.Random,
) -> dict[str, list[dict]]:
    """
    Mengacak urutan sampel secara deterministik dan membagi daftar sampel ke dalam kelompok train, val, dan test.
    """
    salinan_sampel = list(daftar_sampel)
    generator_acak.shuffle(salinan_sampel)

    total_data = len(salinan_sampel)
    if total_data == 0:
        return {"train": [], "val": [], "test": []}

    if total_data == 1:
        return {"train": salinan_sampel, "val": list(salinan_sampel), "test": list(salinan_sampel)}

    if total_data == 2:
        return {"train": [salinan_sampel[0]], "val": [salinan_sampel[1]], "test": [salinan_sampel[1]]}

    jumlah_train = max(1, int(round(total_data * rasio_train)))
    jumlah_val = max(1, int(round(total_data * rasio_val)))
    if jumlah_train + jumlah_val >= total_data:
        jumlah_train = max(1, total_data - 2)
        jumlah_val = 1

    batas_akhir_val = jumlah_train + jumlah_val
    return {
        "train": salinan_sampel[:jumlah_train],
        "val": salinan_sampel[jumlah_train:batas_akhir_val],
        "test": salinan_sampel[batas_akhir_val:],
    }


def salin_sampel_ke_folder_split(
    daftar_sampel_split: list[dict],
    nama_split: str,
    folder_split_yolo: Path,
) -> dict:
    """
    Menyalin file gambar dan menulis file label .txt yang bersesuaian ke dalam folder split_yolo/images/<nama_split>
    dan split_yolo/labels/<nama_split> untuk dibaca oleh modul training YOLOv8 pada Tahap 02.
    """
    folder_gambar_tujuan = folder_split_yolo / "images" / nama_split
    folder_label_tujuan = folder_split_yolo / "labels" / nama_split

    jumlah_positif = 0
    jumlah_negatif = 0
    total_kotak_wajah = 0

    for indeks_urut, data_sampel in enumerate(daftar_sampel_split, start=1):
        path_asal = data_sampel["path_gambar_asal"]
        awalan_tipe = "wajah" if data_sampel["tipe_sampel"] == "positif_wajah" else "negatif"
        nama_dasar_unik = f"{awalan_tipe}_{indeks_urut:05d}_{path_asal.stem}"

        path_gambar_tujuan = folder_gambar_tujuan / f"{nama_dasar_unik}{path_asal.suffix.lower()}"
        path_label_tujuan = folder_label_tujuan / f"{nama_dasar_unik}.txt"

        # Menyalin isi piksel file tanpa membawa atribut read-only dari arsip sumber
        pastikan_file_dapat_ditulis(path_gambar_tujuan)
        shutil.copyfile(path_asal, path_gambar_tujuan)
        pastikan_file_dapat_ditulis(path_gambar_tujuan)
        path_label_tujuan.write_text(data_sampel["isi_label_yolo"], encoding="utf-8")

        if data_sampel["tipe_sampel"] == "positif_wajah":
            jumlah_positif += 1
            total_kotak_wajah += data_sampel["jumlah_kotak_wajah"]
        else:
            jumlah_negatif += 1

    return {
        "total_gambar": len(daftar_sampel_split),
        "jumlah_gambar_wajah_positif": jumlah_positif,
        "jumlah_gambar_negatif_bukan_wajah": jumlah_negatif,
        "total_kotak_wajah": total_kotak_wajah,
    }


def tulis_file_konfigurasi_data_yolo_yaml(folder_split_yolo: Path, path_file_yaml: Path) -> Path:
    """
    Menulis file data_yolo_wajah.yaml dengan path absolut berformat garis miring maju (POSIX)
    agar selalu terbaca dengan benar saat proses training dijalankan dari Jupyter Notebook lokal.
    """
    path_root_posix = folder_split_yolo.resolve().as_posix()
    isi_konfigurasi_yaml = (
        "# Konfigurasi dataset deteksi wajah YOLOv8 IndoLens (dihasilkan otomatis oleh Tahap 01)\n"
        f"path: {path_root_posix}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n\n"
        "nc: 1\n"
        "names:\n"
        "  0: face\n"
    )
    path_file_yaml.parent.mkdir(parents=True, exist_ok=True)
    path_file_yaml.write_text(isi_konfigurasi_yaml, encoding="utf-8")
    return path_file_yaml


def siapkan_dan_split_dataset_yolo(
    rasio_train: float = konfig.RASIO_SPLIT_TRAIN_YOLO,
    rasio_val: float = konfig.RASIO_SPLIT_VAL_YOLO,
    rasio_test: float = konfig.RASIO_SPLIT_TEST_YOLO,
    seed_acak: int = konfig.NILAI_SEED_ACAK,
) -> dict:
    """
    Mengambil data mentah dari folder raw_wajah_manusia dan raw_negatif_bukan_wajah,
    membagi secara proporsional ke dalam split train/val/test, serta menghasilkan file data_yolo_wajah.yaml
    yang akan dikirimkan ke tahap_02_training_yolo_wajah.py.
    """
    # Mengaktifkan mode output Jupyter unlimited sebelum mencetak progres persiapan ribuan file dataset
    konfig.aktifkan_output_notebook_unlimited()
    konfig.pastikan_semua_folder_tersedia()

    print("=" * 78)
    print("  TAHAP 01: PERSIAPAN & PEMBAGIAN DATASET DETEKSI WAJAH YOLOV8")
    print("=" * 78)
    print(f"[*] Folder sumber wajah positif : {konfig.FOLDER_RAW_WAJAH_MANUSIA}")
    print(f"[*] Folder sumber negatif/objek : {konfig.FOLDER_RAW_NEGATIF_BUKAN_WAJAH}")

    daftar_sampel_positif = kumpulkan_pasangan_data_wajah_positif(konfig.FOLDER_RAW_WAJAH_MANUSIA)
    daftar_sampel_negatif = kumpulkan_data_negatif_bukan_wajah(konfig.FOLDER_RAW_NEGATIF_BUKAN_WAJAH)

    if not daftar_sampel_positif:
        raise RuntimeError(
            "Belum ditemukan pasangan gambar wajah dan label .txt di folder:\n"
            f"  {konfig.FOLDER_RAW_WAJAH_MANUSIA}\n"
            "Silakan isi folder tersebut dengan gambar wajah manusia beserta file anotasi .txt YOLO terlebih dahulu."
        )

    generator_acak = random.Random(seed_acak)
    split_positif = bagi_daftar_sampel_ke_train_val_test(
        daftar_sampel_positif, rasio_train, rasio_val, generator_acak
    )
    split_negatif = bagi_daftar_sampel_ke_train_val_test(
        daftar_sampel_negatif, rasio_train, rasio_val, generator_acak
    )

    bersihkan_dan_buat_folder_split_yolo(konfig.FOLDER_SPLIT_YOLO)

    statistik_per_split = {}
    for nama_split in ["train", "val", "test"]:
        gabungan_split = split_positif[nama_split] + split_negatif[nama_split]
        generator_acak.shuffle(gabungan_split)
        statistik_per_split[nama_split] = salin_sampel_ke_folder_split(
            gabungan_split, nama_split, konfig.FOLDER_SPLIT_YOLO
        )

    path_yaml_dihasilkan = tulis_file_konfigurasi_data_yolo_yaml(
        konfig.FOLDER_SPLIT_YOLO, konfig.FILE_KONFIGURASI_DATA_YOLO_YAML
    )

    ringkasan_persiapan_dataset_yolo = {
        "path_file_data_yaml": str(path_yaml_dihasilkan),
        "folder_split_yolo": str(konfig.FOLDER_SPLIT_YOLO),
        "total_sampel_positif_wajah": len(daftar_sampel_positif),
        "total_sampel_negatif_bukan_wajah": len(daftar_sampel_negatif),
        "rasio_split": {"train": rasio_train, "val": rasio_val, "test": rasio_test},
        "detail_split": statistik_per_split,
    }

    print(f"[OK] Total sampel wajah positif       : {len(daftar_sampel_positif)} gambar")
    print(f"[OK] Total sampel negatif (background): {len(daftar_sampel_negatif)} gambar")
    for nama_split, detail in statistik_per_split.items():
        print(
            f"     - Split {nama_split.upper():5s}: {detail['total_gambar']} gambar "
            f"(Positif: {detail['jumlah_gambar_wajah_positif']}, "
            f"Negatif: {detail['jumlah_gambar_negatif_bukan_wajah']}, "
            f"Kotak Wajah: {detail['total_kotak_wajah']})"
        )
    print(f"[OK] File konfigurasi YOLO ditulis ke : {path_yaml_dihasilkan}")

    return ringkasan_persiapan_dataset_yolo


if __name__ == "__main__":
    siapkan_dan_split_dataset_yolo()
