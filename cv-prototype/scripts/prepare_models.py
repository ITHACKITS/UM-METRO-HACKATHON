#!/usr/bin/env python3
"""Prepare the two pinned models without committing any model artifact.

The disease weights are safetensors, so they load safely and are exported to ONNX here.
The pest source is a pickle-based .pt file: it is held only in a temporary
directory, hash-verified, converted to ONNX, and removed with that directory.
Run the pest command only through scripts/prepare_pest_sandboxed.sh, which isolates it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT = Path(__file__).resolve().parents[1]
LOCK_PATH = PROJECT / "model-lock.json"
MODEL_ROOT = Path(os.environ.get("JAGAPADI_CV_MODEL_DIR", PROJECT / ".models"))
PROVENANCE_PATH = MODEL_ROOT / "provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_hash(path: Path, expected: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f"Hash mismatch for {path}: expected {expected}, got {actual}")
    return actual


def load_lock() -> dict[str, Any]:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def load_provenance() -> dict[str, Any]:
    if not PROVENANCE_PATH.is_file():
        return {"schema_version": 1}
    return json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))


def save_provenance(data: dict[str, Any]) -> None:
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = PROVENANCE_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(PROVENANCE_PATH)


def package_versions(names: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def prepare_disease(lock: dict[str, Any]) -> None:
    """Download the pinned safetensors weights and export them to the runtime ONNX file."""
    try:
        import numpy as np
        import onnxruntime as ort
        import timm
        import torch
        from huggingface_hub import hf_hub_download
        from safetensors.torch import load_file
    except ImportError as exc:
        raise RuntimeError("Install requirements-model-tools.txt first") from exc

    model = lock["models"]["disease"]
    expected = {item["path"]: item["sha256"] for item in model["files"]}
    with tempfile.TemporaryDirectory(prefix="tuai-disease-export-") as directory:
        paths = {
            name: Path(
                hf_hub_download(
                    repo_id=model["id"],
                    filename=name,
                    revision=model["revision"],
                    local_dir=directory,
                )
            )
            for name in expected
        }
        for name, digest in expected.items():
            require_hash(paths[name], digest)

        network = timm.create_model(
            model["architecture"], num_classes=len(model["labels"]), pretrained=False
        )
        network.load_state_dict(load_file(str(paths["model.safetensors"])))
        network.eval()

        class WithClassMaps(torch.nn.Module):
            """Adds the classifier applied to each feature-map cell as a second output."""

            def __init__(self, inner: torch.nn.Module) -> None:
                super().__init__()
                self.inner = inner

            def forward(self, pixels: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
                features = self.inner.forward_features(pixels)
                logits = self.inner.forward_head(features)
                classifier = self.inner.classifier
                maps = torch.einsum("bchw,kc->bkhw", features, classifier.weight)
                return logits, maps + classifier.bias[None, :, None, None]

        wrapped = WithClassMaps(network).eval()
        sample = torch.randn(1, 3, *model["input_size"])
        target = MODEL_ROOT / "disease-efficientnet" / "model.onnx"
        target.parent.mkdir(parents=True, exist_ok=True)
        staged = target.with_suffix(".onnx.tmp")
        torch.onnx.export(
            wrapped,
            sample,
            str(staged),
            input_names=["pixel_values"],
            output_names=["logits", "cam"],
            opset_version=model["conversion"]["opset"],
            dynamic_axes={"pixel_values": {0: "b"}, "logits": {0: "b"}, "cam": {0: "b"}},
            dynamo=False,
        )

        # Check the exported graph against PyTorch before it replaces the runtime file.
        session = ort.InferenceSession(str(staged), providers=["CPUExecutionProvider"])
        exported_logits, exported_maps = session.run(None, {"pixel_values": sample.numpy()})
        with torch.inference_mode():
            source_logits = network(sample).numpy()
        drift = float(np.abs(exported_logits - source_logits).max())
        if drift > 1e-3:
            raise RuntimeError(f"ONNX logits drifted from PyTorch by {drift}")
        map_gap = float(np.abs(exported_maps.mean(axis=(2, 3)) - exported_logits).max())
        if map_gap > 1e-3:
            raise RuntimeError(f"Class maps do not average to the logits (gap {map_gap})")
        staged.replace(target)

    provenance = load_provenance()
    provenance["disease"] = {
        "model_id": model["id"],
        "revision": model["revision"],
        "preprocessing_version": model["preprocessing_version"],
        "files": expected,
        "artifact_sha256": sha256(target),
        "artifact_path": str(target.relative_to(PROJECT)) if target.is_relative_to(PROJECT) else str(target),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": "graph_parity_verified",
        "max_logit_drift": drift,
    }
    save_provenance(provenance)
    print(f"Disease ONNX prepared at {target}; logit drift {drift:.2e}")


def box_rows(result: Any, supported: set[int], minimum_score: float = 0.25) -> list[dict[str, Any]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    xyxy = boxes.xyxy.detach().cpu().numpy()
    scores = boxes.conf.detach().cpu().numpy()
    classes = boxes.cls.detach().cpu().numpy().astype(int)
    rows = [
        {"class_id": int(class_id), "score": float(score), "xyxy": coords.astype(float)}
        for coords, score, class_id in zip(xyxy, scores, classes, strict=True)
        if int(class_id) in supported and float(score) >= minimum_score
    ]
    return sorted(rows, key=lambda row: (row["class_id"], -row["score"]))


def backend_box_rows(
    predictions: Iterable[Any], minimum_score: float = 0.25
) -> list[dict[str, Any]]:
    import numpy as np

    rows = [
        {
            "class_id": int(item.class_id),
            "score": float(item.score),
            "xyxy": np.asarray(
                [item.bbox.x_min, item.bbox.y_min, item.bbox.x_max, item.bbox.y_max],
                dtype=np.float32,
            ),
        }
        for item in predictions
        if float(item.score) >= minimum_score
    ]
    return sorted(rows, key=lambda row: (row["class_id"], -row["score"]))


def intersection_over_union(left: Any, right: Any) -> float:
    import numpy as np

    x1, y1 = np.maximum(left[:2], right[:2])
    x2, y2 = np.minimum(left[2:], right[2:])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
    right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
    union = left_area + right_area - intersection
    return float(intersection / union) if union else 0.0


def compare_rows(
    source_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    fixture: Path,
    comparison_name: str,
) -> dict[str, Any]:
    import numpy as np

    if len(source_rows) != len(comparison_rows):
        raise RuntimeError(
            f"Conversion regression for {fixture} ({comparison_name}): supported "
            f"detection count changed from {len(source_rows)} to {len(comparison_rows)}"
        )

    score_drifts: list[float] = []
    ious: list[float] = []
    remaining = list(comparison_rows)
    for source in source_rows:
        candidates = [row for row in remaining if row["class_id"] == source["class_id"]]
        if not candidates:
            raise RuntimeError(
                f"Conversion regression for {fixture} ({comparison_name}): class mismatch"
            )
        match = max(candidates, key=lambda row: intersection_over_union(source["xyxy"], row["xyxy"]))
        remaining.remove(match)
        score_drifts.append(abs(source["score"] - match["score"]))
        ious.append(intersection_over_union(source["xyxy"], match["xyxy"]))

    mean_score_drift = float(np.mean(score_drifts)) if score_drifts else 0.0
    minimum_iou = min(ious, default=1.0)
    if mean_score_drift > 0.03:
        raise RuntimeError(
            f"Conversion regression for {fixture} ({comparison_name}): mean score "
            f"drift {mean_score_drift:.4f} > 0.03"
        )
    if minimum_iou < 0.95:
        raise RuntimeError(
            f"Conversion regression for {fixture} ({comparison_name}): minimum "
            f"matched IoU {minimum_iou:.4f} < 0.95"
        )
    return {
        "supported_detections": len(source_rows),
        "mean_score_drift": mean_score_drift,
        "minimum_box_iou": minimum_iou,
    }


def compare_fixture_results(
    source_result: Any,
    onnx_result: Any,
    supported: set[int],
    fixture: Path,
) -> dict[str, Any]:
    return {
        "fixture_sha256": sha256(fixture),
        **compare_rows(
            box_rows(source_result, supported),
            box_rows(onnx_result, supported),
            fixture,
            "ultralytics-onnx",
        ),
    }


def prepare_pest(lock: dict[str, Any], fixtures: list[Path], acknowledged: bool) -> None:
    if not acknowledged:
        raise RuntimeError(
            "The source .pt uses pickle. Re-run with --acknowledge-pickle-risk only inside "
            "a disposable environment with no secrets."
        )
    try:
        import onnx
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError("Install requirements-model-tools.txt in the disposable environment") from exc

    model = lock["models"]["pest"]
    checkpoint = model["source_checkpoint"]
    supported = {int(index) for index in model["class_map"]["supported_indices"]}
    missing = [fixture for fixture in fixtures if not fixture.is_file()]
    if missing:
        raise RuntimeError("Fixture file(s) missing: " + ", ".join(map(str, missing)))

    with tempfile.TemporaryDirectory(prefix="jagapadi-pest-conversion-") as directory:
        temporary = Path(directory)
        print("Downloading the pinned source checkpoint into a temporary directory...")
        checkpoint_path = Path(
            hf_hub_download(
                repo_id=model["id"],
                filename=checkpoint["path"],
                revision=model["revision"],
                local_dir=temporary,
            )
        )
        require_hash(checkpoint_path, checkpoint["sha256"])
        if checkpoint_path.stat().st_size != checkpoint["size_bytes"]:
            raise RuntimeError("Pest checkpoint size does not match model-lock.json")

        class_map_path = Path(
            hf_hub_download(
                repo_id=model["id"],
                filename=model["class_map"]["path"],
                revision=model["revision"],
                local_dir=temporary,
            )
        )
        require_hash(class_map_path, model["class_map"]["sha256"])

        print("Loading the verified .pt only inside the disposable preparation process...")
        source_model = YOLO(str(checkpoint_path))
        converted_path = Path(
            source_model.export(
                format="onnx",
                opset=model["conversion"]["opset"],
                imgsz=model["conversion"]["input_size"][0],
                dynamic=model["conversion"]["dynamic"],
                simplify=model["conversion"]["simplify"],
                half=False,
                device="cpu",
            )
        )
        graph = onnx.load(str(converted_path))
        onnx.checker.check_model(graph)
        session = ort.InferenceSession(str(converted_path), providers=["CPUExecutionProvider"])
        graph_details = {
            "inputs": [
                {"name": value.name, "shape": value.shape, "type": value.type}
                for value in session.get_inputs()
            ],
            "outputs": [
                {"name": value.name, "shape": value.shape, "type": value.type}
                for value in session.get_outputs()
            ],
        }

        fixture_results: list[dict[str, Any]] = []
        source_fixture_results: dict[Path, Any] = {}
        if fixtures:
            onnx_model = YOLO(str(converted_path), task="detect")
            for fixture in fixtures:
                source_result = source_model.predict(
                    source=str(fixture), imgsz=640, conf=0.05, iou=0.45, verbose=False, device="cpu"
                )[0]
                source_fixture_results[fixture] = source_result
                onnx_result = onnx_model.predict(
                    source=str(fixture), imgsz=640, conf=0.05, iou=0.45, verbose=False, device="cpu"
                )[0]
                fixture_results.append(
                    compare_fixture_results(source_result, onnx_result, supported, fixture)
                )
            if not any(item["supported_detections"] > 0 for item in fixture_results):
                raise RuntimeError(
                    "Fixture parity produced no supported pest detection at model score 0.25. "
                    "Provide at least one licensed/consented positive fixture; a zero-output "
                    "comparison is only a graph check."
                )

            # Check the exact preprocessing and decoder used by FastAPI as well as
            # Ultralytics' own ONNX path. This catches label-order/output-shape and
            # letterbox-coordinate regressions before the pickle source disappears.
            sys.path.insert(0, str(PROJECT.parent / "backend"))
            from app.sigap.models.pest import PestAdapter
            from PIL import Image

            backend_adapter = PestAdapter(converted_path)
            for fixture, item in zip(fixtures, fixture_results, strict=True):
                with Image.open(fixture) as opened:
                    backend_predictions = backend_adapter.predict(opened.convert("RGB"))
                item["backend_runtime"] = compare_rows(
                    box_rows(source_fixture_results[fixture], supported),
                    backend_box_rows(backend_predictions),
                    fixture,
                    "jagapadi-backend-onnx",
                )
            validation_status = "graph_and_fixture_and_runtime_parity_verified"
        else:
            validation_status = "graph_only_not_demo_ready"
            print(
                "Warning: no fixtures supplied. The graph is valid, but demo preflight will remain "
                "incomplete until conversion parity is checked with licensed/consented fixtures.",
                file=sys.stderr,
            )

        target = MODEL_ROOT / "pest" / "model.onnx"
        target.parent.mkdir(parents=True, exist_ok=True)
        staged_target = target.with_suffix(".onnx.tmp")
        shutil.copy2(converted_path, staged_target)
        staged_target.replace(target)
        artifact_hash = sha256(target)

    provenance = load_provenance()
    provenance["pest"] = {
        "model_id": model["id"],
        "revision": model["revision"],
        "preprocessing_version": model["preprocessing_version"],
        "source_checkpoint_sha256": checkpoint["sha256"],
        "artifact_sha256": artifact_hash,
        "artifact_path": str(target.relative_to(PROJECT)) if target.is_relative_to(PROJECT) else str(target),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation_status,
        "fixture_results": fixture_results,
        "graph": graph_details,
        "packages": package_versions(("ultralytics", "onnx", "onnxruntime", "torch")),
        "source_checkpoint_retained": False,
    }
    save_provenance(provenance)
    print(f"Pest ONNX prepared at {target}; sha256={artifact_hash}")
    print("The temporary source .pt has been deleted.")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("disease", help="Download the pinned safetensors weights and export the runtime ONNX")
    pest = subcommands.add_parser("pest", help="Convert the pinned pickle checkpoint to runtime ONNX")
    pest.add_argument(
        "--fixture",
        action="append",
        default=[],
        type=Path,
        help="Licensed/consented image used to compare source and ONNX outputs; repeat as needed",
    )
    pest.add_argument("--acknowledge-pickle-risk", action="store_true")
    return command


def main() -> int:
    arguments = parser().parse_args()
    lock = load_lock()
    try:
        if arguments.command == "disease":
            prepare_disease(lock)
        elif arguments.command == "pest":
            prepare_pest(lock, arguments.fixture, arguments.acknowledge_pickle_risk)
    except Exception as exc:  # preparation must fail closed with a concise reason
        print(f"Model preparation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

