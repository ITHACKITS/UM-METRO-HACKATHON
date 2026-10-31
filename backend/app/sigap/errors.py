"""Sanitized TUAI Sigap API errors."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import BilingualText, ErrorDetail, ErrorResponse


class APIError(Exception):
    def __init__(
        self, status_code: int, code: str, message_id: str, message_en: str
    ) -> None:
        super().__init__(message_en)
        self.status_code = status_code
        self.detail = ErrorDetail(
            code=code, message=BilingualText(id=message_id, en=message_en)
        )


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    body = ErrorResponse(detail=exc.detail)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


async def validation_error_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    """Return a stable error without reflecting upload metadata or input values."""
    body = ErrorResponse(
        detail=ErrorDetail(
            code="invalid_request",
            message=BilingualText(
                id="Permintaan tidak lengkap atau mode tidak valid.",
                en="The request is incomplete or the selected mode is invalid.",
            ),
        )
    )
    return JSONResponse(status_code=422, content=body.model_dump())

