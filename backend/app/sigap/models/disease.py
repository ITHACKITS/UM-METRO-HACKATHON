"""Frozen rice-leaf disease model adapter."""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

from PIL import Image, ImageOps

from ..constants import (
    DISEASE_CLASSES,
    DISEASE_MODEL_ID,
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
)
from ..schemas import ModelHealth, ModelProvenance
from .base import (
    DiseaseInference,
    DiseasePrediction,
    ModelAdapter,
    ModelInferenceError,
    ModelUnavailableError,
    sha256_file,
)


def _canonical_class(raw_label: str) -> str | None:
    normalized = raw_label.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    for class_id, metadata in DISEASE_CLASSES.items():
        aliases = {
            str(alias).strip().lower().replace("_", " ").replace("-", " ")
            for alias in metadata["aliases"]
        }
        if normalized in aliases:
            return class_id
    return None


class DiseaseAdapter(ModelAdapter):
    mode = "disease"
    model_id = DISEASE_MODEL_ID
    revision = DISEASE_MODEL_REVISION
    preprocessing_version = DISEASE_PREPROCESSING_VERSION

    def __init__(self, model_dir: Path, device_preference: str = "auto") -> None:
        self.model_dir = model_dir
        self.device_preference = device_preference
        self._model = None
        self._processor = None
        self._torch = None
        self._device = "cpu"
        self._error: str | None = None
        self._artifact_hash: str | None = None
        self._load_lock = threading.Lock()

    @property
    def weight_path(self) -> Path | None:
        for name in ("model.safetensors", "pytorch_model.bin"):
            candidate = self.model_dir / name
            if candidate.is_file():
                return candidate
        return None

    def _runtime_available(self) -> bool:
        return bool(
            importlib.util.find_spec("torch")
            and importlib.util.find_spec("transformers")
        )

    def provenance(self) -> ModelProvenance:
        weight = self.weight_path
        if self._artifact_hash is None and weight:
            self._artifact_hash = sha256_file(weight)
        return ModelProvenance(
            id=self.model_id,
            revision=self.revision,
            artifact_sha256=self._artifact_hash,
            preprocessing_version=self.preprocessing_version,
        )

    def health(self) -> ModelHealth:
        artifact = self.weight_path
        if self._model is not None:
            state = "ready"
        elif self._error:
            state = "error"
        elif not artifact or not (self.model_dir / "config.json").is_file():
            state = "unavailable"
        elif not self._runtime_available():
            state = "unavailable"
        else:
            state = "unloaded"
        provenance = self.provenance()
        error = self._error
        if state == "unavailable" and error is None:
            if not artifact:
                error = "Prepared disease weights are absent. Run model preflight."
            elif not self._runtime_available():
                error = "Disease runtime dependencies are not installed."
            else:
                error = "Disease model config.json is absent."
        return ModelHealth(
            mode="disease",
            id=self.model_id,
            revision=self.revision,
            state=state,
            ready=state in {"unloaded", "ready"},
            loaded=self._model is not None,
            artifact_sha256=provenance.artifact_sha256,
            error=error,
        )

    def load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            weight = self.weight_path
            if not weight or not (self.model_dir / "config.json").is_file():
                raise ModelUnavailableError(
                    "Prepared disease model is absent; run the offline preflight first."
                )
            if not self._runtime_available():
                raise ModelUnavailableError(
                    "Install the disease runtime dependencies before inference."
                )
            try:
                import torch
                from transformers import AutoImageProcessor, AutoModelForImageClassification

                if self.device_preference == "cuda":
                    if not torch.cuda.is_available():
                        raise ModelUnavailableError("CUDA was requested but is unavailable.")
                    device = "cuda"
                elif self.device_preference == "cpu":
                    device = "cpu"
                else:
                    device = "cuda" if torch.cuda.is_available() else "cpu"

                processor = AutoImageProcessor.from_pretrained(
                    self.model_dir,
                    local_files_only=True,
                    trust_remote_code=False,
                    use_fast=False,
                )
                model = AutoModelForImageClassification.from_pretrained(
                    self.model_dir, local_files_only=True, trust_remote_code=False
                )
                model.eval()
                model.to(device)
                self._torch = torch
                self._processor = processor
                self._model = model
                self._device = device
                self._artifact_hash = sha256_file(weight)
                self._error = None
            except ModelUnavailableError:
                raise
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                raise ModelUnavailableError(
                    "The prepared disease model could not be loaded; inspect health details."
                ) from exc

    @staticmethod
    def _views(image: Image.Image) -> list[Image.Image]:
        """Return deterministic views that preserve the locked processor contract."""
        width, height = image.size
        crop_width = max(1, round(width * 0.82))
        crop_height = max(1, round(height * 0.82))
        left = (width - crop_width) // 2
        top = (height - crop_height) // 2
        center_crop = image.crop((left, top, left + crop_width, top + crop_height))
        return [image, ImageOps.mirror(image), center_crop]

    def predict(self, image: Image.Image) -> DiseaseInference:
        self.load()
        assert self._model is not None
        assert self._processor is not None
        assert self._torch is not None
        try:
            views = self._views(image)
            inputs = self._processor(images=views, return_tensors="pt")
            inputs = {key: value.to(self._device) for key, value in inputs.items()}
            with self._torch.inference_mode():
                logits = self._model(**inputs).logits
                probabilities = (
                    self._torch.softmax(logits, dim=-1).detach().cpu().tolist()
                )

            id_to_label = getattr(self._model.config, "id2label", {})
            class_ids: list[str] = []
            for index in range(len(probabilities[0])):
                raw_label = str(id_to_label.get(index, id_to_label.get(str(index), index)))
                class_id = _canonical_class(raw_label)
                if class_id is None:
                    raise ModelInferenceError(
                        "Disease label order does not match the locked five-class contract."
                    )
                class_ids.append(class_id)
            if len(class_ids) != len(DISEASE_CLASSES):
                raise ModelInferenceError(
                    "Disease label order does not match the locked five-class contract."
                )

            mean_scores = [
                sum(view[index] for view in probabilities) / len(probabilities)
                for index in range(len(class_ids))
            ]
            predictions = sorted(
                (
                    DiseasePrediction(class_id=class_id, score=float(mean_scores[index]))
                    for index, class_id in enumerate(class_ids)
                ),
                key=lambda item: item.score,
                reverse=True,
            )
            top_class = predictions[0].class_id
            top_index = class_ids.index(top_class)
            view_top_classes = [
                class_ids[max(range(len(view)), key=view.__getitem__)]
                for view in probabilities
            ]
            agreement = sum(item == top_class for item in view_top_classes) / len(views)
            top_scores = [view[top_index] for view in probabilities]
            spread = max(top_scores) - min(top_scores)
            stable = agreement == 1.0 and spread <= 0.25
            return DiseaseInference(
                predictions=predictions,
                view_count=len(views),
                top_class_agreement=float(agreement),
                top_score_spread=float(spread),
                stable=stable,
            )
        except ModelInferenceError:
            raise
        except Exception as exc:
            raise ModelInferenceError("Disease inference failed.") from exc

