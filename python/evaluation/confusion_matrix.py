"""
IndoLens - Confusion Matrix Module for Face Recognition Evaluation
"""

import os
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from sklearn.metrics import confusion_matrix as sklearn_cm
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

def build_matrix(y_true: List[str], y_pred: List[str], labels: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
    """Build confusion matrix and return matrix with unique labels."""
    if labels is None:
        labels = sorted(list(set(y_true + y_pred)))
    cm = sklearn_cm(y_true, y_pred, labels=labels)
    return cm, labels

def export_matrix(cm: np.ndarray, labels: List[str]) -> Dict[str, Any]:
    """Export confusion matrix to dictionary representation."""
    return {
        "labels": labels,
        "matrix": cm.tolist()
    }

def plot_matrix(cm: np.ndarray, labels: List[str], output_path: str, title: str = "Face Recognition Confusion Matrix") -> str:
    """Plot confusion matrix as a heatmap and save PNG to output_path."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    cax = ax.matshow(cm, cmap=plt.cm.Blues)
    fig.colorbar(cax)

    # Set labels
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='left')
    ax.set_yticklabels(labels)

    # Write values inside cells
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), va='center', ha='center', color='black' if cm[i, j] < cm.max() / 2 else 'white')

    plt.title(title, fontsize=14, pad=25)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.ylabel('True Label', fontsize=12)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close()
    return output_path
