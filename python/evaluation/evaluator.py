"""
IndoLens - Main Evaluator Module
Orchestrates face recognition evaluation, threshold experiments, performance metrics, and report generation.
"""

import os
import json
import time
import csv
from typing import List, Dict, Any, Tuple, Optional

from metrics import calculate_all_metrics
from confusion_matrix import build_matrix, export_matrix, plot_matrix
from performance import get_performance_summary
from report_generator import generate_json, generate_csv, generate_summary

class Evaluator:
    """Evaluator for Face Recognition Performance (FaceNet Classification)."""

    def __init__(self, output_dir: str = "python/outputs"):
        self.reports_dir = os.path.join(output_dir, "reports")
        self.eval_dir = os.path.join(output_dir, "evaluation")
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.eval_dir, exist_ok=True)

    def load_ground_truth(self, ground_truth_path: str) -> List[Dict[str, Any]]:
        """
        Load ground truth data from external CSV or JSON file.
        Supports format:
        CSV: frame/sample, ground_truth_label
        JSON: [{"sample_id": ..., "ground_truth": "Actor Name"}, ...]
        """
        if not os.path.exists(ground_truth_path):
            raise FileNotFoundError(f"Ground truth file not found: {ground_truth_path}")

        records = []
        if ground_truth_path.endswith('.json'):
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        elif ground_truth_path.endswith('.csv'):
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
        else:
            raise ValueError("Unsupported ground truth format. Must be .json or .csv")
            
        return records

    def load_predictions(self, predictions_path: str) -> List[Dict[str, Any]]:
        """Load predictions data from external CSV or JSON file."""
        if not os.path.exists(predictions_path):
            raise FileNotFoundError(f"Predictions file not found: {predictions_path}")

        records = []
        if predictions_path.endswith('.json'):
            with open(predictions_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        elif predictions_path.endswith('.csv'):
            with open(predictions_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(row)
        else:
            raise ValueError("Unsupported predictions format. Must be .json or .csv")
            
        return records

    def evaluate(self, ground_truth_path: str, predictions_path: str, threshold: float = 0.60, total_frames: int = 0) -> Dict[str, Any]:
        """
        Main evaluation function.
        Reads external ground truth and prediction files, computes metrics, plots confusion matrix,
        and exports reports (JSON, CSV, summary text).
        """
        start_time = time.time()

        gt_records = self.load_ground_truth(ground_truth_path)
        pred_records = self.load_predictions(predictions_path)

        if len(gt_records) != len(pred_records):
            raise ValueError(f"Ground truth count ({len(gt_records)}) does not match prediction count ({len(pred_records)})")

        y_true = [r.get("ground_truth", r.get("label", "Unknown")) for r in gt_records]
        y_pred = [r.get("prediction", r.get("predicted_label", "Unknown")) for r in pred_records]

        if total_frames <= 0:
            total_frames = len(y_true)

        # 1. Calculate Classification Metrics
        metrics_res = calculate_all_metrics(y_true, y_pred)

        # 2. Build Confusion Matrix & Plot Image
        cm, labels = build_matrix(y_true, y_pred)
        cm_data = export_matrix(cm, labels)
        cm_plot_path = os.path.join(self.eval_dir, "confusion_matrix.png")
        plot_matrix(cm, labels, cm_plot_path)

        end_time = time.time()

        # 3. Performance Measurement
        perf_res = get_performance_summary(start_time, end_time, total_frames)

        # Build Full Report Object
        report_data = {
            "threshold": threshold,
            "metrics": metrics_res,
            "performance": perf_res,
            "confusion_matrix": cm_data
        }

        # 4. Export Reports
        json_path = os.path.join(self.reports_dir, "evaluation.json")
        csv_path = os.path.join(self.reports_dir, "evaluation.csv")
        txt_path = os.path.join(self.reports_dir, "evaluation_summary.txt")

        generate_json(report_data, json_path)
        generate_csv(report_data, csv_path)
        generate_summary(report_data, txt_path)

        return report_data

    def evaluate_video(self, video_path: str, ground_truth_path: str, predictions_path: str) -> Dict[str, Any]:
        """Reserved method for video-specific evaluation."""
        return self.evaluate(ground_truth_path, predictions_path)

    def evaluate_dataset(self, dataset_dir: str, ground_truth_path: str, predictions_path: str) -> Dict[str, Any]:
        """Reserved method for dataset-wide evaluation."""
        return self.evaluate(ground_truth_path, predictions_path)

    def run_threshold_experiments(self, y_true: List[str], predictions_by_threshold: Dict[float, List[str]]) -> List[Dict[str, Any]]:
        """
        Evaluates recognition performance across multiple distance thresholds (e.g. 0.40 - 0.70).
        Saves accuracy, precision, recall, f1, FP, and FN per threshold.
        """
        threshold_results = []
        for thresh, y_pred in sorted(predictions_by_threshold.items()):
            metrics = calculate_all_metrics(y_true, y_pred)
            metrics["threshold"] = thresh
            threshold_results.append(metrics)
        return threshold_results

def evaluate(ground_truth_path: str, predictions_path: str, threshold: float = 0.60) -> Dict[str, Any]:
    """Helper entry point for evaluator."""
    evaluator = Evaluator()
    return evaluator.evaluate(ground_truth_path, predictions_path, threshold)

def evaluate_video(video_path: str, ground_truth_path: str, predictions_path: str) -> Dict[str, Any]:
    """Helper entry point for video evaluation."""
    evaluator = Evaluator()
    return evaluator.evaluate_video(video_path, ground_truth_path, predictions_path)

def evaluate_dataset(dataset_dir: str, ground_truth_path: str, predictions_path: str) -> Dict[str, Any]:
    """Helper entry point for dataset evaluation."""
    evaluator = Evaluator()
    return evaluator.evaluate_dataset(dataset_dir, ground_truth_path, predictions_path)
