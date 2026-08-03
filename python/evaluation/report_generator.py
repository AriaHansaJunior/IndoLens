"""
IndoLens - Report Generator Module
Generates evaluation reports in JSON, CSV, and TXT Summary formats for Bab 4.
"""

import os
import json
import csv
from typing import Dict, Any, List

def generate_json(report_data: Dict[str, Any], output_path: str) -> str:
    """Export evaluation metrics to JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False)
    return output_path

def generate_csv(report_data: Dict[str, Any], output_path: str) -> str:
    """Export main evaluation metrics and threshold tests to CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    metrics = report_data.get("metrics", {})
    performance = report_data.get("performance", {})
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Metric Category", "Metric Name", "Value"])
        
        for k, v in metrics.items():
            writer.writerow(["Face Recognition Metrics", k, v])
            
        for k, v in performance.items():
            writer.writerow(["Performance Metrics", k, v])
            
        if "threshold_results" in report_data:
            writer.writerow([])
            writer.writerow(["Threshold Test", "Threshold", "Accuracy", "Precision", "Recall", "F1 Score", "FP", "FN"])
            for row in report_data["threshold_results"]:
                writer.writerow([
                    "Threshold Test",
                    row.get("threshold"),
                    row.get("accuracy"),
                    row.get("precision"),
                    row.get("recall"),
                    row.get("f1_score"),
                    row.get("false_positives"),
                    row.get("false_negatives")
                ])
    return output_path

def generate_summary(report_data: Dict[str, Any], output_path: str) -> str:
    """Generate human-readable summary text file (evaluation_summary.txt)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    metrics = report_data.get("metrics", {})
    perf = report_data.get("performance", {})
    
    lines = [
        "==================================================",
        "          INDOLENS EVALUATION SUMMARY             ",
        "==================================================",
        f"Evaluation Target: Face Recognition Performance",
        f"Threshold        : {report_data.get('threshold', 0.60)}",
        f"Total Samples    : {metrics.get('support', 0)}",
        f"Processed Frames : {perf.get('total_frames_processed', 0)}",
        "--------------------------------------------------",
        "CLASSIFICATION METRICS:",
        f"  - Accuracy        : {metrics.get('accuracy', 0.0):.4f}",
        f"  - Precision       : {metrics.get('precision', 0.0):.4f}",
        f"  - Recall          : {metrics.get('recall', 0.0):.4f}",
        f"  - F1 Score        : {metrics.get('f1_score', 0.0):.4f}",
        f"  - False Positives : {metrics.get('false_positives', 0)}",
        f"  - False Negatives : {metrics.get('false_negatives', 0)}",
        "--------------------------------------------------",
        "PERFORMANCE METRICS:",
        f"  - Processing Time : {perf.get('processing_time_sec', 0.0)} sec",
        f"  - FPS             : {perf.get('fps', 0.0)}",
        f"  - Memory Usage    : {perf.get('memory_mb', 0.0)} MB ({perf.get('memory_percent', 0.0)}%)",
        f"  - CPU Usage       : {perf.get('cpu_percent', 0.0)}%",
        "==================================================",
        "Status: Evaluation Completed Successfully",
        "=================================================="
    ]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
        
    return output_path
