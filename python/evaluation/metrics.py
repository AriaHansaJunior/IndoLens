"""
IndoLens - Face Recognition Classification Metrics Module
Focuses on evaluating FaceNet face recognition performance.
"""

from typing import List, Dict, Any, Union
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

def calculate_accuracy(y_true: List[str], y_pred: List[str]) -> float:
    """Calculate overall accuracy for face recognition classification."""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    return float(accuracy_score(y_true, y_pred))

def calculate_precision(y_true: List[str], y_pred: List[str], average: str = 'weighted', zero_division: int = 0) -> float:
    """Calculate precision for face recognition classification."""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    return float(precision_score(y_true, y_pred, average=average, zero_division=zero_division))

def calculate_recall(y_true: List[str], y_pred: List[str], average: str = 'weighted', zero_division: int = 0) -> float:
    """Calculate recall for face recognition classification."""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    return float(recall_score(y_true, y_pred, average=average, zero_division=zero_division))

def calculate_f1(y_true: List[str], y_pred: List[str], average: str = 'weighted', zero_division: int = 0) -> float:
    """Calculate F1-Score for face recognition classification."""
    if not y_true or len(y_true) != len(y_pred):
        return 0.0
    return float(f1_score(y_true, y_pred, average=average, zero_division=zero_division))

def calculate_support(y_true: List[str]) -> int:
    """Calculate total number of ground truth samples."""
    return len(y_true)

def calculate_fp_fn_counts(y_true: List[str], y_pred: List[str], unknown_label: str = "Unknown") -> Dict[str, int]:
    """
    Calculate False Positive and False Negative counts.
    - False Positive (FP): Known face incorrectly predicted as wrong actor or unknown predicted as an actor.
    - False Negative (FN): Known face predicted as Unknown or wrong actor.
    """
    fp = 0
    fn = 0
    for gt, pred in zip(y_true, y_pred):
        if gt == pred:
            continue
        if gt == unknown_label and pred != unknown_label:
            fp += 1
        elif gt != unknown_label and pred == unknown_label:
            fn += 1
        else:
            # Wrong actor prediction counts as both FP (for predicted class) & FN (for true class)
            fp += 1
            fn += 1
    return {"false_positives": fp, "false_negatives": fn}

def calculate_all_metrics(y_true: List[str], y_pred: List[str], unknown_label: str = "Unknown") -> Dict[str, Any]:
    """Calculate complete metric summary for evaluation."""
    if len(y_true) != len(y_pred):
        raise ValueError(f"Ground truth length ({len(y_true)}) does not match prediction length ({len(y_pred)})")
        
    acc = calculate_accuracy(y_true, y_pred)
    prec = calculate_precision(y_true, y_pred, average='macro', zero_division=0)
    rec = calculate_recall(y_true, y_pred, average='macro', zero_division=0)
    f1 = calculate_f1(y_true, y_pred, average='macro', zero_division=0)
    support = calculate_support(y_true)
    fp_fn = calculate_fp_fn_counts(y_true, y_pred, unknown_label)

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "support": support,
        "false_positives": fp_fn["false_positives"],
        "false_negatives": fp_fn["false_negatives"],
    }
