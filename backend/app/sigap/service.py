"""TUAI Sigap inference orchestration."""

from __future__ import annotations

import platform
import sys
from concurrent.futures import ThreadPoolExecutor

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
from .models.base import ModelInferenceError, ModelUnavailableError
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
            enabled=settings.roboflow_fallback_enabled,
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
        if self.settings.roboflow_fallback_enabled:
            models.append(fallback)
        return HealthResponse(
            status="ready" if disease.ready and (pest.ready or fallback.ready) else "degraded",
            service="TUAI Sigap API",
            version=__version__,
            offline=self.settings.offline
            and not self.settings.roboflow_fallback_enabled,
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
        if self.settings.roboflow_fallback_enabled:
            models.append(self.roboflow_adapter.provenance())
        limitations = list(DISEASE_LIMITATIONS + PEST_LIMITATIONS)
        if self.settings.roboflow_fallback_enabled:
            limitations.append(
                BilingualText(
                    id="Fallback hama Roboflow hanya digunakan setelah persetujuan; foto dikirim ke layanan cloud eksternal.",
                    en="The Roboflow pest fallback is used only after consent; the photo is sent to an external cloud service.",
                )
            )
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
                "Model untuk mode ini belum siap. Jalankan pemeriksaan model sebelum demo.",
                "The model for this mode is not ready. Run model preflight before the demo.",
            )
        return APIError(
            503,
            "inference_failed",
            "Model gagal memproses foto ini. Periksa status layanan dan coba lagi.",
            "The model failed to process this photo. Check service health and try again.",
        )

    def analyze_disease(
        self, decoded: DecodedImage, confirm_leaf_subject: bool = False
    ) -> DiseaseAnalysisResponse:
        quality = assess_quality(decoded, "disease")
        provenance = self.disease_adapter.provenance()
        subject_rejection = None
        if not confirm_leaf_subject:
            subject_rejection = BilingualText(
                id="Konfirmasikan bahwa foto menampilkan satu daun padi dari dekat, bukan hamparan sawah atau serangga.",
                en="Confirm that the photo shows one rice leaf close up, not a whole field or an insect.",
            )
            quality = quality.model_copy(update={"rejection_reason": subject_rejection})
        if quality.rejection_reason:
            return DiseaseAnalysisResponse(
                status="retake",
                model=provenance,
                quality=quality,
                limitations=list(DISEASE_LIMITATIONS),
                next_action=BilingualText(
                    id=(
                        "Pilih atau ambil foto satu daun padi dari dekat, lalu konfirmasikan subjek sebelum analisis."
                        if subject_rejection
                        else "Ambil ulang satu daun dari dekat dengan fokus dan cahaya merata."
                    ),
                    en=(
                        "Choose or take a close-up photo of one rice leaf, then confirm the subject before analysis."
                        if subject_rejection
                        else "Retake one leaf close up, in focus, with even lighting."
                    ),
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
        status, result, limitations, action = disease_decision(
            inference, self.calibration
        )
        return DiseaseAnalysisResponse(
            status=status,
            model=self.disease_adapter.provenance(),
            quality=quality,
            limitations=limitations,
            next_action=action,
            disease=result,
        )

    def analyze_pest(
        self, decoded: DecodedImage, allow_remote_fallback: bool = False
    ) -> PestAnalysisResponse:
        quality = assess_quality(decoded, "pest")
        local_ready = self.pest_adapter.health().ready
        provenance = (
            self.pest_adapter.provenance()
            if local_ready or not allow_remote_fallback
            else self.roboflow_adapter.provenance()
        )
        if quality.rejection_reason:
            return PestAnalysisResponse(
                status="retake",
                model=provenance,
                quality=quality,
                limitations=list(PEST_LIMITATIONS),
                next_action=BilingualText(
                    id="Ambil ulang serangga yang terlihat dari jarak lebih dekat dan dalam fokus.",
                    en="Retake the visible insect closer and in focus.",
                ),
                pest=PestResult(
                    detections=[],
                    image_width=quality.width,
                    image_height=quality.height,
                    calibration_status=self.calibration.status,
                ),
            )
        processing = "local"
        try:
            predictions = self.pest_adapter.predict(decoded.image)
        except (ModelUnavailableError, ModelInferenceError) as exc:
            if not self.roboflow_adapter.ready:
                raise self._model_error(exc) from exc
            if not allow_remote_fallback:
                raise APIError(
                    503,
                    "remote_fallback_requires_consent",
                    "Model hama lokal belum siap. Aktifkan izin fallback cloud untuk mengirim foto ini ke Roboflow.",
                    "The local pest model is not ready. Enable cloud-fallback consent to send this photo to Roboflow.",
                ) from exc
            try:
                predictions = self.roboflow_adapter.predict(decoded.image)
                provenance = self.roboflow_adapter.provenance()
                processing = "roboflow_cloud"
            except (ModelUnavailableError, ModelInferenceError) as remote_exc:
                raise self._model_error(remote_exc) from remote_exc
        status, result, limitations, action = pest_decision(
            predictions, self.calibration, quality.width, quality.height
        )
        if processing == "roboflow_cloud":
            limitations.extend(
                [
                    BilingualText(
                        id="Foto ini dikirim ke layanan cloud Roboflow karena model hama lokal tidak siap; TUAI tidak menyimpan salinannya.",
                        en="This photo was sent to Roboflow cloud because the local pest model was unavailable; TUAI does not retain a copy.",
                    ),
                    BilingualText(
                        id="Fallback hanya memetakan brown-planthopper dan leaf-folder. Kelas stem-borer umum tidak dianggap penggerek batang padi kuning.",
                        en="The fallback maps only brown-planthopper and leaf-folder. Its generic stem-borer class is not treated as yellow rice stem borer.",
                    ),
                ]
            )
        return PestAnalysisResponse(
            status=status,
            processing=processing,
            model=provenance,
            quality=quality,
            limitations=limitations,
            next_action=action,
            pest=result,
        )

