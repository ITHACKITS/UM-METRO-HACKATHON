"""Threshold calibration loading for TUAI Sigap."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .constants import (
    DISEASE_CLASSES,
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
    PEST_CLASSES,
    PEST_MODEL_REVISION,
    PEST_PREPROCESSING_VERSION,
)

CalibrationStatus = Literal["unavailable", "partial", "frozen"]


@dataclass(frozen=True, slots=True)
class DiseaseThreshold:
    min_score: float
    min_margin: float


@dataclass(frozen=True, slots=True)
class PestThreshold:
    min_score: float


@dataclass(slots=True)
class Calibration:
    disease: dict[str, DiseaseThreshold]
    pest: dict[int, PestThreshold]
    error: str | None = None

    @property
    def status(self) -> CalibrationStatus:
        count = len(self.disease) + len(self.pest)
        total = len(DISEASE_CLASSES) + len(PEST_CLASSES)
        if count == 0:
            return "unavailable"
        return "frozen" if count == total else "partial"

    @classmethod
    def unavailable(cls, error: str | None = None) -> Calibration:
        return cls(disease={}, pest={}, error=error)

    @classmethod
    def load(cls, path: Path) -> Calibration:
        if not path.is_file():
            return cls.unavailable()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("status") != "frozen":
                raise ValueError("threshold file status must be 'frozen'")
            if raw.get("disease_model_revision") != DISEASE_MODEL_REVISION:
                raise ValueError("disease revision does not match the locked model")
            if raw.get("pest_model_revision") != PEST_MODEL_REVISION:
                raise ValueError("pest revision does not match the locked model")
            if raw.get("disease_preprocessing_version") != DISEASE_PREPROCESSING_VERSION:
                raise ValueError("disease preprocessing does not match the runtime")
            if raw.get("pest_preprocessing_version") != PEST_PREPROCESSING_VERSION:
                raise ValueError("pest preprocessing does not match the runtime")
            if not raw.get("calibration_manifest_sha256"):
                raise ValueError("calibration manifest hash is required")

            disease: dict[str, DiseaseThreshold] = {}
            for class_id, values in raw.get("disease", {}).items():
                if class_id not in DISEASE_CLASSES or values.get("status") != "validated":
                    continue
                min_score = float(values["min_score"])
                min_margin = float(values["min_margin"])
                if not (0 <= min_score <= 1 and 0 <= min_margin <= 1):
                    raise ValueError(f"invalid disease threshold for {class_id}")
                disease[class_id] = DiseaseThreshold(min_score, min_margin)

            pest: dict[int, PestThreshold] = {}
            pest_keys = {metadata["key"]: index for index, metadata in PEST_CLASSES.items()}
            for class_key, values in raw.get("pest", {}).items():
                if class_key not in pest_keys or values.get("status") != "validated":
                    continue
                min_score = float(values["min_score"])
                if not 0 <= min_score <= 1:
                    raise ValueError(f"invalid pest threshold for {class_key}")
                pest[pest_keys[class_key]] = PestThreshold(min_score)
            return cls(disease=disease, pest=pest)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            return cls.unavailable(error=f"Invalid calibration file: {exc}")

