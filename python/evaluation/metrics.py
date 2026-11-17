"""Modul perhitungan metrik evaluasi pengenalan wajah (TP, TN, FP, FN, Accuracy, Precision, Recall, F1-Score)."""


def hitung_komponen_tp_tn_fp_fn(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    label_unknown: str = "Unknown",
) -> dict[str, int]:
    """
    Menghitung jumlah True Positive (TP), True Negative (TN), False Positive (FP), dan False Negative (FN)
    secara manual dengan ketentuan:
    - TP (True Positive)  : Wajah aktor terdaftar dikenali dengan benar sebagai aktor yang bersangkutan.
    - TN (True Negative)  : Wajah orang asing (Unknown) ditolak dengan benar sebagai Unknown.
    - FP (False Positive) : Wajah orang asing dikenali sebagai aktor, atau aktor A salah dikenali sebagai aktor B.
    - FN (False Negative) : Wajah aktor terdaftar gagal dikenali (dianggap Unknown).
    """
    jumlah_tp = 0
    jumlah_tn = 0
    jumlah_fp = 0
    jumlah_fn = 0

    set_label_unknown = {label_unknown, "Tidak Dikenali", "unknown"}

    for label_asli, label_prediksi in zip(daftar_label_asli, daftar_label_prediksi):
        asli_adalah_unknown = label_asli in set_label_unknown
        prediksi_adalah_unknown = label_prediksi in set_label_unknown

        if not asli_adalah_unknown and label_asli == label_prediksi:
            jumlah_tp += 1
        elif asli_adalah_unknown and prediksi_adalah_unknown:
            jumlah_tn += 1
        elif asli_adalah_unknown and not prediksi_adalah_unknown:
            jumlah_fp += 1
        elif not asli_adalah_unknown and prediksi_adalah_unknown:
            jumlah_fn += 1
        else:
            # Aktor A ditebak sebagai Aktor B dihitung sebagai kesalahan klasifikasi positif palsu
            jumlah_fp += 1

    return {
        "true_positives": jumlah_tp,
        "true_negatives": jumlah_tn,
        "false_positives": jumlah_fp,
        "false_negatives": jumlah_fn,
    }


def hitung_nilai_accuracy(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
) -> float:
    """
    Menghitung nilai Accuracy menggunakan rumus: (jumlah prediksi tepat) / (total seluruh sampel uji).
    """
    if not daftar_label_asli or len(daftar_label_asli) != len(daftar_label_prediksi):
        return 0.0
    jumlah_tepat = sum(1 for asli, pred in zip(daftar_label_asli, daftar_label_prediksi) if asli == pred)
    return float(jumlah_tepat / len(daftar_label_asli))


def hitung_nilai_precision(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    label_unknown: str = "Unknown",
    average: str = "macro",
    zero_division: int = 0,
) -> float:
    """
    Menghitung nilai Precision menggunakan rumus: TP / (TP + FP).
    Mengukur tingkat ketepatan sistem ketika memutuskan bahwa suatu wajah adalah aktor tertentu.
    """
    if not daftar_label_asli or len(daftar_label_asli) != len(daftar_label_prediksi):
        return float(zero_division)

    komponen = hitung_komponen_tp_tn_fp_fn(daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown)
    tp = komponen["true_positives"]
    fp = komponen["false_positives"]
    penyebut = tp + fp
    if penyebut == 0:
        return float(zero_division)
    return float(tp / penyebut)


def hitung_nilai_recall(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    label_unknown: str = "Unknown",
    average: str = "macro",
    zero_division: int = 0,
) -> float:
    """
    Menghitung nilai Recall (Sensitivity) menggunakan rumus: TP / (TP + FN).
    Mengukur kemampuan sistem dalam menemukan kembali seluruh wajah aktor yang seharusnya dikenali.
    """
    if not daftar_label_asli or len(daftar_label_asli) != len(daftar_label_prediksi):
        return float(zero_division)

    komponen = hitung_komponen_tp_tn_fp_fn(daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown)
    tp = komponen["true_positives"]
    fn = komponen["false_negatives"]
    penyebut = tp + fn
    if penyebut == 0:
        return float(zero_division)
    return float(tp / penyebut)


def hitung_nilai_f1_score(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    label_unknown: str = "Unknown",
    average: str = "macro",
    zero_division: int = 0,
) -> float:
    """
    Menghitung nilai F1-Score sebagai rata-rata harmonik dari Precision dan Recall:
    F1 = (2 * Precision * Recall) / (Precision + Recall).
    """
    nilai_precision = hitung_nilai_precision(
        daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown, average=average, zero_division=zero_division
    )
    nilai_recall = hitung_nilai_recall(
        daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown, average=average, zero_division=zero_division
    )
    jumlah_pr = nilai_precision + nilai_recall
    if jumlah_pr == 0.0:
        return float(zero_division)
    return float((2.0 * nilai_precision * nilai_recall) / jumlah_pr)


def hitung_jumlah_sampel_uji(daftar_label_asli: list[str]) -> int:
    """Mengembalikan jumlah total sampel evaluasi."""
    return len(daftar_label_asli)


def hitung_seluruh_metrik_evaluasi(
    daftar_label_asli: list[str],
    daftar_label_prediksi: list[str],
    label_unknown: str = "Unknown",
) -> dict:
    """
    Menghitung dan merangkum seluruh metrik evaluasi skripsi (TP, TN, FP, FN, Accuracy, Precision, Recall, F1-Score).
    """
    if len(daftar_label_asli) != len(daftar_label_prediksi):
        raise ValueError(
            f"Panjang daftar_label_asli ({len(daftar_label_asli)}) tidak sama dengan daftar_label_prediksi ({len(daftar_label_prediksi)})"
        )

    komponen = hitung_komponen_tp_tn_fp_fn(
        daftar_label_asli,
        daftar_label_prediksi,
        label_unknown=label_unknown,
    )
    skor_accuracy = hitung_nilai_accuracy(daftar_label_asli, daftar_label_prediksi)
    skor_precision = hitung_nilai_precision(daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown)
    skor_recall = hitung_nilai_recall(daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown)
    skor_f1 = hitung_nilai_f1_score(daftar_label_asli, daftar_label_prediksi, label_unknown=label_unknown)

    return {
        "accuracy": round(skor_accuracy, 4),
        "precision": round(skor_precision, 4),
        "recall": round(skor_recall, 4),
        "f1_score": round(skor_f1, 4),
        "support": len(daftar_label_asli),
        "true_positives": komponen["true_positives"],
        "true_negatives": komponen["true_negatives"],
        "false_positives": komponen["false_positives"],
        "false_negatives": komponen["false_negatives"],
    }


# Menyediakan alias fungsi untuk menjaga kompatibilitas pemanggilan lintas modul
calculate_accuracy = hitung_nilai_accuracy
calculate_precision = hitung_nilai_precision
calculate_recall = hitung_nilai_recall
calculate_f1 = hitung_nilai_f1_score
calculate_support = hitung_jumlah_sampel_uji
calculate_fp_fn_counts = hitung_komponen_tp_tn_fp_fn
calculate_all_metrics = hitung_seluruh_metrik_evaluasi
