"""TUAI Sigap backend test fixtures."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import pytest
from PIL import Image

from app.sigap.constants import (
    DISEASE_MODEL_ID,
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
    PEST_MODEL_ID,
    PEST_MODEL_REVISION,
    PEST_PREPROCESSING_VERSION,
)
from app.sigap.models.base import DiseaseInference, DiseasePrediction, PestPrediction
from app.sigap.schemas import BoundingBox, ModelHealth, ModelProvenance
from app.sigap.settings import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        prototype_root=tmp_path,
        model_dir=tmp_path / ".models",
        disease_dir=tmp_path / ".models" / "disease",
        pest_onnx=tmp_path / ".models" / "pest" / "model.onnx",
        calibration_path=tmp_path / "frozen-thresholds.json",
        offline=True,
        device="cpu",
        preload=False,
        max_concurrency=1,
    )


@pytest.fixture
def anyio_backend():
    return "asyncio"


def image_bytes(
    size: tuple[int, int] = (640, 640),
    image_format: str = "JPEG",
    color: tuple[int, int, int] = (80, 150, 65),
    exif_orientation: int | None = None,
) -> bytes:
    image = Image.new("RGB", size, color)
    # Add high-luminance-contrast edges so JPEG conversion cannot collapse the
    # fixture into a visually blank grayscale image.
    for x in range(0, size[0], max(1, size[0] // 12)):
        for y in range(size[1]):
            image.putpixel((x, y), (245, 245, 235))
    buffer = io.BytesIO()
    kwargs = {}
    if exif_orientation is not None and image_format == "JPEG":
        exif = Image.Exif()
        exif[274] = exif_orientation
        kwargs["exif"] = exif
    image.save(buffer, format=image_format, **kwargs)
    return buffer.getvalue()


@dataclass
class FakeDiseaseAdapter:
    predictions: list[DiseasePrediction]
    calls: int = 0
    mode: str = "disease"
    stable: bool = True
    top_class_agreement: float = 1.0
    top_score_spread: float = 0.04

    def load(self) -> None:
        return None

    def provenance(self) -> ModelProvenance:
        return ModelProvenance(
            id=DISEASE_MODEL_ID,
            revision=DISEASE_MODEL_REVISION,
            artifact_sha256="d" * 64,
            preprocessing_version=DISEASE_PREPROCESSING_VERSION,
        )

    def health(self) -> ModelHealth:
        return ModelHealth(
            mode="disease",
            id=DISEASE_MODEL_ID,
            revision=DISEASE_MODEL_REVISION,
            state="ready",
            ready=True,
            loaded=True,
            artifact_sha256="d" * 64,
            error=None,
        )

    def predict(self, _image: Image.Image) -> DiseaseInference:
        self.calls += 1
        return DiseaseInference(
            predictions=self.predictions,
            view_count=3,
            top_class_agreement=self.top_class_agreement,
            top_score_spread=self.top_score_spread,
            stable=self.stable,
        )


@dataclass
class FakePestAdapter:
    predictions: list[PestPrediction]
    calls: int = 0
    mode: str = "pest"

    def load(self) -> None:
        return None

    def provenance(self) -> ModelProvenance:
        return ModelProvenance(
            id=PEST_MODEL_ID,
            revision=PEST_MODEL_REVISION,
            artifact_sha256="e" * 64,
            preprocessing_version=PEST_PREPROCESSING_VERSION,
        )

    def health(self) -> ModelHealth:
        return ModelHealth(
            mode="pest",
            id=PEST_MODEL_ID,
            revision=PEST_MODEL_REVISION,
            state="ready",
            ready=True,
            loaded=True,
            artifact_sha256="e" * 64,
            error=None,
        )

    def predict(self, _image: Image.Image) -> list[PestPrediction]:
        self.calls += 1
        return self.predictions


@pytest.fixture
def disease_adapter() -> FakeDiseaseAdapter:
    return FakeDiseaseAdapter(
        predictions=[
            DiseasePrediction("blast", 0.72),
            DiseasePrediction("brown_spot", 0.15),
            DiseasePrediction("tungro", 0.07),
            DiseasePrediction("bacterial_leaf_blight", 0.04),
            DiseasePrediction("healthy", 0.02),
        ]
    )


@pytest.fixture
def pest_adapter() -> FakePestAdapter:
    return FakePestAdapter(
        predictions=[
            PestPrediction(
                class_id=7,
                score=0.76,
                bbox=BoundingBox(x_min=100, y_min=110, x_max=240, y_max=280),
            )
        ]
    )

