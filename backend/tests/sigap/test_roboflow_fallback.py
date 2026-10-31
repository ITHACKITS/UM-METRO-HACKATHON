"""Roboflow-first detection and silent local fallback tests."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass

import httpx
import pytest
from conftest import FakePestAdapter, image_bytes
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from PIL import Image

from app.sigap.calibration import Calibration, PestThreshold
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


def test_remote_adapter_keeps_generic_stem_borer_separate() -> None:
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
    predictions = adapter.predict(Image.new("RGB", (640, 640), "green"))
    assert [item.class_id for item in predictions] == [102, 7, 0]


PLANTHOPPER = {
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


def service_with(settings, disease_adapter, local, remote) -> InferenceService:
    return InferenceService(
        settings,
        disease_adapter=disease_adapter,
        pest_adapter=local,
        roboflow_adapter=remote,
        calibration=Calibration(
            disease={},
            pest={7: PestThreshold(0.5)},
            pest_remote={7: PestThreshold(0.6)},
        ),
    )


async def post_pest(service: InferenceService, data: dict | None = None) -> httpx.Response:
    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(create_router(service))
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/sigap/v1/analyze",
                data={"mode": "pest", **(data or {})},
                files={"file": ("pest.jpg", image_bytes(), "image/jpeg")},
            )
    finally:
        service.close()


@pytest.mark.anyio
async def test_photo_goes_to_roboflow_first(settings, disease_adapter, pest_adapter) -> None:
    service = service_with(settings, disease_adapter, pest_adapter, remote_adapter(PLANTHOPPER))
    response = await post_pest(service)
    body = response.json()
    assert response.status_code == 200
    assert body["processing"] == "roboflow_cloud"
    assert body["model"]["id"] == "roboflow/rice-pest-jmdev"
    assert body["pest"]["detections"][0]["accepted"] is True
    assert pest_adapter.calls == 0


@pytest.mark.anyio
async def test_roboflow_failure_falls_back_without_telling_the_user(
    settings, disease_adapter, pest_adapter
) -> None:
    def failing(url, **kwargs):
        raise httpx.ConnectError("offline")

    remote = remote_adapter(PLANTHOPPER)
    remote._sender = failing
    service = service_with(settings, disease_adapter, pest_adapter, remote)
    response = await post_pest(service)
    body = response.json()
    assert response.status_code == 200
    assert body["processing"] == "local"
    assert pest_adapter.calls == 1
    text = str(body["limitations"]) + str(body["next_action"]) + str(body["general_steps"])
    assert "roboflow" not in text.lower()
    assert "cloud" not in text.lower()


@pytest.mark.anyio
async def test_live_frames_stay_local_when_the_local_model_works(
    settings, disease_adapter, pest_adapter
) -> None:
    service = service_with(settings, disease_adapter, pest_adapter, remote_adapter(PLANTHOPPER))
    body = (await post_pest(service, {"live": "true"})).json()
    assert body["processing"] == "local"
    assert pest_adapter.calls == 1


@pytest.mark.anyio
async def test_both_detectors_failing_is_a_clean_503(settings, disease_adapter, pest_adapter) -> None:
    def failing(url, **kwargs):
        raise httpx.ConnectError("offline")

    local = MissingPestAdapter(predictions=pest_adapter.predictions)
    remote = remote_adapter(PLANTHOPPER)
    remote._sender = failing
    service = service_with(settings, disease_adapter, local, remote)
    response = await post_pest(service)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "model_unavailable"


def test_large_photos_are_shrunk_and_boxes_map_back_to_the_original() -> None:
    sizes: list[tuple[int, int]] = []

    def sender(url, **kwargs):
        decoded = Image.open(io.BytesIO(base64.b64decode(kwargs["content"])))
        sizes.append(decoded.size)
        return httpx.Response(
            200,
            json={
                "predictions": [
                    {"class": "rice-bug", "confidence": 0.9, "x": 640, "y": 360, "width": 128, "height": 72}
                ]
            },
            request=httpx.Request("POST", url),
        )

    adapter = remote_adapter({})
    adapter._sender = sender
    prediction = adapter.predict(Image.new("RGB", (2560, 1440), "green"))[0]
    assert sizes == [(1280, 720)]
    assert prediction.bbox.x_min == pytest.approx(1152)
    assert prediction.bbox.x_max == pytest.approx(1408)
