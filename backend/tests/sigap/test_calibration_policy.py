"""TUAI Sigap calibration-policy tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.sigap.calibration import Calibration, DiseaseThreshold
from app.sigap.constants import (
    DISEASE_CLASSES,
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
    DISEASE_RAW_LABELS,
    PEST_CLASSES,
    PEST_MODEL_REVISION,
    PEST_PREPROCESSING_VERSION,
)
from app.sigap.models.base import DiseaseInference, DiseasePrediction
from app.sigap.models.disease import _canonical_class
from app.sigap.policy import disease_decision
from app.sigap.recommendations import for_class
from app.sigap.schemas import BilingualText


def test_every_model_output_maps_to_a_known_class():
    assert len(DISEASE_RAW_LABELS) == 17
    assert all(_canonical_class(label) for label in DISEASE_RAW_LABELS)
    assert _canonical_class("Leaf Blast") == _canonical_class("Neck Blast") == "blast"


def test_only_the_five_measured_classes_can_become_named_results():
    named = {key for key, value in DISEASE_CLASSES.items() if value["result"]}
    assert named == {"bacterial_leaf_blight", "blast", "brown_spot", "healthy", "tungro"}


def _inference(class_id: str, score: float, stable: bool = True) -> DiseaseInference:
    return DiseaseInference(
        predictions=[
            DiseasePrediction(class_id=class_id, score=score),
            DiseasePrediction(class_id="sheath_rot", score=1 - score),
        ],
        view_count=2,
        top_class_agreement=1.0 if stable else 0.5,
        top_score_spread=0.01,
        stable=stable,
    )


def _thresholds() -> Calibration:
    keys = {key for key, value in DISEASE_CLASSES.items() if value["result"]}
    return Calibration(disease={key: DiseaseThreshold(0.75, 0.4) for key in keys}, pest={})


def test_unmeasured_class_stays_uncertain_even_at_a_high_score():
    status, result, *_ = disease_decision(_inference("hispa", 0.99), _thresholds())
    assert status == "abstain"
    assert result.closest_match is None


def test_low_score_gets_closest_match_but_no_named_result():
    status, result, *_ = disease_decision(_inference("tungro", 0.5), _thresholds())
    assert status == "abstain"
    assert result.closest_match is not None


def test_uncertain_result_never_hints_that_the_leaf_is_healthy():
    status, result, *_ = disease_decision(_inference("healthy", 0.6), _thresholds())
    assert status == "abstain"
    assert result.closest_match is None


def test_views_that_disagree_stay_uncertain():
    status, *_ = disease_decision(_inference("tungro", 0.9, stable=False), _thresholds())
    assert status == "abstain"


def test_no_recommendation_names_a_pesticide_product_or_dose():
    forbidden = ("iprodione", "propiconazole", "azoxystrobin", "carbendazim", "ml/", "gram/", "liter")
    for key, _value in {**DISEASE_CLASSES}.items():
        entry = for_class(key, BilingualText(id=key, en=key))
        if entry is None:
            continue
        text = " ".join(step.id + step.en for step in entry.steps).lower()
        assert not any(word in text for word in forbidden), key


def test_every_named_class_and_pest_has_sourced_guidance():
    for key in ("bacterial_leaf_blight", "blast", "brown_spot", "tungro"):
        assert for_class(key, BilingualText(id=key, en=key)) is not None
    for metadata in PEST_CLASSES.values():
        key = str(metadata["key"])
        assert for_class(key, BilingualText(id=key, en=key)) is not None


def test_shipped_thresholds_load_and_match_the_runtime():
    shipped = Path(__file__).resolve().parents[3] / "cv-prototype/evaluation/operating-thresholds.json"
    calibration = Calibration.load(shipped)
    assert calibration.error is None
    assert calibration.status == "operating"
    assert len(calibration.disease) == 5
    assert len(calibration.pest_remote) == 6


def test_calibration_loader_requires_frozen_revision_and_manifest(tmp_path):
    path = tmp_path / "thresholds.json"
    path.write_text(
        json.dumps(
            {
                "status": "frozen",
                "disease_model_revision": DISEASE_MODEL_REVISION,
                "pest_model_revision": PEST_MODEL_REVISION,
                "disease_preprocessing_version": DISEASE_PREPROCESSING_VERSION,
                "pest_preprocessing_version": PEST_PREPROCESSING_VERSION,
                "calibration_manifest_sha256": "a" * 64,
                "disease": {
                    "blast": {
                        "status": "validated",
                        "min_score": 0.7,
                        "min_margin": 0.2,
                    },
                    "brown_spot": {"status": "not_testable"},
                },
                "pest": {
                    "brown_plant_hopper": {
                        "status": "validated",
                        "min_score": 0.6,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    calibration = Calibration.load(path)
    assert calibration.status == "partial"
    assert calibration.disease["blast"].min_margin == 0.2
    assert calibration.pest[7].min_score == 0.6

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["disease_model_revision"] = "0" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    invalid = Calibration.load(path)
    assert invalid.status == "unavailable"
    assert "revision" in (invalid.error or "")

