"""Real ONNX disease adapter checks; skipped when the prepared model is absent."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.sigap.models.disease import DiseaseAdapter, center_crop_box
from app.sigap.models.pest import PestAdapter

MODELS = Path(__file__).resolve().parents[3] / "cv-prototype" / ".models"


def test_center_crop_box_is_the_centered_square():
    assert center_crop_box(1000, 800) == (150.0, 50.0, 850.0, 750.0)


@pytest.mark.skipif(not (MODELS / "disease-efficientnet/model.onnx").is_file(), reason="model absent")
def test_real_model_returns_scores_and_a_highlight_inside_the_photo():
    image = Image.new("RGB", (640, 480), (70, 130, 60))
    ImageDraw.Draw(image).ellipse((280, 200, 360, 280), fill=(120, 70, 40))
    result = DiseaseAdapter(MODELS / "disease-efficientnet").predict(image)
    assert sum(item.score for item in result.predictions) == pytest.approx(1.0, abs=1e-3)
    assert result.view_count == 2
    assert result.heatmap is not None
    assert len(result.heatmap.grid) == 7
    assert max(max(row) for row in result.heatmap.grid) == pytest.approx(1.0, abs=1e-3)
    assert result.heatmap.region.x_max <= 640


@pytest.mark.skipif(not (MODELS / "pest/model.onnx").is_file(), reason="model absent")
def test_real_pest_model_output_shape_decodes():
    assert isinstance(PestAdapter(MODELS / "pest/model.onnx").predict(Image.new("RGB", (800, 450), "green")), list)
