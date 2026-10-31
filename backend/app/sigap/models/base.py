"""Shared TUAI Sigap model adapter contracts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from ..schemas import BoundingBox, ModelHealth, ModelProvenance


class ModelUnavailableError(RuntimeError):
    """Raised when a prepared model or its runtime dependency is unavailable."""


class ModelInferenceError(RuntimeError):
    """Raised when a prepared model cannot produce a valid output."""


@dataclass(frozen=True, slots=True)
class DiseasePrediction:
    class_id: str
    score: float


@dataclass(frozen=True, slots=True)
class DiseaseInference:
    predictions: list[DiseasePrediction]
    view_count: int
    top_class_agreement: float
    top_score_spread: float
    stable: bool


@dataclass(frozen=True, slots=True)
class PestPrediction:
    class_id: int
    score: float
    bbox: BoundingBox


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ModelAdapter:
    mode: str
    model_id: str
    revision: str
    preprocessing_version: str

    def health(self) -> ModelHealth:  # pragma: no cover - abstract contract
        raise NotImplementedError

    def provenance(self) -> ModelProvenance:  # pragma: no cover - abstract contract
        raise NotImplementedError

    def load(self) -> None:  # pragma: no cover - abstract contract
        raise NotImplementedError

