"""Integrated TUAI Sigap API tests."""

from __future__ import annotations

import io
from contextlib import asynccontextmanager

import httpx
import pytest
from conftest import image_bytes
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from PIL import Image
from starlette.formparsers import MultiPartParser

from app.sigap.calibration import Calibration, DiseaseThreshold, PestThreshold
from app.sigap.constants import MAX_COMPRESSED_BYTES
from app.sigap.errors import APIError, api_error_handler, validation_error_handler
from app.sigap.router import create_router
from app.sigap.service import InferenceService


def app_for(service: InferenceService) -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(create_router(service))
    return app


@asynccontextmanager
async def client_for(settings, disease_adapter, pest_adapter, calibration=None):
    service = InferenceService(
        settings,
        disease_adapter=disease_adapter,
        pest_adapter=pest_adapter,
        calibration=calibration or Calibration.unavailable(),
    )
    transport = httpx.ASGITransport(app=app_for(service))
    try:
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client
    finally:
        service.close()


@pytest.mark.anyio
async def test_health_and_capabilities(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        health = await client.get("/api/sigap/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ready"
        assert health.json()["offline"] is True
        assert {item["mode"] for item in health.json()["models"]} == {"disease", "pest"}

        capabilities = await client.get("/api/sigap/v1/capabilities")
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert [mode["mode"] for mode in body["modes"]] == ["disease", "pest"]
        assert len(body["modes"][0]["classes"]) == 5
        assert len(body["modes"][1]["classes"]) == 3
        assert body["input_limits"]["max_compressed_bytes"] == MAX_COMPRESSED_BYTES


@pytest.mark.anyio
async def test_missing_real_models_report_degraded(settings):
    service = InferenceService(settings)
    transport = httpx.ASGITransport(app=app_for(service))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            body = (await client.get("/api/sigap/v1/health")).json()
    finally:
        service.close()
    assert body["status"] == "degraded"
    assert all(model["state"] == "unavailable" for model in body["models"])


@pytest.mark.anyio
async def test_disease_abstains_without_local_calibration(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        response = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("leaf.jpg", image_bytes(), "image/jpeg")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "abstain"
    assert body["score_kind"] == "model_score"
    assert body["disease"]["accepted"] is False
    assert [item["class_id"] for item in body["disease"]["candidates"]] == [
        "blast",
        "brown_spot",
        "tungro",
    ]
    assert body["model"]["revision"]
    assert disease_adapter.calls == 1
    assert body["disease"]["consistency_status"] == "stable"
    assert body["disease"]["view_count"] == 3


@pytest.mark.anyio
async def test_disease_requires_explicit_closeup_leaf_confirmation(
    settings, disease_adapter, pest_adapter
):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        response = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease"},
            files={"file": ("field.jpg", image_bytes(), "image/jpeg")},
        )
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "retake"
    assert body["disease"]["candidates"] == []
    assert body["quality"]["rejection_reason"] is not None
    assert disease_adapter.calls == 0


@pytest.mark.anyio
async def test_unstable_multiview_result_cannot_be_accepted(
    settings, disease_adapter, pest_adapter
):
    disease_adapter.stable = False
    disease_adapter.top_class_agreement = 2 / 3
    disease_adapter.top_score_spread = 0.42
    calibration = Calibration(
        disease={"blast": DiseaseThreshold(min_score=0.7, min_margin=0.5)}, pest={}
    )
    async with client_for(settings, disease_adapter, pest_adapter, calibration) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("leaf.jpg", image_bytes(), "image/jpeg")},
        )).json()
    assert body["status"] == "abstain"
    assert body["disease"]["accepted"] is False
    assert body["disease"]["consistency_status"] == "unstable"


@pytest.mark.anyio
async def test_disease_accepts_only_frozen_class_threshold(settings, disease_adapter, pest_adapter):
    calibration = Calibration(
        disease={"blast": DiseaseThreshold(min_score=0.7, min_margin=0.5)}, pest={}
    )
    async with client_for(settings, disease_adapter, pest_adapter, calibration) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("leaf.jpg", image_bytes(), "application/octet-stream")},
        )).json()
    assert body["status"] == "ok"
    assert body["disease"]["accepted"] is True
    assert body["disease"]["calibration_status"] == "partial"


@pytest.mark.anyio
async def test_pest_boxes_are_candidates_until_calibrated(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "pest"},
            files={"file": ("pest.webp", image_bytes(image_format="WEBP"), "image/webp")},
        )).json()
    assert body["status"] == "abstain"
    assert body["pest"]["detections"][0]["class_id"] == 7
    assert body["pest"]["detections"][0]["accepted"] is False
    assert body["pest"]["image_width"] == 640


@pytest.mark.anyio
async def test_pest_validated_positive_can_be_accepted(settings, disease_adapter, pest_adapter):
    calibration = Calibration(
        disease={},
        pest={
            0: PestThreshold(0.5),
            4: PestThreshold(0.5),
            7: PestThreshold(0.7),
        },
    )
    async with client_for(settings, disease_adapter, pest_adapter, calibration) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "pest"},
            files={"file": ("pest.png", image_bytes(image_format="PNG"), "image/png")},
        )).json()
    assert body["status"] == "ok"
    assert body["pest"]["detections"][0]["accepted"] is True


@pytest.mark.anyio
async def test_low_resolution_returns_retake_without_inference(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("small.jpg", image_bytes((180, 300)), "image/jpeg")},
        )).json()
    assert body["status"] == "retake"
    assert body["quality"]["rejection_reason"] is not None
    assert body["disease"]["candidates"] == []
    assert disease_adapter.calls == 0


@pytest.mark.anyio
async def test_exif_orientation_is_applied(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        body = (await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={
                "file": (
                    "rotated.jpg",
                    image_bytes((300, 500), exif_orientation=6),
                    "image/jpeg",
                )
            },
        )).json()
    assert body["quality"]["width"] == 500
    assert body["quality"]["height"] == 300


@pytest.mark.anyio
async def test_corrupt_empty_and_unsupported_files_have_explicit_errors(
    settings, disease_adapter, pest_adapter
):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        corrupt = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("bad.jpg", b"not an image", "image/jpeg")},
        )
        empty = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("empty.jpg", b"", "image/jpeg")},
        )
        gif = io.BytesIO()
        Image.new("RGB", (300, 300), (20, 80, 20)).save(gif, format="GIF")
        unsupported = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease", "confirm_leaf_subject": "true"},
            files={"file": ("leaf.jpg", gif.getvalue(), "image/jpeg")},
        )
    assert corrupt.status_code == 422
    assert corrupt.json()["detail"]["code"] == "decode_failed"
    assert empty.status_code == 422
    assert empty.json()["detail"]["code"] == "empty_file"
    assert unsupported.status_code == 415
    assert unsupported.json()["detail"]["code"] == "unsupported_format"


@pytest.mark.anyio
async def test_oversized_compressed_and_decoded_inputs_are_rejected(
    settings, disease_adapter, pest_adapter
):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        compressed = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease"},
            files={"file": ("large.jpg", b"x" * (MAX_COMPRESSED_BYTES + 1), "image/jpeg")},
        )

        bomb_buffer = io.BytesIO()
        Image.new("1", (5001, 5000), 1).save(bomb_buffer, format="PNG")
        decoded = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "disease"},
            files={"file": ("large.png", bomb_buffer.getvalue(), "image/png")},
        )
    assert compressed.status_code == 413
    assert compressed.json()["detail"]["code"] == "file_too_large"
    assert decoded.status_code == 413
    assert decoded.json()["detail"]["code"] == "decoded_image_too_large"


@pytest.mark.anyio
async def test_invalid_mode_and_model_absence(settings, disease_adapter, pest_adapter):
    async with client_for(settings, disease_adapter, pest_adapter) as client:
        invalid = await client.post(
            "/api/sigap/v1/analyze",
            data={"mode": "other"},
            files={"file": ("leaf.jpg", image_bytes(), "image/jpeg")},
        )
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "invalid_request"

    service = InferenceService(settings)
    transport = httpx.ASGITransport(app=app_for(service))
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            unavailable = await client.post(
                "/api/sigap/v1/analyze",
                data={"mode": "disease", "confirm_leaf_subject": "true"},
                files={"file": ("leaf.jpg", image_bytes(), "image/jpeg")},
            )
    finally:
        service.close()
    assert unavailable.status_code == 503
    assert unavailable.json()["detail"]["code"] == "model_unavailable"


def test_accepted_uploads_remain_in_memory():
    assert MultiPartParser.spool_max_size > MAX_COMPRESSED_BYTES

