import unittest

from jagapadi_eval.thresholds import (
    select_disease_thresholds,
    select_pest_thresholds,
)


class ThresholdTests(unittest.TestCase):
    def test_disease_selects_highest_coverage_under_error_limit(self) -> None:
        rows = [
            {"true_label": "blast", "predicted_label": "blast", "score": 0.9, "margin": 0.2},
            {"true_label": "blast", "predicted_label": "blast", "score": 0.8, "margin": 0.2},
            {"true_label": "tungro", "predicted_label": "blast", "score": 0.6, "margin": 0.2},
        ]
        result = select_disease_thresholds(
            rows, classes=["blast"], minimum_predictions=3
        )["blast"]
        self.assertEqual(result["state"], "calibrated")
        self.assertEqual(result["score_threshold"], 0.8)
        self.assertAlmostEqual(result["coverage"], 2 / 3, places=7)
        self.assertEqual(result["selective_error"], 0.0)

    def test_disease_insufficient_class_remains_experimental(self) -> None:
        result = select_disease_thresholds(
            [], classes=["brown_spot"], minimum_predictions=5
        )["brown_spot"]
        self.assertEqual(result["state"], "experimental")

    def test_pest_selects_highest_recall_meeting_precision(self) -> None:
        rows = [
            {"class_name": "roller", "score": 0.9, "is_true_positive": True},
            {"class_name": "roller", "score": 0.8, "is_true_positive": False},
            {"class_name": "roller", "score": 0.7, "is_true_positive": True},
        ]
        result = select_pest_thresholds(
            rows,
            classes=["roller"],
            ground_truth_counts={"roller": 3},
            minimum_ground_truth=3,
        )["roller"]
        self.assertEqual(result["state"], "calibrated")
        self.assertEqual(result["score_threshold"], 0.9)
        self.assertEqual(result["precision"], 1.0)

    def test_pest_without_ground_truth_remains_experimental(self) -> None:
        result = select_pest_thresholds(
            [], classes=["hopper"], ground_truth_counts={}, minimum_ground_truth=5
        )["hopper"]
        self.assertEqual(result["state"], "experimental")


if __name__ == "__main__":
    unittest.main()

