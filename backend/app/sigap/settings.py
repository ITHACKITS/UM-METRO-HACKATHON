"""Runtime settings for TUAI Sigap models."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, minimum)


def _resolve_path(value: str | None, default: Path) -> Path:
    candidate = Path(value).expanduser() if value else default
    return candidate.resolve()


def _env(primary: str, legacy: str, default: str | None = None) -> str | None:
    """Read the TUAI name while tolerating the former local variable once."""
    return os.getenv(primary, os.getenv(legacy, default))


@dataclass(frozen=True, slots=True)
class Settings:
    prototype_root: Path
    model_dir: Path
    disease_dir: Path
    pest_onnx: Path
    calibration_path: Path
    offline: bool
    device: str
    preload: bool
    max_concurrency: int
    roboflow_enabled: bool = False
    roboflow_api_url: str = "https://serverless.roboflow.com"
    roboflow_api_key: str | None = None
    roboflow_model_id: str = "rice-pest-jmdev/1"
    roboflow_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> Settings:
        repository_root = Path(__file__).resolve().parents[3]
        prototype_root = repository_root / "cv-prototype"
        model_dir = _resolve_path(
            _env("TUAI_SIGAP_MODEL_DIR", "JAGAPADI_CV_MODEL_DIR"),
            prototype_root / ".models",
        )
        return cls(
            prototype_root=prototype_root,
            model_dir=model_dir,
            disease_dir=_resolve_path(
                _env("TUAI_SIGAP_DISEASE_DIR", "JAGAPADI_CV_DISEASE_DIR"),
                model_dir / "disease-efficientnet",
            ),
            pest_onnx=_resolve_path(
                _env("TUAI_SIGAP_PEST_ONNX", "JAGAPADI_CV_PEST_ONNX"),
                model_dir / "pest" / "model.onnx",
            ),
            calibration_path=_resolve_path(
                _env("TUAI_SIGAP_CALIBRATION", "JAGAPADI_CV_CALIBRATION"),
                prototype_root / "evaluation" / "operating-thresholds.json",
            ),
            offline=_env_bool(
                "TUAI_SIGAP_OFFLINE",
                _env_bool("JAGAPADI_CV_OFFLINE", True),
            ),
            device=(_env("TUAI_SIGAP_DEVICE", "JAGAPADI_CV_DEVICE", "auto") or "auto")
            .strip()
            .lower(),
            preload=_env_bool(
                "TUAI_SIGAP_PRELOAD",
                _env_bool("JAGAPADI_CV_PRELOAD", False),
            ),
            max_concurrency=_env_int(
                "TUAI_SIGAP_MAX_CONCURRENCY",
                _env_int("JAGAPADI_CV_MAX_CONCURRENCY", 1),
            ),
            roboflow_enabled=_env_bool("TUAI_SIGAP_ROBOFLOW", True),
            roboflow_api_url=(
                os.getenv("TUAI_SIGAP_ROBOFLOW_API_URL", "https://serverless.roboflow.com")
                .strip()
                .rstrip("/")
            ),
            roboflow_api_key=os.getenv("ROBOFLOW_API_KEY"),
            roboflow_model_id=os.getenv(
                "TUAI_SIGAP_ROBOFLOW_MODEL_ID", "rice-pest-jmdev/1"
            ).strip(),
            roboflow_timeout_seconds=_env_int(
                "TUAI_SIGAP_ROBOFLOW_TIMEOUT_SECONDS", 30
            ),
        )

