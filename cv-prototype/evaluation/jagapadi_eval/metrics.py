"""Small dependency-light metric implementations with explicit sample counts."""

from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any, Callable, Iterable


def _safe_div(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def classification_metrics(
    rows: Iterable[dict[str, Any]], classes: Iterable[str]
) -> dict[str, Any]:
    """Compute disease classification metrics for accepted rows only.

    Required fields are `true_label`, `predicted_label`, and `accepted`. Coverage
    and selective error are reported alongside the classification statistics so
    abstention cannot make a headline metric look better without its trade-off.
    """

    all_rows = list(rows)
    labels = list(classes)
    accepted = [row for row in all_rows if bool(row.get("accepted", True))]
    confusion = {
        truth: {prediction: 0 for prediction in labels} for truth in labels
    }
    unknown_predictions = 0
    for row in accepted:
        truth = str(row["true_label"])
        prediction = str(row["predicted_label"])
        if truth in confusion and prediction in confusion[truth]:
            confusion[truth][prediction] += 1
        else:
            unknown_predictions += 1

    per_class: dict[str, dict[str, Any]] = {}
    recalls: list[float] = []
    f1_values: list[float] = []
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[truth][label] for truth in labels if truth != label)
        fn = sum(
            confusion[label][prediction]
            for prediction in labels
            if prediction != label
        )
        support = sum(confusion[label].values())
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        if support:
            precision_for_f1 = precision if precision is not None else 0.0
            recall_for_f1 = recall if recall is not None else 0.0
            denominator = precision_for_f1 + recall_for_f1
            f1 = (
                2 * precision_for_f1 * recall_for_f1 / denominator
                if denominator
                else 0.0
            )
        else:
            f1 = None
        if recall is not None:
            recalls.append(recall)
        if f1 is not None:
            f1_values.append(f1)
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    correct = sum(confusion[label][label] for label in labels)
    accepted_in_scope = sum(sum(row.values()) for row in confusion.values())
    errors = accepted_in_scope - correct + unknown_predictions
    return {
        "total_count": len(all_rows),
        "accepted_count": len(accepted),
        "coverage": _safe_div(len(accepted), len(all_rows)),
        "selective_error": _safe_div(errors, len(accepted)),
        "accuracy": _safe_div(correct, len(accepted)),
        "balanced_accuracy": sum(recalls) / len(recalls) if recalls else None,
        "macro_f1": sum(f1_values) / len(f1_values) if f1_values else None,
        "per_class": per_class,
        "confusion_matrix": confusion,
        "unknown_prediction_count": unknown_predictions,
    }


def bootstrap_interval(
    rows: Iterable[dict[str, Any]],
    statistic: Callable[[list[dict[str, Any]]], float | None],
    *,
    iterations: int = 2000,
    seed: int = 20261031,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    """Return a deterministic percentile bootstrap confidence interval."""

    observations = list(rows)
    if not observations or iterations < 1:
        return {"estimate": None, "lower": None, "upper": None, "iterations": 0}
    estimate = statistic(observations)
    randomizer = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        resample = [
            observations[randomizer.randrange(len(observations))]
            for _ in observations
        ]
        value = statistic(resample)
        if value is not None and math.isfinite(value):
            samples.append(value)
    if not samples:
        return {
            "estimate": estimate,
            "lower": None,
            "upper": None,
            "iterations": 0,
        }
    samples.sort()
    lower_index = max(0, int((alpha / 2) * (len(samples) - 1)))
    upper_index = min(
        len(samples) - 1, int((1 - alpha / 2) * (len(samples) - 1))
    )
    return {
        "estimate": estimate,
        "lower": samples[lower_index],
        "upper": samples[upper_index],
        "iterations": len(samples),
    }


def group_bootstrap_interval(
    rows: Iterable[dict[str, Any]],
    statistic: Callable[[list[dict[str, Any]]], float | None],
    *,
    group_key: str = "group_id",
    iterations: int = 2000,
    seed: int = 20261031,
    alpha: float = 0.05,
) -> dict[str, float | int | None]:
    """Bootstrap whole field/plant/session groups rather than individual images."""

    observations = list(rows)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        if group_key not in row:
            raise ValueError(f"missing bootstrap group key: {group_key}")
        grouped.setdefault(str(row[group_key]), []).append(row)
    group_ids = sorted(grouped)
    if not group_ids or iterations < 1:
        return {
            "estimate": None,
            "lower": None,
            "upper": None,
            "iterations": 0,
            "group_count": len(group_ids),
        }
    estimate = statistic(observations)
    randomizer = random.Random(seed)
    samples: list[float] = []
    for _ in range(iterations):
        selected_groups = [
            group_ids[randomizer.randrange(len(group_ids))] for _ in group_ids
        ]
        resample = [row for group in selected_groups for row in grouped[group]]
        value = statistic(resample)
        if value is not None and math.isfinite(value):
            samples.append(value)
    if not samples:
        return {
            "estimate": estimate,
            "lower": None,
            "upper": None,
            "iterations": 0,
            "group_count": len(group_ids),
        }
    samples.sort()
    lower_index = max(0, int((alpha / 2) * (len(samples) - 1)))
    upper_index = min(
        len(samples) - 1, int((1 - alpha / 2) * (len(samples) - 1))
    )
    return {
        "estimate": estimate,
        "lower": samples[lower_index],
        "upper": samples[upper_index],
        "iterations": len(samples),
        "group_count": len(group_ids),
    }


def score_calibration_diagnostics(
    rows: Iterable[dict[str, Any]], *, bins: int = 10
) -> dict[str, Any]:
    """Compute raw-score Brier/ECE diagnostics without calling scores probabilities.

    Rows contain `true_label` and `scores`, a mapping for every evaluated class.
    These diagnostics do not establish probabilistic calibration; the report and UI
    must continue to call the values `model_score`.
    """

    observations = list(rows)
    if not observations:
        return {"count": 0, "brier_score": None, "ece": None, "bins": []}
    brier_total = 0.0
    top_items: list[tuple[float, bool]] = []
    for row in observations:
        scores = {str(key): float(value) for key, value in row["scores"].items()}
        if not scores or any(value < 0 or value > 1 for value in scores.values()):
            raise ValueError("scores must be a non-empty mapping in [0, 1]")
        truth = str(row["true_label"])
        brier_total += sum(
            (score - (1.0 if label == truth else 0.0)) ** 2
            for label, score in scores.items()
        )
        top_label, top_score = max(scores.items(), key=lambda item: item[1])
        top_items.append((top_score, top_label == truth))

    bin_rows: list[dict[str, Any]] = []
    weighted_gap = 0.0
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            item
            for item in top_items
            if lower <= item[0] <= upper
            and (index == bins - 1 or item[0] < upper)
        ]
        if not members:
            continue
        mean_score = sum(item[0] for item in members) / len(members)
        accuracy = sum(item[1] for item in members) / len(members)
        gap = abs(mean_score - accuracy)
        weighted_gap += gap * len(members) / len(top_items)
        bin_rows.append(
            {
                "lower": lower,
                "upper": upper,
                "count": len(members),
                "mean_model_score": mean_score,
                "observed_accuracy": accuracy,
                "absolute_gap": gap,
            }
        )
    return {
        "count": len(observations),
        "brier_score": brier_total / len(observations),
        "ece": weighted_gap,
        "bins": bin_rows,
        "warning": "raw model-score diagnostic; not evidence of calibrated probability",
    }


def detection_precision_recall(
    detections: Iterable[dict[str, Any]], ground_truth_count: int
) -> dict[str, Any]:
    """Compute precision/recall/AP from already one-to-one-matched detections."""

    rows = sorted(detections, key=lambda row: float(row["score"]), reverse=True)
    if ground_truth_count < 0:
        raise ValueError("ground_truth_count cannot be negative")
    true_positives = 0
    false_positives = 0
    curve: list[dict[str, float | int]] = []
    for row in rows:
        if bool(row["is_true_positive"]):
            true_positives += 1
        else:
            false_positives += 1
        curve.append(
            {
                "score": float(row["score"]),
                "precision": true_positives / (true_positives + false_positives),
                "recall": min(true_positives / ground_truth_count, 1.0)
                if ground_truth_count
                else 0.0,
            }
        )
    # All-point interpolated AP over recall increments.
    ap = None
    if ground_truth_count:
        recalls = [0.0, *(float(point["recall"]) for point in curve), 1.0]
        precisions = [0.0, *(float(point["precision"]) for point in curve), 0.0]
        for index in range(len(precisions) - 2, -1, -1):
            precisions[index] = max(precisions[index], precisions[index + 1])
        ap = sum(
            (recalls[index] - recalls[index - 1]) * precisions[index]
            for index in range(1, len(recalls))
            if recalls[index] != recalls[index - 1]
        )
    return {
        "detection_count": len(rows),
        "ground_truth_count": ground_truth_count,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "precision": _safe_div(true_positives, len(rows)),
        "recall": _safe_div(true_positives, ground_truth_count),
        "average_precision": ap,
        "curve": curve,
    }


def box_iou(first: dict[str, float], second: dict[str, float]) -> float:
    """Intersection over union for two boxes in the same coordinate space."""

    required = {"x_min", "y_min", "x_max", "y_max"}
    if not required <= first.keys() or not required <= second.keys():
        raise ValueError("boxes require x_min, y_min, x_max, and y_max")
    for box in (first, second):
        if box["x_max"] <= box["x_min"] or box["y_max"] <= box["y_min"]:
            raise ValueError("box maximums must be greater than minimums")
    x_min = max(float(first["x_min"]), float(second["x_min"]))
    y_min = max(float(first["y_min"]), float(second["y_min"]))
    x_max = min(float(first["x_max"]), float(second["x_max"]))
    y_max = min(float(first["y_max"]), float(second["y_max"]))
    intersection = max(0.0, x_max - x_min) * max(0.0, y_max - y_min)
    first_area = (float(first["x_max"]) - float(first["x_min"])) * (
        float(first["y_max"]) - float(first["y_min"])
    )
    second_area = (float(second["x_max"]) - float(second["x_min"])) * (
        float(second["y_max"]) - float(second["y_min"])
    )
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


def match_detections(
    detections: Iterable[dict[str, Any]],
    ground_truth: Iterable[dict[str, Any]],
    *,
    iou_threshold: float,
) -> list[dict[str, Any]]:
    """Greedily match ranked detections once per image, class, and truth box."""

    if not 0 < iou_threshold <= 1:
        raise ValueError("iou_threshold must be in (0, 1]")
    truth_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for truth in ground_truth:
        key = (str(truth["image_id"]), str(truth["class_name"]))
        truth_by_key.setdefault(key, []).append(dict(truth))
    matched: dict[tuple[str, str], set[int]] = {
        key: set() for key in truth_by_key
    }
    ranked = sorted(
        (dict(row) for row in detections),
        key=lambda row: (-float(row["score"]), str(row["image_id"])),
    )
    results: list[dict[str, Any]] = []
    for detection in ranked:
        key = (str(detection["image_id"]), str(detection["class_name"]))
        candidates = truth_by_key.get(key, [])
        best_index: int | None = None
        best_iou = 0.0
        for index, truth in enumerate(candidates):
            if index in matched.get(key, set()):
                continue
            iou = box_iou(detection["bbox"], truth["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_index = index
        is_true_positive = best_index is not None and best_iou >= iou_threshold
        if is_true_positive:
            matched.setdefault(key, set()).add(best_index)
        results.append(
            {
                **detection,
                "is_true_positive": is_true_positive,
                "matched_iou": best_iou,
            }
        )
    return results


def pest_detection_metrics(
    detections: Iterable[dict[str, Any]],
    ground_truth: Iterable[dict[str, Any]],
    *,
    classes: Iterable[str],
    evaluated_image_ids: Iterable[str],
    iou_thresholds: Iterable[float] = tuple(
        index / 100 for index in range(50, 100, 5)
    ),
    minimum_ground_truth: int = 20,
) -> dict[str, Any]:
    """Compute per-class AP50/AP50:95 and mAP after one-to-one box matching.

    Prediction/truth coordinates must use the same EXIF-corrected image space.
    Classes below `minimum_ground_truth` are `not_testable` and excluded from mAP.
    """

    detections_list = [dict(row) for row in detections]
    truth_list = [dict(row) for row in ground_truth]
    image_ids = {str(value) for value in evaluated_image_ids}
    thresholds = sorted({round(float(value), 2) for value in iou_thresholds})
    if not thresholds or any(value <= 0 or value > 1 for value in thresholds):
        raise ValueError("IoU thresholds must be in (0, 1]")

    per_class: dict[str, dict[str, Any]] = {}
    map50_values: list[float] = []
    map_values: list[float] = []
    for label in classes:
        class_truth = [
            row for row in truth_list if str(row["class_name"]) == label
        ]
        class_detections = [
            row for row in detections_list if str(row["class_name"]) == label
        ]
        gt_count = len(class_truth)
        positive_images = {str(row["image_id"]) for row in class_truth}
        negative_images = image_ids - positive_images
        false_detections_on_negatives = sum(
            str(row["image_id"]) in negative_images for row in class_detections
        )
        false_positive_rate = _safe_div(
            false_detections_on_negatives, len(negative_images)
        )
        if gt_count < minimum_ground_truth:
            per_class[label] = {
                "state": "not_testable",
                "ground_truth_count": gt_count,
                "minimum_required": minimum_ground_truth,
                "detection_count": len(class_detections),
                "negative_image_count": len(negative_images),
                "false_detections_per_negative_image": false_positive_rate,
            }
            continue

        by_iou: dict[str, dict[str, Any]] = {}
        ap_values: list[float] = []
        for threshold in thresholds:
            matched = match_detections(
                class_detections, class_truth, iou_threshold=threshold
            )
            metric = detection_precision_recall(matched, gt_count)
            metric.pop("curve", None)
            by_iou[f"{threshold:.2f}"] = metric
            if metric["average_precision"] is not None:
                ap_values.append(float(metric["average_precision"]))
        metric_50 = by_iou.get("0.50")
        ap50 = (
            float(metric_50["average_precision"])
            if metric_50 and metric_50["average_precision"] is not None
            else None
        )
        ap50_95 = sum(ap_values) / len(ap_values) if ap_values else None
        precision = metric_50["precision"] if metric_50 else None
        recall = metric_50["recall"] if metric_50 else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else 0.0
        )
        per_class[label] = {
            "state": "tested",
            "ground_truth_count": gt_count,
            "detection_count": len(class_detections),
            "precision_at_iou_0.50": precision,
            "recall_at_iou_0.50": recall,
            "f1_at_iou_0.50": f1,
            "ap_0.50": ap50,
            "ap_0.50_0.95": ap50_95,
            "by_iou": by_iou,
            "negative_image_count": len(negative_images),
            "false_detections_per_negative_image": false_positive_rate,
        }
        if ap50 is not None:
            map50_values.append(ap50)
        if ap50_95 is not None:
            map_values.append(ap50_95)

    return {
        "per_class": per_class,
        "map_0.50": sum(map50_values) / len(map50_values)
        if map50_values
        else None,
        "map_0.50_0.95": sum(map_values) / len(map_values) if map_values else None,
        "tested_class_count": len(map_values),
        "iou_thresholds": thresholds,
    }


def presence_metrics(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compute pest presence/absence metrics when box counts are insufficient."""

    counts = Counter(
        (bool(row["present"]), bool(row["detected"])) for row in rows
    )
    tp = counts[(True, True)]
    tn = counts[(False, False)]
    fp = counts[(False, True)]
    fn = counts[(True, False)]
    total = tp + tn + fp + fn
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "count": total,
        "accuracy": _safe_div(tp + tn, total),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }

