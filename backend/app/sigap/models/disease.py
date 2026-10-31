"""Rice-leaf disease classifier running from a local ONNX export.

Model: Huyt/rice-leaf-disease-efficientnet-b0 (Apache-2.0), exported by
cv-prototype/scripts/prepare_models.py. The export has a second output, a class map: the
classifier weights applied to the final 7x7 feature map. Its mean equals the class logit,
so it shows which parts of the photo actually drove that class.
"""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from ..constants import (
    DISEASE_CLASSES,
    DISEASE_MODEL_ID,
    DISEASE_MODEL_REVISION,
    DISEASE_PREPROCESSING_VERSION,
    DISEASE_RAW_LABELS,
)
from ..schemas import BoundingBox, DiseaseHeatmap, ModelHealth, ModelProvenance
from .base import (
    DiseaseInference,
    DiseasePrediction,
    ModelAdapter,
    ModelInferenceError,
    ModelUnavailableError,
    sha256_file,
)

INPUT_SIZE = 224
CROP_PCT = 0.875
MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)


def _canonical_class(raw_label: str) -> str | None:
    for class_id, metadata in DISEASE_CLASSES.items():
        if raw_label in metadata["aliases"]:
            return class_id
    return None


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)


def center_crop_box(width: int, height: int) -> tuple[float, float, float, float]:
    """Return the square region of the original photo that the model actually sees."""
    side = min(width, height) * CROP_PCT
    left = (width - side) / 2
    top = (height - side) / 2
    return left, top, left + side, top + side


class DiseaseAdapter(ModelAdapter):
    mode = "disease"
    model_id = DISEASE_MODEL_ID
    revision = DISEASE_MODEL_REVISION
    preprocessing_version = DISEASE_PREPROCESSING_VERSION

    def __init__(self, model_dir: Path, device_preference: str = "auto") -> None:
        self.model_dir = model_dir
        self.device_preference = device_preference
        self._session = None
        self._error: str | None = None
        self._artifact_hash: str | None = None
        self._load_lock = threading.Lock()

    @property
    def onnx_path(self) -> Path:
        return self.model_dir / "model.onnx"

    def provenance(self) -> ModelProvenance:
        if self._artifact_hash is None and self.onnx_path.is_file():
            self._artifact_hash = sha256_file(self.onnx_path)
        return ModelProvenance(
            id=self.model_id,
            revision=self.revision,
            artifact_sha256=self._artifact_hash,
            preprocessing_version=self.preprocessing_version,
        )

    def health(self) -> ModelHealth:
        runtime = bool(importlib.util.find_spec("onnxruntime"))
        if self._session is not None:
            state = "ready"
        elif self._error:
            state = "error"
        elif not self.onnx_path.is_file() or not runtime:
            state = "unavailable"
        else:
            state = "unloaded"
        error = self._error
        if state == "unavailable" and error is None:
            error = (
                "ONNX Runtime is not installed."
                if self.onnx_path.is_file()
                else "Prepared disease ONNX model is absent."
            )
        return ModelHealth(
            mode="disease",
            id=self.model_id,
            revision=self.revision,
            state=state,
            ready=state in {"unloaded", "ready"},
            loaded=self._session is not None,
            artifact_sha256=self.provenance().artifact_sha256,
            error=error,
        )

    def load(self) -> None:
        if self._session is not None:
            return
        with self._load_lock:
            if self._session is not None:
                return
            if not self.onnx_path.is_file():
                raise ModelUnavailableError("Prepared disease ONNX model is absent.")
            if not importlib.util.find_spec("onnxruntime"):
                raise ModelUnavailableError("Install ONNX Runtime before disease inference.")
            try:
                import onnxruntime as ort

                self._session = ort.InferenceSession(
                    str(self.onnx_path), providers=["CPUExecutionProvider"]
                )
                self._artifact_hash = sha256_file(self.onnx_path)
                self._error = None
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                raise ModelUnavailableError(
                    "The prepared disease ONNX model could not be loaded."
                ) from exc

    @staticmethod
    def _preprocess(image: Image.Image) -> np.ndarray:
        """Match the model card: bicubic resize, 0.875 center crop, ImageNet norm."""
        width, height = image.size
        short_side = int(np.floor(INPUT_SIZE / CROP_PCT))
        scale = short_side / min(width, height)
        resized_w, resized_h = round(width * scale), round(height * scale)
        resized = image.resize((resized_w, resized_h), Image.Resampling.BICUBIC)
        left = int(round((resized_w - INPUT_SIZE) / 2))
        top = int(round((resized_h - INPUT_SIZE) / 2))
        cropped = resized.crop((left, top, left + INPUT_SIZE, top + INPUT_SIZE))
        array = (np.asarray(cropped, dtype=np.float32) / 255.0 - MEAN) / STD
        return array.transpose(2, 0, 1)

    def predict(self, image: Image.Image) -> DiseaseInference:
        self.load()
        assert self._session is not None
        try:
            views = np.stack(
                [self._preprocess(image), self._preprocess(ImageOps.mirror(image))]
            )
            logits, class_maps = self._session.run(None, {"pixel_values": views})
            if logits.shape[1] != len(DISEASE_RAW_LABELS):
                raise ModelInferenceError("Disease output does not match the class list.")
            probabilities = _softmax(logits)

            mean_scores: dict[str, float] = {}
            for index, raw_label in enumerate(DISEASE_RAW_LABELS):
                class_id = _canonical_class(raw_label)
                if class_id is None:
                    raise ModelInferenceError("Unknown disease label in the class list.")
                # Leaf and neck blast share a class here, so their scores add up.
                mean_scores[class_id] = mean_scores.get(class_id, 0.0) + float(
                    probabilities[:, index].mean()
                )
            predictions = sorted(
                (DiseasePrediction(class_id=key, score=value) for key, value in mean_scores.items()),
                key=lambda item: item.score,
                reverse=True,
            )

            top_class = predictions[0].class_id
            view_classes = [
                _canonical_class(DISEASE_RAW_LABELS[int(view.argmax())]) for view in probabilities
            ]
            agreement = sum(item == top_class for item in view_classes) / len(view_classes)
            top_indices = [
                index
                for index, raw_label in enumerate(DISEASE_RAW_LABELS)
                if _canonical_class(raw_label) == top_class
            ]
            top_scores = probabilities[:, top_indices].sum(axis=1)

            # Highlight from the unmirrored view, using its strongest raw class.
            best_raw = max(top_indices, key=lambda index: float(probabilities[0, index]))
            class_map = class_maps[0, best_raw]
            spread = float(class_map.max() - class_map.min())
            grid = (class_map - class_map.min()) / spread if spread > 1e-6 else class_map * 0
            x_min, y_min, x_max, y_max = center_crop_box(*image.size)
            return DiseaseInference(
                predictions=predictions,
                view_count=len(view_classes),
                top_class_agreement=float(agreement),
                top_score_spread=float(top_scores.max() - top_scores.min()),
                stable=agreement == 1.0,
                heatmap=DiseaseHeatmap(
                    grid=[[round(float(cell), 3) for cell in row] for row in grid],
                    region=BoundingBox(
                        x_min=round(x_min, 2),
                        y_min=round(y_min, 2),
                        x_max=round(x_max, 2),
                        y_max=round(y_max, 2),
                    ),
                ),
            )
        except ModelInferenceError:
            raise
        except Exception as exc:
            raise ModelInferenceError("Disease inference failed.") from exc
