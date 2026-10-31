"""TUAI Sigap calibration-policy tests."""

from __future__ import annotations

import json

from app.sigap.calibration import Calibration
from app.sigap.constants import (
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
    PEST_MODEL_REVISION,
    PEST_PREPROCESSING_VERSION,
)
from app.sigap.models.disease import _canonical_class


def test_locked_disease_model_labels_map_to_canonical_contract():
    labels = ["Bacterialblight", "Blast", "Brownspot", "Healthy", "Tungro"]
    assert [_canonical_class(label) for label in labels] == [
        "bacterial_leaf_blight",
        "blast",
        "brown_spot",
        "healthy",
        "tungro",
    ]


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

