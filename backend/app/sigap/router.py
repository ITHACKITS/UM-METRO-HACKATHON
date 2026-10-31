"""Versioned FastAPI router for TUAI Sigap visual observations."""

from __future__ import annotations

import asyncio
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, UploadFile
from starlette.formparsers import MultiPartParser

from .constants import MAX_COMPRESSED_BYTES
from .image_io import decode_image
from .schemas import (
    AnalyzeResponse,
    CapabilitiesResponse,
    ErrorResponse,
    HealthResponse,
)
from .service import InferenceService
from .settings import Settings

# Accepted photos remain in RAM instead of Starlette's default 1 MiB disk spool.
# The endpoint still reads only MAX_COMPRESSED_BYTES + 1 and the deployment must
# also enforce a request-body limit before multipart parsing.
MultiPartParser.spool_max_size = MAX_COMPRESSED_BYTES + 1
MultiPartParser.max_part_size = MAX_COMPRESSED_BYTES + 1


async def _run_in_executor(executor, operation, *args):
    """Run native model work while keeping request cancellation responsive."""
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(executor, operation, *args)
    while not future.done():
        await asyncio.sleep(0.025)
    return future.result()


def create_router(service: InferenceService) -> APIRouter:
    """Build the integrated router around one injectable inference service."""
    api = APIRouter(prefix="/api/sigap/v1", tags=["TUAI Sigap"])

    @api.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return service.health()

    @api.get("/capabilities", response_model=CapabilitiesResponse)
    async def capabilities() -> CapabilitiesResponse:
        return service.capabilities()

    @api.post(
        "/analyze",
        response_model=AnalyzeResponse,
        responses={
            413: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def analyze(
        mode: Annotated[Literal["disease", "pest"], Form()],
        file: Annotated[UploadFile, File()],
        live: Annotated[bool, Form()] = False,
    ) -> AnalyzeResponse:
        try:
            payload = await file.read(MAX_COMPRESSED_BYTES + 1)
        finally:
            await file.close()
        decoded = decode_image(payload)
        if mode == "disease":
            return await _run_in_executor(
                service.executor,
                service.analyze_disease,
                decoded,
            )
        return await _run_in_executor(
            service.executor,
            service.analyze_pest,
            decoded,
            live,
        )

    return api


settings = Settings.from_env()
inference_service = InferenceService(settings)
router = create_router(inference_service)


async def preload() -> None:
    """Optionally warm the frozen models without preventing health inspection."""
    if not settings.preload:
        return
    try:
        await _run_in_executor(inference_service.executor, inference_service.preload)
    except Exception:
        # Per-model readiness and the sanitized error remain visible on /health.
        pass


def close() -> None:
    inference_service.close()
