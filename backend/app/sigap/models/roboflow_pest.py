"""Roboflow serverless detector: the first choice for pest photos when a key is set."""

from __future__ import annotations

import base64
import io
from collections.abc import Callable
from typing import Any

import httpx
from PIL import Image

from ..constants import (
    ROBOFLOW_PEST_MODEL_ID,
    ROBOFLOW_PEST_MODEL_REVISION,
    ROBOFLOW_PEST_PREPROCESSING_VERSION,
)
from ..schemas import BoundingBox, ModelHealth, ModelProvenance
from .base import ModelAdapter, ModelInferenceError, ModelUnavailableError, PestPrediction

# All six labels of rice-pest-jmdev/1. `stem-borer` keeps its own generic class and is
# never presented as the narrower yellow rice stem borer from the local detector.
ROBOFLOW_CLASS_MAP = {
    "brown-planthopper": 7,
    "leaf-folder": 0,
    "green-leafhopper": 100,
    "rice-bug": 101,
    "stem-borer": 102,
    "whorl-maggot": 103,
}

# Larger phone photos gain nothing at this model's input size and only slow the upload.
MAX_UPLOAD_SIDE = 1280


def _normalise_label(value: object) -> str:
    return "-".join(str(value).strip().lower().replace("_", "-").split())


class RoboflowPestAdapter(ModelAdapter):
    mode = "pest"
    model_id = ROBOFLOW_PEST_MODEL_ID
    revision = ROBOFLOW_PEST_MODEL_REVISION
    preprocessing_version = ROBOFLOW_PEST_PREPROCESSING_VERSION

    def __init__(
        self,
        *,
        enabled: bool,
        api_url: str,
        api_key: str | None,
        remote_model_id: str,
        timeout_seconds: int,
        sender: Callable[..., httpx.Response] | None = None,
    ) -> None:
        self.enabled = enabled
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key.strip() if api_key else None
        self.remote_model_id = remote_model_id.strip()
        self.timeout_seconds = timeout_seconds
        self._sender = sender or httpx.post

    @property
    def ready(self) -> bool:
        return bool(
            self.enabled
            and self.api_key
            and self.api_url.startswith("https://")
            and self.remote_model_id == "rice-pest-jmdev/1"
        )

    def provenance(self) -> ModelProvenance:
        project, _, revision = self.remote_model_id.partition("/")
        return ModelProvenance(
            id=f"roboflow/{project or self.model_id}",
            revision=revision or self.revision,
            artifact_sha256=None,
            preprocessing_version=self.preprocessing_version,
        )

    def health(self) -> ModelHealth:
        error: str | None = None
        if not self.enabled:
            error = "Roboflow is disabled."
        elif not self.api_key:
            error = "ROBOFLOW_API_KEY is not configured."
        elif not self.api_url.startswith("https://"):
            error = "Roboflow requires an HTTPS API URL."
        elif self.remote_model_id != "rice-pest-jmdev/1":
            error = "The configured Roboflow model is not the approved one."
        return ModelHealth(
            mode="pest",
            id=self.provenance().id,
            revision=self.provenance().revision,
            state="unloaded" if error is None else "unavailable",
            ready=error is None,
            loaded=False,
            artifact_sha256=None,
            error=error,
        )

    def load(self) -> None:
        if not self.ready:
            raise ModelUnavailableError(self.health().error or "Roboflow is unavailable.")

    def _decode(
        self, payload: Any, image_size: tuple[int, int], scale: float = 1.0
    ) -> list[PestPrediction]:
        if not isinstance(payload, dict) or not isinstance(payload.get("predictions"), list):
            raise ModelInferenceError("Roboflow returned an invalid object-detection response.")

        image_width, image_height = image_size
        decoded: list[PestPrediction] = []
        for item in payload["predictions"][:100]:
            if not isinstance(item, dict):
                continue
            class_id = ROBOFLOW_CLASS_MAP.get(_normalise_label(item.get("class")))
            if class_id is None:
                continue
            try:
                center_x = float(item["x"]) / scale
                center_y = float(item["y"]) / scale
                width = float(item["width"]) / scale
                height = float(item["height"]) / scale
                score = float(item["confidence"])
            except (KeyError, TypeError, ValueError):
                continue
            x_min = max(0.0, min(float(image_width), center_x - width / 2))
            y_min = max(0.0, min(float(image_height), center_y - height / 2))
            x_max = max(0.0, min(float(image_width), center_x + width / 2))
            y_max = max(0.0, min(float(image_height), center_y + height / 2))
            if not 0 <= score <= 1 or x_max <= x_min or y_max <= y_min:
                continue
            decoded.append(
                PestPrediction(
                    class_id=class_id,
                    score=score,
                    bbox=BoundingBox(
                        x_min=round(x_min, 2),
                        y_min=round(y_min, 2),
                        x_max=round(x_max, 2),
                        y_max=round(y_max, 2),
                    ),
                )
            )
        return sorted(decoded, key=lambda item: item.score, reverse=True)

    def predict(self, image: Image.Image) -> list[PestPrediction]:
        self.load()
        scale = min(1.0, MAX_UPLOAD_SIDE / max(image.size))
        upload = image
        if scale < 1.0:
            upload = image.resize(
                (round(image.width * scale), round(image.height * scale)),
                Image.Resampling.BILINEAR,
            )
        buffer = io.BytesIO()
        upload.save(buffer, format="JPEG", quality=90)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        endpoint = f"{self.api_url}/{self.remote_model_id}"
        try:
            response = self._sender(
                endpoint,
                content=encoded,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                params={"confidence": 0.05},
                # A dead network should reach the local model quickly.
                timeout=httpx.Timeout(self.timeout_seconds, connect=4.0),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            # Never include a URL, response body, or auth header in public errors.
            raise ModelInferenceError("Roboflow pest request failed.") from exc
        return self._decode(payload, image.size, scale)
