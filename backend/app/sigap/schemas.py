"""Public TUAI Sigap API schemas."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

CalibrationStatus = Literal["unavailable", "partial", "operating", "frozen"]


class BilingualText(BaseModel):
    id: str
    en: str


class QualityWarning(BaseModel):
    code: str
    message: BilingualText


class QualityReport(BaseModel):
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    format: str
    file_size_bytes: int = Field(ge=0)
    blur_score: float = Field(ge=0)
    mean_luminance: float = Field(ge=0, le=255)
    warnings: list[QualityWarning] = Field(default_factory=list)
    rejection_reason: BilingualText | None = None


class ModelProvenance(BaseModel):
    id: str
    revision: str
    artifact_sha256: str | None
    preprocessing_version: str


class BoundingBox(BaseModel):
    x_min: float = Field(ge=0)
    y_min: float = Field(ge=0)
    x_max: float = Field(ge=0)
    y_max: float = Field(ge=0)


class DiseaseHeatmap(BaseModel):
    """Per-cell influence (0-1) on the top class, over the photo region the model saw."""

    grid: list[list[float]]
    region: BoundingBox


class Recommendation(BaseModel):
    label: BilingualText
    steps: list[BilingualText]
    source_name: str
    source_url: str


class DiseaseCandidate(BaseModel):
    class_id: str
    label: BilingualText
    score: float = Field(ge=0, le=1)


class DiseaseResult(BaseModel):
    accepted: bool
    candidates: list[DiseaseCandidate]
    top_score: float | None = Field(default=None, ge=0, le=1)
    score_margin: float | None = Field(default=None, ge=0, le=1)
    calibration_status: CalibrationStatus
    consistency_status: Literal["not_checked", "stable", "unstable"] = "not_checked"
    view_count: int = Field(default=0, ge=0)
    top_class_agreement: float | None = Field(default=None, ge=0, le=1)
    top_score_spread: float | None = Field(default=None, ge=0, le=1)
    heatmap: DiseaseHeatmap | None = None
    closest_match: BilingualText | None = None


class PestDetection(BaseModel):
    class_id: int
    class_key: str
    label: BilingualText
    score: float = Field(ge=0, le=1)
    accepted: bool
    bbox: BoundingBox


class PestResult(BaseModel):
    detections: list[PestDetection]
    image_width: int = Field(ge=1)
    image_height: int = Field(ge=1)
    calibration_status: CalibrationStatus


class AnalysisBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "abstain", "retake"]
    score_kind: Literal["model_score"] = "model_score"
    processing: Literal["local", "roboflow_cloud"] = "local"
    model: ModelProvenance
    quality: QualityReport
    limitations: list[BilingualText]
    next_action: BilingualText
    recommendations: list[Recommendation] = Field(default_factory=list)
    general_steps: list[BilingualText] = Field(default_factory=list)


class DiseaseAnalysisResponse(AnalysisBase):
    mode: Literal["disease"] = "disease"
    disease: DiseaseResult


class PestAnalysisResponse(AnalysisBase):
    mode: Literal["pest"] = "pest"
    pest: PestResult


AnalyzeResponse = Annotated[
    DiseaseAnalysisResponse | PestAnalysisResponse, Field(discriminator="mode")
]


class ErrorDetail(BaseModel):
    code: str
    message: BilingualText


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class ModelHealth(BaseModel):
    mode: Literal["disease", "pest"]
    id: str
    revision: str
    state: Literal["unavailable", "unloaded", "ready", "error"]
    ready: bool
    loaded: bool
    artifact_sha256: str | None
    error: str | None


class RuntimeHealth(BaseModel):
    python: str
    platform: str
    device_preference: str


class HealthResponse(BaseModel):
    status: Literal["ready", "degraded"]
    service: str
    version: str
    offline: bool
    runtime: RuntimeHealth
    calibration_status: CalibrationStatus
    models: list[ModelHealth]


class CapabilityClass(BaseModel):
    class_id: str | int
    class_key: str
    label: BilingualText


class ModeCapability(BaseModel):
    mode: Literal["disease", "pest"]
    title: BilingualText
    photo_instruction: BilingualText
    classes: list[CapabilityClass]


class InputLimits(BaseModel):
    formats: list[str]
    max_compressed_bytes: int
    max_decoded_pixels: int
    disease_min_short_side: int
    pest_min_short_side: int


class CapabilitiesResponse(BaseModel):
    service: str
    models: list[ModelProvenance]
    modes: list[ModeCapability]
    input_limits: InputLimits
    limitations: list[BilingualText]

