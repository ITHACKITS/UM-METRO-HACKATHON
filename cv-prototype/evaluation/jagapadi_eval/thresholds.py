"""Deterministic threshold selection using calibration data only."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def _round(value: float) -> float:
    return round(float(value), 8)


def select_disease_thresholds(
    samples: Iterable[dict[str, Any]],
    *,
    classes: Iterable[str],
    max_selective_error: float = 0.10,
    minimum_predictions: int = 20,
) -> dict[str, dict[str, Any]]:
    """Select the highest-coverage score/margin pair for each predicted class.

    Each calibration row must contain `true_label`, `predicted_label`, `score`, and
    `margin`. Coverage is calculated over rows predicted as that class. A class is
    experimental unless enough calibration predictions exist and an accepted set
    satisfies the selective-error constraint.
    """

    if not 0 <= max_selective_error < 1:
        raise ValueError("max_selective_error must be in [0, 1)")
    rows_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in samples:
        row = dict(raw)
        score = float(row["score"])
        margin = float(row["margin"])
        if not 0 <= score <= 1 or not 0 <= margin <= 1:
            raise ValueError("score and margin must be in [0, 1]")
        rows_by_class[str(row["predicted_label"])].append(row)

    result: dict[str, dict[str, Any]] = {}
    for label in classes:
        rows = rows_by_class.get(label, [])
        if len(rows) < minimum_predictions:
            result[label] = {
                "state": "experimental",
                "reason": "insufficient_calibration_predictions",
                "prediction_count": len(rows),
                "minimum_required": minimum_predictions,
            }
            continue
        score_values = sorted({0.0, *(float(row["score"]) for row in rows)})
        margin_values = sorted({0.0, *(float(row["margin"]) for row in rows)})
        candidates: list[dict[str, Any]] = []
        for score_threshold in score_values:
            for margin_threshold in margin_values:
                accepted = [
                    row
                    for row in rows
                    if float(row["score"]) >= score_threshold
                    and float(row["margin"]) >= margin_threshold
                ]
                if not accepted:
                    continue
                errors = sum(
                    row["true_label"] != row["predicted_label"] for row in accepted
                )
                selective_error = errors / len(accepted)
                if selective_error <= max_selective_error:
                    candidates.append(
                        {
                            "score_threshold": score_threshold,
                            "margin_threshold": margin_threshold,
                            "accepted": len(accepted),
                            "coverage": len(accepted) / len(rows),
                            "selective_error": selective_error,
                        }
                    )
        if not candidates:
            result[label] = {
                "state": "experimental",
                "reason": "selective_error_target_not_met",
                "prediction_count": len(rows),
                "max_selective_error": max_selective_error,
            }
            continue
        candidates.sort(
            key=lambda item: (
                -item["coverage"],
                item["selective_error"],
                item["score_threshold"],
                item["margin_threshold"],
            )
        )
        chosen = candidates[0]
        result[label] = {
            "state": "calibrated",
            "prediction_count": len(rows),
            "accepted_count": chosen["accepted"],
            "score_threshold": _round(chosen["score_threshold"]),
            "margin_threshold": _round(chosen["margin_threshold"]),
            "coverage": _round(chosen["coverage"]),
            "selective_error": _round(chosen["selective_error"]),
            "selection_rule": "highest_coverage_with_selective_error_limit",
            "max_selective_error": max_selective_error,
        }
    return result


def select_pest_thresholds(
    detections: Iterable[dict[str, Any]],
    *,
    classes: Iterable[str],
    ground_truth_counts: dict[str, int],
    minimum_precision: float = 0.85,
    minimum_ground_truth: int = 20,
) -> dict[str, dict[str, Any]]:
    """Choose the highest-recall score threshold meeting calibration precision.

    Rows contain `class_name`, `score`, and an evaluator-produced `is_true_positive`
    flag after one-to-one box matching. `ground_truth_counts` is the number of
    labelled instances for each class in the grouped calibration partition.
    """

    if not 0 < minimum_precision <= 1:
        raise ValueError("minimum_precision must be in (0, 1]")
    rows_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in detections:
        row = dict(raw)
        score = float(row["score"])
        if not 0 <= score <= 1:
            raise ValueError("score must be in [0, 1]")
        rows_by_class[str(row["class_name"])].append(row)

    result: dict[str, dict[str, Any]] = {}
    for label in classes:
        gt_count = int(ground_truth_counts.get(label, 0))
        rows = rows_by_class.get(label, [])
        if gt_count < minimum_ground_truth:
            result[label] = {
                "state": "experimental",
                "reason": "insufficient_ground_truth_instances",
                "ground_truth_count": gt_count,
                "minimum_required": minimum_ground_truth,
            }
            continue
        thresholds = sorted({0.0, *(float(row["score"]) for row in rows)})
        candidates: list[dict[str, Any]] = []
        for threshold in thresholds:
            accepted = [row for row in rows if float(row["score"]) >= threshold]
            if not accepted:
                continue
            true_positives = sum(bool(row["is_true_positive"]) for row in accepted)
            precision = true_positives / len(accepted)
            recall = min(true_positives / gt_count, 1.0)
            if precision >= minimum_precision:
                candidates.append(
                    {
                        "threshold": threshold,
                        "precision": precision,
                        "recall": recall,
                        "true_positives": true_positives,
                        "false_positives": len(accepted) - true_positives,
                    }
                )
        if not candidates:
            result[label] = {
                "state": "experimental",
                "reason": "precision_target_not_met",
                "ground_truth_count": gt_count,
                "minimum_precision": minimum_precision,
            }
            continue
        candidates.sort(
            key=lambda item: (
                -item["recall"],
                -item["precision"],
                item["threshold"],
            )
        )
        chosen = candidates[0]
        result[label] = {
            "state": "calibrated",
            "ground_truth_count": gt_count,
            "score_threshold": _round(chosen["threshold"]),
            "precision": _round(chosen["precision"]),
            "recall": _round(chosen["recall"]),
            "true_positives": chosen["true_positives"],
            "false_positives": chosen["false_positives"],
            "selection_rule": "highest_recall_with_precision_floor",
            "minimum_precision": minimum_precision,
        }
    return result

