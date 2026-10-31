"""How TUAI Sigap turns model output into a named result or an honest "uncertain".

Thresholds come from cv-prototype/evaluation/operating-thresholds.json, and the report
cv-prototype/docs/reports/MODEL_TEST_2026-10-31.md records what they were measured on.
"""

from __future__ import annotations

from .calibration import Calibration, PestThreshold
from .constants import DISEASE_CLASSES, PEST_CLASSES, PEST_MIN_CANDIDATE_SCORE
from .models.base import DiseaseInference, PestPrediction
from .recommendations import (
    NO_PEST_STEPS,
    NO_SYMPTOM_STEPS,
    UNCERTAIN_STEPS,
    for_class,
)
from .schemas import (
    BilingualText,
    DiseaseCandidate,
    DiseaseResult,
    PestDetection,
    PestResult,
    Recommendation,
)

DISEASE_LIMITATIONS = [
    BilingualText(
        id="Perkiraan dari satu foto, bukan diagnosis. Pastikan langsung di sawah atau tanya PPL.",
        en="An estimate from one photo, not a diagnosis. Check in the field or ask an extension officer.",
    ),
]

PEST_LIMITATIONS = [
    BilingualText(
        id="Perkiraan dari satu foto. Hama yang tidak terlihat di foto tidak terhitung.",
        en="An estimate from one photo. Pests not visible in the photo are not counted.",
    ),
]

# Minimum score at which the closest class is worth mentioning next to "uncertain".
CLOSEST_MATCH_MIN_SCORE = 0.4


def _label(metadata: dict) -> BilingualText:
    return BilingualText(id=str(metadata["id"]), en=str(metadata["en"]))


def disease_decision(
    inference: DiseaseInference, calibration: Calibration
) -> tuple[str, DiseaseResult, list[BilingualText], BilingualText, list[Recommendation], list[BilingualText]]:
    predictions = inference.predictions
    top = predictions[:3]
    candidates = [
        DiseaseCandidate(
            class_id=item.class_id,
            label=_label(DISEASE_CLASSES[item.class_id]),
            score=round(item.score, 6),
        )
        for item in top
    ]
    top_score = top[0].score if top else None
    runner_up = top[1].score if len(top) > 1 else 0.0
    margin = max(0.0, top_score - runner_up) if top_score is not None else None
    top_class = top[0].class_id if top else None
    threshold = calibration.disease.get(top_class) if top_class else None
    accepted = bool(
        top_class
        and DISEASE_CLASSES[top_class]["result"]
        and threshold
        and top_score is not None
        and margin is not None
        and top_score >= threshold.min_score
        and margin >= threshold.min_margin
        and inference.stable
    )
    # "No symptom" is never offered as a hint: it must not reassure on an uncertain photo.
    closest_match = None
    if (
        not accepted
        and top_class
        and top_class != "healthy"
        and DISEASE_CLASSES[top_class]["result"]
        and top_score is not None
        and top_score >= CLOSEST_MATCH_MIN_SCORE
    ):
        closest_match = _label(DISEASE_CLASSES[top_class])
    # The highlight explains a disease result, so a "no symptom" result has none.
    show_heatmap = accepted and top_class != "healthy"
    result = DiseaseResult(
        accepted=accepted,
        candidates=candidates,
        top_score=round(top_score, 6) if top_score is not None else None,
        score_margin=round(margin, 6) if margin is not None else None,
        calibration_status=calibration.status,
        consistency_status="stable" if inference.stable else "unstable",
        view_count=inference.view_count,
        top_class_agreement=round(inference.top_class_agreement, 6),
        top_score_spread=round(inference.top_score_spread, 6),
        heatmap=inference.heatmap if show_heatmap else None,
        closest_match=closest_match,
    )
    recommendations: list[Recommendation] = []
    general: list[BilingualText] = []
    if accepted and top_class == "healthy":
        general = list(NO_SYMPTOM_STEPS)
        action = general[0]
    elif accepted and top_class:
        recommendation = for_class(top_class, _label(DISEASE_CLASSES[top_class]))
        if recommendation:
            recommendations.append(recommendation)
        action = recommendation.steps[0] if recommendation else UNCERTAIN_STEPS[1]
    else:
        general = list(UNCERTAIN_STEPS)
        action = general[0]
    return "ok" if accepted else "abstain", result, list(DISEASE_LIMITATIONS), action, recommendations, general


def pest_decision(
    predictions: list[PestPrediction],
    calibration: Calibration,
    image_width: int,
    image_height: int,
    thresholds: dict[int, PestThreshold] | None = None,
) -> tuple[str, PestResult, list[BilingualText], BilingualText, list[Recommendation], list[BilingualText]]:
    active = calibration.pest if thresholds is None else thresholds
    detections: list[PestDetection] = []
    for prediction in predictions:
        threshold = active.get(prediction.class_id)
        accepted = bool(threshold and prediction.score >= threshold.min_score)
        if not accepted and prediction.score < PEST_MIN_CANDIDATE_SCORE:
            continue
        metadata = PEST_CLASSES[prediction.class_id]
        detections.append(
            PestDetection(
                class_id=prediction.class_id,
                class_key=str(metadata["key"]),
                label=_label(metadata),
                score=round(prediction.score, 6),
                accepted=accepted,
                bbox=prediction.bbox,
            )
        )

    result = PestResult(
        detections=detections,
        image_width=image_width,
        image_height=image_height,
        calibration_status=calibration.status,
    )
    recommendations: list[Recommendation] = []
    for detection in detections:
        if detection.accepted and all(
            item.label != detection.label for item in recommendations
        ):
            recommendation = for_class(detection.class_key, detection.label)
            if recommendation:
                recommendations.append(recommendation)

    general: list[BilingualText] = []
    if recommendations:
        status = "ok"
        action = recommendations[0].steps[0]
    elif detections:
        status = "abstain"
        general = list(UNCERTAIN_STEPS)
        action = general[0]
    else:
        # Nothing to name is still a usable outcome when thresholds exist; the steps
        # tell the user how to look, because one photo cannot show the base of a hill.
        status = "ok" if active else "abstain"
        general = list(NO_PEST_STEPS)
        action = general[0]
    return status, result, list(PEST_LIMITATIONS), action, recommendations, general
