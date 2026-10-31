"""Safety-first abstention policy for TUAI Sigap."""

from __future__ import annotations

from .calibration import Calibration
from .constants import DISEASE_CLASSES, PEST_CLASSES
from .models.base import DiseaseInference, PestPrediction
from .schemas import (
    BilingualText,
    DiseaseCandidate,
    DiseaseResult,
    PestDetection,
    PestResult,
)

DISEASE_LIMITATIONS = [
    BilingualText(
        id="Hasil ini adalah indikasi model dari satu foto, bukan diagnosis lapangan.",
        en="This is a model indication from one photo, not a field diagnosis.",
    ),
    BilingualText(
        id="Model hanya mengenali empat penyakit target dan keluaran tanpa gejala target.",
        en="The model only recognizes four target diseases and a no-target-symptom output.",
    ),
]

PEST_LIMITATIONS = [
    BilingualText(
        id="Model hanya mencari tiga jenis hama yang tampak jelas pada foto.",
        en="The model only searches for three supported pests that are clearly visible.",
    ),
    BilingualText(
        id="Tidak ada deteksi bukan berarti tanaman aman atau bebas hama.",
        en="No detection does not mean the plant is safe or pest-free.",
    ),
]


def disease_decision(
    inference: DiseaseInference, calibration: Calibration
) -> tuple[str, DiseaseResult, list[BilingualText], BilingualText]:
    predictions = inference.predictions
    top = predictions[:3]
    candidates = [
        DiseaseCandidate(
            class_id=item.class_id,
            label=BilingualText(
                id=str(DISEASE_CLASSES[item.class_id]["id"]),
                en=str(DISEASE_CLASSES[item.class_id]["en"]),
            ),
            score=round(item.score, 6),
        )
        for item in top
    ]
    top_score = top[0].score if top else None
    runner_up = top[1].score if len(top) > 1 else 0.0
    margin = max(0.0, top_score - runner_up) if top_score is not None else None
    threshold = calibration.disease.get(top[0].class_id) if top else None
    accepted = bool(
        top
        and threshold
        and top_score is not None
        and margin is not None
        and top_score >= threshold.min_score
        and margin >= threshold.min_margin
        and inference.stable
    )
    status = "ok" if accepted else "abstain"
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
    )
    if accepted:
        action = BilingualText(
            id="Periksa daun lain dan konfirmasikan indikasi ini dengan PPL/agronomis sebelum bertindak.",
            en="Inspect other leaves and confirm this indication with an extension officer/agronomist before acting.",
        )
    else:
        action = BilingualText(
            id="Model belum dapat menerima hasil ini. Ambil ulang foto yang jelas atau hubungi PPL/agronomis.",
            en="The model cannot accept this result. Retake a clear photo or contact an extension officer/agronomist.",
        )
    limitations = list(DISEASE_LIMITATIONS)
    if threshold is None:
        limitations.append(
            BilingualText(
                id="Ambang kelas teratas belum divalidasi dengan foto lapangan lokal.",
                en="The top class threshold has not been validated on local field photos.",
            )
        )
    if not inference.stable:
        limitations.append(
            BilingualText(
                id="Hasil berubah antarpotongan foto, sehingga model menolak indikasi ini.",
                en="The result changed across image views, so the model rejected this indication.",
            )
        )
    return status, result, limitations, action


def pest_decision(
    predictions: list[PestPrediction],
    calibration: Calibration,
    image_width: int,
    image_height: int,
) -> tuple[str, PestResult, list[BilingualText], BilingualText]:
    detections: list[PestDetection] = []
    for prediction in predictions:
        metadata = PEST_CLASSES[prediction.class_id]
        threshold = calibration.pest.get(prediction.class_id)
        accepted = bool(threshold and prediction.score >= threshold.min_score)
        detections.append(
            PestDetection(
                class_id=prediction.class_id,
                class_key=str(metadata["key"]),
                label=BilingualText(id=str(metadata["id"]), en=str(metadata["en"])),
                score=round(prediction.score, 6),
                accepted=accepted,
                bbox=prediction.bbox,
            )
        )

    accepted_count = sum(item.accepted for item in detections)
    all_classes_validated = len(calibration.pest) == len(PEST_CLASSES)
    status = "ok" if accepted_count > 0 or all_classes_validated else "abstain"
    result = PestResult(
        detections=detections,
        image_width=image_width,
        image_height=image_height,
        calibration_status=calibration.status,
    )
    limitations = list(PEST_LIMITATIONS)
    if not all_classes_validated:
        limitations.append(
            BilingualText(
                id="Satu atau lebih ambang hama belum divalidasi dengan foto lapangan lokal.",
                en="One or more pest thresholds have not been validated on local field photos.",
            )
        )
    if accepted_count:
        action = BilingualText(
            id="Periksa objek dari dekat dan konfirmasikan indikasi dengan PPL/agronomis sebelum bertindak.",
            en="Inspect the object closely and confirm the indication with an extension officer/agronomist before acting.",
        )
    else:
        action = BilingualText(
            id="Jangan menyimpulkan tanaman aman. Ambil foto hama yang lebih dekat atau minta pemeriksaan PPL/agronomis.",
            en="Do not conclude the plant is safe. Take a closer pest photo or request an extension-officer/agronomist inspection.",
        )
    return status, result, limitations, action

