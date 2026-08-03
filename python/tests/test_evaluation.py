"""
IndoLens - Session 12 Evaluation Module Unit Test
Verifies evaluator, metrics, confusion matrix, performance, and report generator.
"""

import os
import sys
import json
import csv
import unittest

# Add python directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../evaluation')))

from evaluation.evaluator import Evaluator
from evaluation.metrics import calculate_all_metrics
from evaluation.performance import get_performance_summary

class TestEvaluationModule(unittest.TestCase):

    def setUp(self):
        self.temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../temp/test_eval'))
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.gt_file = os.path.join(self.temp_dir, "gt.json")
        self.pred_file = os.path.join(self.temp_dir, "pred.json")

        self.gt_data = [
            {"sample_id": 1, "ground_truth": "Bayu Skak"},
            {"sample_id": 2, "ground_truth": "Bayu Skak"},
            {"sample_id": 3, "ground_truth": "Joe Taslim"},
            {"sample_id": 4, "ground_truth": "Unknown"},
            {"sample_id": 5, "ground_truth": "Bayu Skak"}
        ]
        
        self.pred_data = [
            {"sample_id": 1, "prediction": "Bayu Skak"},
            {"sample_id": 2, "prediction": "Bayu Skak"},
            {"sample_id": 3, "prediction": "Joe Taslim"},
            {"sample_id": 4, "prediction": "Unknown"},
            {"sample_id": 5, "prediction": "Unknown"} # False Negative for Bayu Skak
        ]

        with open(self.gt_file, 'w') as f:
            json.dump(self.gt_data, f)
            
        with open(self.pred_file, 'w') as f:
            json.dump(self.pred_data, f)

    def test_evaluator_pipeline(self):
        evaluator = Evaluator(output_dir=self.temp_dir)
        report = evaluator.evaluate(self.gt_file, self.pred_file, threshold=0.60, total_frames=5)

        # Check metrics calculated
        metrics = report["metrics"]
        self.assertEqual(metrics["support"], 5)
        self.assertEqual(metrics["false_negatives"], 1)
        self.assertEqual(metrics["false_positives"], 0)
        self.assertEqual(metrics["accuracy"], 0.8)

        # Check performance metrics
        perf = report["performance"]
        self.assertEqual(perf["total_frames_processed"], 5)

        # Check files created
        reports_dir = os.path.join(self.temp_dir, "reports")
        eval_dir = os.path.join(self.temp_dir, "evaluation")
        
        json_path = os.path.join(reports_dir, "evaluation.json")
        csv_path = os.path.join(reports_dir, "evaluation.csv")
        summary_path = os.path.join(reports_dir, "evaluation_summary.txt")
        cm_path = os.path.join(eval_dir, "confusion_matrix.png")

        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(os.path.exists(summary_path))
        self.assertTrue(os.path.exists(cm_path))

        # Check JSON and CSV consistency
        with open(json_path, 'r') as f:
            json_report = json.load(f)

        self.assertEqual(json_report["metrics"]["accuracy"], metrics["accuracy"])
        self.assertEqual(json_report["metrics"]["f1_score"], metrics["f1_score"])

if __name__ == "__main__":
    unittest.main()
