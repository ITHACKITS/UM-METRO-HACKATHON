import unittest

from jagapadi_eval.metrics import (
    box_iou,
    classification_metrics,
    detection_precision_recall,
    group_bootstrap_interval,
    match_detections,
    pest_detection_metrics,
    presence_metrics,
    score_calibration_diagnostics,
)


class MetricsTests(unittest.TestCase):
    def test_classification_reports_coverage_and_macro_f1(self) -> None:
        rows = [
            {"true_label": "a", "predicted_label": "a", "accepted": True},
            {"true_label": "a", "predicted_label": "b", "accepted": True},
            {"true_label": "b", "predicted_label": "b", "accepted": True},
            {"true_label": "b", "predicted_label": "a", "accepted": False},
        ]
        result = classification_metrics(rows, ["a", "b"])
        self.assertEqual(result["coverage"], 0.75)
        self.assertEqual(result["accepted_count"], 3)
        self.assertAlmostEqual(result["balanced_accuracy"], 0.75)

    def test_calibration_is_explicitly_raw_score_diagnostic(self) -> None:
        result = score_calibration_diagnostics(
            [
                {"true_label": "a", "scores": {"a": 0.8, "b": 0.2}},
                {"true_label": "b", "scores": {"a": 0.4, "b": 0.6}},
            ],
            bins=5,
        )
        self.assertEqual(result["count"], 2)
        self.assertIn("not evidence", result["warning"])
        self.assertIsNotNone(result["brier_score"])

    def test_missed_supported_class_contributes_zero_f1(self) -> None:
        result = classification_metrics(
            [
                {"true_label": "a", "predicted_label": "a", "accepted": True},
                {"true_label": "b", "predicted_label": "a", "accepted": True},
            ],
            ["a", "b"],
        )
        self.assertEqual(result["per_class"]["b"]["f1"], 0.0)
        self.assertLess(result["macro_f1"], 0.5)

    def test_detection_and_presence_metrics(self) -> None:
        detection = detection_precision_recall(
            [
                {"score": 0.9, "is_true_positive": True},
                {"score": 0.8, "is_true_positive": False},
                {"score": 0.7, "is_true_positive": True},
            ],
            ground_truth_count=3,
        )
        self.assertEqual(detection["true_positives"], 2)
        self.assertAlmostEqual(detection["recall"], 2 / 3)
        presence = presence_metrics(
            [
                {"present": True, "detected": True},
                {"present": False, "detected": False},
                {"present": False, "detected": True},
            ]
        )
        self.assertAlmostEqual(presence["accuracy"], 2 / 3)

    def test_box_iou_and_greedy_matching_do_not_reuse_truth(self) -> None:
        box = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
        self.assertEqual(box_iou(box, box), 1.0)
        truth = [{"image_id": "one", "class_name": "roller", "bbox": box}]
        detections = [
            {"image_id": "one", "class_name": "roller", "score": 0.9, "bbox": box},
            {"image_id": "one", "class_name": "roller", "score": 0.8, "bbox": box},
        ]
        matched = match_detections(detections, truth, iou_threshold=0.5)
        self.assertTrue(matched[0]["is_true_positive"])
        self.assertFalse(matched[1]["is_true_positive"])

    def test_pest_map_and_false_positive_negative_rate(self) -> None:
        box = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
        truth = [{"image_id": "positive", "class_name": "roller", "bbox": box}]
        detections = [
            {"image_id": "positive", "class_name": "roller", "score": 0.9, "bbox": box},
            {"image_id": "negative", "class_name": "roller", "score": 0.8, "bbox": box},
        ]
        result = pest_detection_metrics(
            detections,
            truth,
            classes=["roller", "hopper"],
            evaluated_image_ids=["positive", "negative"],
            minimum_ground_truth=1,
        )
        self.assertEqual(result["tested_class_count"], 1)
        self.assertEqual(result["map_0.50"], 1.0)
        self.assertEqual(result["map_0.50_0.95"], 1.0)
        self.assertEqual(
            result["per_class"]["roller"]["false_detections_per_negative_image"],
            1.0,
        )
        self.assertEqual(result["per_class"]["hopper"]["state"], "not_testable")

    def test_group_bootstrap_is_deterministic(self) -> None:
        rows = [
            {"group_id": "field-a", "value": 1.0},
            {"group_id": "field-a", "value": 1.0},
            {"group_id": "field-b", "value": 0.0},
        ]
        statistic = lambda sample: sum(row["value"] for row in sample) / len(sample)
        first = group_bootstrap_interval(rows, statistic, iterations=100, seed=7)
        second = group_bootstrap_interval(rows, statistic, iterations=100, seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first["group_count"], 2)


if __name__ == "__main__":
    unittest.main()

