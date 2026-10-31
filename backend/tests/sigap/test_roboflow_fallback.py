"""Roboflow fallback contract and consent tests."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest
from conftest import FakePestAdapter, image_bytes
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.sigap.calibration import Calibration
from app.sigap.errors import APIError, api_error_handler, validation_error_handler
from app.sigap.models.base import ModelUnavailableError
from app.sigap.models.roboflow_pest import RoboflowPestAdapter
from app.sigap.router import create_router
from app.sigap.service import InferenceService


def remote_adapter(payload: dict) -> RoboflowPestAdapter:
    def sender(url, **kwargs):
        assert url == "https://serverless.roboflow.com/rice-pest-jmdev/1"
        assert kwargs["headers"]["Authorization"] == "Bearer test-secret"
        assert "test-secret" not in url
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    return RoboflowPestAdapter(
        enabled=True,
        api_url="https://serverless.roboflow.com",
        api_key="test-secret",
        remote_model_id="rice-pest-jmdev/1",
        timeout_seconds=5,
        sender=sender,
    )


@dataclass
class MissingPestAdapter(FakePestAdapter):
    def predict(self, _image):
        raise ModelUnavailableError("local ONNX absent")

    def health(self):
        health = super().health()
        return health.model_copy(
            update={
                "state": "unavailable",
                "ready": False,
                "loaded": False,
                "artifact_sha256": None,
                "error": "Prepared pest ONNX artifact is absent.",
            }
        )


def test_remote_adapter_maps_only_semantically_compatible_classes() -> None:
    adapter = remote_adapter(
        {
            "predictions": [
                {
                    "class": "brown-planthopper",
                    "confidence": 0.91,
                    "x": 120,
                    "y": 140,
                    "width": 80,
                    "height": 100,
                },
                {
                    "class": "leaf-folder",
                    "confidence": 0.82,
                    "x": 300,
                    "y": 320,
                    "width": 70,
                    "height": 60,
                },
                {
                    "class": "stem-borer",
                    "confidence": 0.99,
                    "x": 400,
                    "y": 400,
                    "width": 50,
                    "height": 50,
                },
            ]
        }
    )
    from PIL import Image

    predictions = adapter.predict(Image.new("RGB", (640, 640), "green"))
    assert [item.class_id for item in predictions] == [7, 0]


@pytest.mark.anyio
async def test_remote_fallback_requires_explicit_request_consent(
    settings, disease_adapter, pest_adapter
) -> None:
    local = MissingPestAdapter(predictions=pest_adapter.predictions)
    remote = remote_adapter(
        {
            "predictions": [
                {
                    "class": "brown-planthopper",
                    "confidence": 0.91,
                    "x": 120,
                    "y": 140,
                    "width": 80,
                    "height": 100,
                }
            ]
        }
    )
    service = InferenceService(
        settings,
        disease_adapter=disease_adapter,
        pest_adapter=local,
        roboflow_adapter=remote,
        calibration=Calibration.unavailable(),
    )
    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(create_router(service))
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            without_consent = await client.post(
                "/api/sigap/v1/analyze",
                data={"mode": "pest"},
                files={"file": ("pest.jpg", image_bytes(), "image/jpeg")},
            )
            with_consent = await client.post(
                "/api/sigap/v1/analyze",
                data={"mode": "pest", "allow_remote_fallback": "true"},
                files={"file": ("pest.jpg", image_bytes(), "image/jpeg")},
            )
    finally:
        service.close()

    assert without_consent.status_code == 503
    assert without_consent.json()["detail"]["code"] == "remote_fallback_requires_consent"
    assert with_consent.status_code == 200
    body = with_consent.json()
    assert body["processing"] == "roboflow_cloud"
    assert body["model"]["id"] == "roboflow/rice-pest-jmdev"
    assert body["pest"]["detections"][0]["class_id"] == 7
