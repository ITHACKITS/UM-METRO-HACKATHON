"""TUAI Sigap inference orchestration."""

from __future__ import annotations

import logging
import platform
import sys
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

from . import __version__
from .calibration import Calibration
from .constants import (
    ALLOWED_IMAGE_FORMATS,
    DISEASE_CLASSES,
    DISEASE_MIN_SIDE,
    MAX_COMPRESSED_BYTES,
    MAX_DECODED_PIXELS,
    PEST_CLASSES,
    PEST_MIN_SIDE,
)
from .errors import APIError
from .image_io import DecodedImage
from .models import DiseaseAdapter, PestAdapter, RoboflowPestAdapter
from .models.base import ModelInferenceError, ModelUnavailableError, PestPrediction
from .policy import (
    DISEASE_LIMITATIONS,
    PEST_LIMITATIONS,
    disease_decision,
    pest_decision,
)
from .quality import assess_quality
from .schemas import (
    BilingualText,
    CapabilitiesResponse,
    CapabilityClass,
    DiseaseAnalysisResponse,
    DiseaseResult,
    HealthResponse,
    InputLimits,
    ModeCapability,
    PestAnalysisResponse,
    PestResult,
    RuntimeHealth,
)
from .settings import Settings

logger = logging.getLogger(__name__)


class InferenceService:
    def __init__(
        self,
        settings: Settings,
        disease_adapter: DiseaseAdapter | None = None,
        pest_adapter: PestAdapter | None = None,
        roboflow_adapter: RoboflowPestAdapter | None = None,
        calibration: Calibration | None = None,
    ) -> None:
        self.settings = settings
        self.disease_adapter = disease_adapter or DiseaseAdapter(
            settings.disease_dir, settings.device
        )
        self.pest_adapter = pest_adapter or PestAdapter(settings.pest_onnx)
        self.roboflow_adapter = roboflow_adapter or RoboflowPestAdapter(
            enabled=settings.roboflow_enabled,
            api_url=settings.roboflow_api_url,
            api_key=settings.roboflow_api_key,
            remote_model_id=settings.roboflow_model_id,
            timeout_seconds=settings.roboflow_timeout_seconds,
        )
        self.calibration = calibration or Calibration.load(settings.calibration_path)
        self.executor = ThreadPoolExecutor(
            max_workers=settings.max_concurrency, thread_name_prefix="cv-inference"
        )

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def preload(self) -> None:
        errors: list[str] = []
        for adapter in (self.disease_adapter, self.pest_adapter):
            try:
                adapter.load()
            except ModelUnavailableError as exc:
                if adapter is self.pest_adapter and self.roboflow_adapter.ready:
                    continue
                errors.append(str(exc))
        if errors:
            raise ModelUnavailableError("; ".join(errors))

    def health(self) -> HealthResponse:
        disease = self.disease_adapter.health()
        pest = self.pest_adapter.health()
        fallback = self.roboflow_adapter.health()
        models = [disease, pest]
        if self.settings.roboflow_enabled:
            models.append(fallback)
        return HealthResponse(
            status="ready" if disease.ready and (pest.ready or fallback.ready) else "degraded",
            service="TUAI Sigap API",
            version=__version__,
            offline=self.settings.offline
            and not self.settings.roboflow_enabled,
            runtime=RuntimeHealth(
                python=sys.version.split()[0],
                platform=platform.platform(),
                device_preference=self.settings.device,
            ),
            calibration_status=self.calibration.status,
            models=models,
        )

    def capabilities(self) -> CapabilitiesResponse:
        disease_classes = [
            CapabilityClass(
                class_id=class_id,
                class_key=class_id,
                label=BilingualText(id=str(data["id"]), en=str(data["en"])),
            )
            for class_id, data in DISEASE_CLASSES.items()
            if data["result"]
        ]
        pest_classes = [
            CapabilityClass(
                class_id=class_id,
                class_key=str(data["key"]),
                label=BilingualText(id=str(data["id"]), en=str(data["en"])),
            )
            for class_id, data in PEST_CLASSES.items()
        ]
        models = [
            self.disease_adapter.provenance(),
            self.pest_adapter.provenance(),
        ]
        if self.settings.roboflow_enabled:
            models.append(self.roboflow_adapter.provenance())
        limitations = list(DISEASE_LIMITATIONS + PEST_LIMITATIONS)
        return CapabilitiesResponse(
            service="TUAI Sigap — Cek Daun & Hama",
            models=models,
            modes=[
                ModeCapability(
                    mode="disease",
                    title=BilingualText(id="Cek gejala daun", en="Check leaf symptoms"),
                    photo_instruction=BilingualText(
                        id="Foto satu daun dari dekat, fokus, dan dalam cahaya alami merata.",
                        en="Photograph one leaf close up, in focus, under even natural light.",
                    ),
                    classes=disease_classes,
                ),
                ModeCapability(
                    mode="pest",
                    title=BilingualText(id="Cari hama yang terlihat", en="Find visible pests"),
                    photo_instruction=BilingualText(
                        id="Foto serangga yang terlihat dari dekat saat masih berada pada tanaman.",
                        en="Photograph the visible insect close up while it is still on the plant.",
                    ),
                    classes=pest_classes,
                ),
            ],
            input_limits=InputLimits(
                formats=sorted("HEIC" if item == "HEIF" else item for item in ALLOWED_IMAGE_FORMATS),
                max_compressed_bytes=MAX_COMPRESSED_BYTES,
                max_decoded_pixels=MAX_DECODED_PIXELS,
                disease_min_short_side=DISEASE_MIN_SIDE,
                pest_min_short_side=PEST_MIN_SIDE,
            ),
            limitations=limitations,
        )

    @staticmethod
    def _model_error(exc: Exception) -> APIError:
        if isinstance(exc, ModelUnavailableError):
            return APIError(
                503,
                "model_unavailable",
                "Pemeriksaan foto tidak tersedia saat ini. Coba lagi sebentar lagi.",
                "Photo checking is unavailable right now. Please try again shortly.",
            )
        return APIError(
            503,
            "inference_failed",
            "Foto ini tidak berhasil diperiksa. Coba lagi.",
            "This photo could not be checked. Please try again.",
        )

    def analyze_disease(self, decoded: DecodedImage) -> DiseaseAnalysisResponse:
        quality = assess_quality(decoded, "disease")
        if quality.rejection_reason:
            return DiseaseAnalysisResponse(
                status="retake",
                model=self.disease_adapter.provenance(),
                quality=quality,
                limitations=list(DISEASE_LIMITATIONS),
                next_action=BilingualText(
                    id="Ambil ulang satu daun dari dekat dengan fokus dan cahaya merata.",
                    en="Retake one leaf close up, in focus, with even lighting.",
                ),
                disease=DiseaseResult(
                    accepted=False,
                    candidates=[],
                    top_score=None,
                    score_margin=None,
                    calibration_status=self.calibration.status,
                ),
            )
        try:
            inference = self.disease_adapter.predict(decoded.image)
        except (ModelUnavailableError, ModelInferenceError) as exc:
            raise self._model_error(exc) from exc
        status, result, limitations, action, recommendations, general = disease_decision(
            inference, self.calibration
        )
        return DiseaseAnalysisResponse(
            status=status,
            model=self.disease_adapter.provenance(),
            quality=quality,
            limitations=limitations,
            next_action=action,
            recommendations=recommendations,
            general_steps=general,
            disease=result,
        )

    def _detect_pests(
        self, image: Image.Image, live: bool
    ) -> tuple[list[PestPrediction], str]:
        """Try the detectors in order and return the first answer.

        Full photos go to Roboflow first. Live camera frames stay local when possible,
        because they arrive continuously and each cloud call uses account credits.
        """
        remote = (self.roboflow_adapter, "roboflow_cloud")
        local = (self.pest_adapter, "local")
        order = [local, remote] if live else [remote, local]
        failure: Exception | None = None
        for adapter, processing in order:
            if adapter is self.roboflow_adapter and not adapter.ready:
                continue
            try:
                return adapter.predict(image), processing
            except (ModelUnavailableError, ModelInferenceError) as exc:
                logger.info("Pest detector %s unavailable: %s", processing, type(exc).__name__)
                failure = exc
        raise self._model_error(failure or ModelUnavailableError("No pest detector."))

    def analyze_pest(self, decoded: DecodedImage, live: bool = False) -> PestAnalysisResponse:
        quality = assess_quality(decoded, "pest")
        if quality.rejection_reason:
            return PestAnalysisResponse(
                status="retake",
                model=(
                    self.roboflow_adapter
                    if self.roboflow_adapter.ready
                    else self.pest_adapter
                ).provenance(),
                quality=quality,
                limitations=list(PEST_LIMITATIONS),
                next_action=BilingualText(
                    id="Ambil ulang serangga dari jarak lebih dekat dan dalam fokus.",
                    en="Retake the insect closer and in focus.",
                ),
                pest=PestResult(
                    detections=[],
                    image_width=quality.width,
                    image_height=quality.height,
                    calibration_status=self.calibration.status,
                ),
            )
        predictions, processing = self._detect_pests(decoded.image, live)
        is_remote = processing == "roboflow_cloud"
        status, result, limitations, action, recommendations, general = pest_decision(
            predictions,
            self.calibration,
            quality.width,
            quality.height,
            thresholds=self.calibration.pest_remote if is_remote else self.calibration.pest,
        )
        return PestAnalysisResponse(
            status=status,
            processing=processing,
            model=(self.roboflow_adapter if is_remote else self.pest_adapter).provenance(),
            quality=quality,
            limitations=limitations,
            next_action=action,
            recommendations=recommendations,
            general_steps=general,
            pest=result,
        )
