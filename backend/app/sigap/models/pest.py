"""Frozen visible rice-pest ONNX adapter."""

from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

import numpy as np
from PIL import Image

from ..constants import (
    PEST_CLASSES,
    PEST_MODEL_ID,
    PEST_MODEL_REVISION,
    PEST_PREPROCESSING_VERSION,
)
from ..schemas import BoundingBox, ModelHealth, ModelProvenance
from .base import (
    ModelAdapter,
    ModelInferenceError,
    ModelUnavailableError,
    PestPrediction,
    sha256_file,
)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -80, 80)))


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    box_area = max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))
    boxes_area = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(
        0, boxes[:, 3] - boxes[:, 1]
    )
    union = box_area + boxes_area - intersection
    return np.divide(intersection, union, out=np.zeros_like(intersection), where=union > 0)


def _nms(boxes: np.ndarray, scores: np.ndarray, threshold: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        current = int(order[0])
        keep.append(current)
        if order.size == 1:
            break
        overlap = _iou(boxes[current], boxes[order[1:]])
        order = order[1:][overlap <= threshold]
    return keep


class PestAdapter(ModelAdapter):
    mode = "pest"
    model_id = PEST_MODEL_ID
    revision = PEST_MODEL_REVISION
    preprocessing_version = PEST_PREPROCESSING_VERSION

    def __init__(self, onnx_path: Path, candidate_threshold: float = 0.05) -> None:
        self.onnx_path = onnx_path
        self.candidate_threshold = candidate_threshold
        self._session = None
        self._input_name: str | None = None
        self._input_size = 640
        self._error: str | None = None
        self._artifact_hash: str | None = None
        self._load_lock = threading.Lock()

    def _runtime_available(self) -> bool:
        return bool(importlib.util.find_spec("onnxruntime"))

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
        if self._session is not None:
            state = "ready"
        elif self._error:
            state = "error"
        elif not self.onnx_path.is_file() or self.onnx_path.suffix.lower() != ".onnx":
            state = "unavailable"
        elif not self._runtime_available():
            state = "unavailable"
        else:
            state = "unloaded"
        error = self._error
        if state == "unavailable" and error is None:
            if not self.onnx_path.is_file():
                error = "Prepared pest ONNX artifact is absent. Run model preflight."
            elif self.onnx_path.suffix.lower() != ".onnx":
                error = "Runtime pest artifact must be an ONNX file."
            else:
                error = "ONNX Runtime is not installed."
        provenance = self.provenance()
        return ModelHealth(
            mode="pest",
            id=self.model_id,
            revision=self.revision,
            state=state,
            ready=state in {"unloaded", "ready"},
            loaded=self._session is not None,
            artifact_sha256=provenance.artifact_sha256,
            error=error,
        )

    def load(self) -> None:
        if self._session is not None:
            return
        with self._load_lock:
            if self._session is not None:
                return
            if not self.onnx_path.is_file() or self.onnx_path.suffix.lower() != ".onnx":
                raise ModelUnavailableError(
                    "Prepared pest ONNX model is absent; run the offline preflight first."
                )
            if not self._runtime_available():
                raise ModelUnavailableError("Install ONNX Runtime before pest inference.")
            try:
                import onnxruntime as ort

                session = ort.InferenceSession(
                    str(self.onnx_path), providers=["CPUExecutionProvider"]
                )
                model_input = session.get_inputs()[0]
                shape = model_input.shape
                if len(shape) == 4 and isinstance(shape[-1], int):
                    self._input_size = int(shape[-1])
                self._input_name = model_input.name
                self._session = session
                self._artifact_hash = sha256_file(self.onnx_path)
                self._error = None
            except Exception as exc:
                self._error = f"{type(exc).__name__}: {exc}"
                raise ModelUnavailableError(
                    "The prepared pest ONNX model could not be loaded; inspect health details."
                ) from exc

    def _preprocess(self, image: Image.Image) -> tuple[np.ndarray, float, float, float]:
        width, height = image.size
        size = self._input_size
        scale = min(size / width, size / height)
        resized_width = max(1, round(width * scale))
        resized_height = max(1, round(height * scale))
        resized = image.resize((resized_width, resized_height), Image.Resampling.BILINEAR)
        pad_x = (size - resized_width) / 2
        pad_y = (size - resized_height) / 2
        canvas = Image.new("RGB", (size, size), (114, 114, 114))
        canvas.paste(resized, (round(pad_x), round(pad_y)))
        tensor = np.asarray(canvas, dtype=np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
        return np.ascontiguousarray(tensor), scale, pad_x, pad_y

    def _decode_raw(
        self,
        output: np.ndarray,
        original_size: tuple[int, int],
        scale: float,
        pad_x: float,
        pad_y: float,
    ) -> list[PestPrediction]:
        values = np.asarray(output)
        while values.ndim > 2 and values.shape[0] == 1:
            values = values[0]
        if values.ndim != 2:
            raise ModelInferenceError(f"Unexpected pest output shape: {values.shape}")
        # The pinned YOLO export is either raw IP102 output (106 channels,
        # occasionally 107 with explicit objectness) or postprocessed xyxy,
        # score, class rows (6 channels).  Detect the channel axis explicitly;
        # a generic "shorter axis" heuristic corrupts valid small N x 6 output.
        channel_counts = {6, 106, 107}
        if values.shape[1] not in channel_counts and values.shape[0] in channel_counts:
            values = values.T

        width, height = original_size
        decoded: list[tuple[int, float, np.ndarray]] = []

        if values.shape[1] == 6:
            for row in values:
                class_id = int(round(float(row[5])))
                score = float(row[4])
                if class_id in PEST_CLASSES and score >= self.candidate_threshold:
                    box = np.asarray(row[:4], dtype=np.float32)
                    decoded.append((class_id, score, box))
        else:
            if values.shape[1] < 12:
                raise ModelInferenceError(f"Unexpected pest output shape: {values.shape}")
            class_scores = np.asarray(values[:, 4:], dtype=np.float32)
            if values.shape[1] == 107:  # 4 box + objectness + 102 IP102 classes
                objectness = class_scores[:, :1]
                class_scores = class_scores[:, 1:] * objectness
            if class_scores.min(initial=0) < 0 or class_scores.max(initial=1) > 1:
                class_scores = _sigmoid(class_scores)
            for class_id in PEST_CLASSES:
                if class_id >= class_scores.shape[1]:
                    continue
                scores = class_scores[:, class_id]
                candidate_indices = np.flatnonzero(scores >= self.candidate_threshold)
                for index in candidate_indices:
                    cx, cy, box_width, box_height = values[index, :4]
                    box = np.asarray(
                        [
                            cx - box_width / 2,
                            cy - box_height / 2,
                            cx + box_width / 2,
                            cy + box_height / 2,
                        ],
                        dtype=np.float32,
                    )
                    decoded.append((class_id, float(scores[index]), box))

        predictions: list[PestPrediction] = []
        for class_id in PEST_CLASSES:
            class_items = [item for item in decoded if item[0] == class_id]
            if not class_items:
                continue
            scores = np.asarray([item[1] for item in class_items], dtype=np.float32)
            boxes = np.stack([item[2] for item in class_items])
            keep = _nms(boxes, scores, threshold=0.45)
            for index in keep:
                box = boxes[index]
                x_min = float(np.clip((box[0] - pad_x) / scale, 0, width))
                y_min = float(np.clip((box[1] - pad_y) / scale, 0, height))
                x_max = float(np.clip((box[2] - pad_x) / scale, 0, width))
                y_max = float(np.clip((box[3] - pad_y) / scale, 0, height))
                if x_max <= x_min or y_max <= y_min:
                    continue
                predictions.append(
                    PestPrediction(
                        class_id=class_id,
                        score=float(scores[index]),
                        bbox=BoundingBox(
                            x_min=round(x_min, 2),
                            y_min=round(y_min, 2),
                            x_max=round(x_max, 2),
                            y_max=round(y_max, 2),
                        ),
                    )
                )
        return sorted(predictions, key=lambda item: item.score, reverse=True)

    def predict(self, image: Image.Image) -> list[PestPrediction]:
        self.load()
        assert self._session is not None
        assert self._input_name is not None
        tensor, scale, pad_x, pad_y = self._preprocess(image)
        try:
            outputs = self._session.run(None, {self._input_name: tensor})
            if not outputs:
                raise ModelInferenceError("Pest model returned no outputs.")
            return self._decode_raw(
                outputs[0], image.size, scale=scale, pad_x=pad_x, pad_y=pad_y
            )
        except ModelInferenceError:
            raise
        except Exception as exc:
            raise ModelInferenceError("Pest inference failed.") from exc

