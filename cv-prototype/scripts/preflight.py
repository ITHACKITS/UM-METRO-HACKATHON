#!/usr/bin/env python3
"""Offline-safe verification of model files, hashes, and runtime prerequisites."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent
LOCK_PATH = PROJECT / "model-lock.json"
MODEL_ROOT = Path(os.environ.get("JAGAPADI_CV_MODEL_DIR", PROJECT / ".models"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_file(path: Path, expected: str | None) -> tuple[bool, str]:
    if not path.is_file():
        return False, f"missing: {path}"
    actual = sha256(path)
    if expected and actual != expected:
        return False, f"hash mismatch: {path} (expected {expected}, got {actual})"
    return True, f"ok: {path} sha256={actual}"


def load_provenance() -> dict[str, Any]:
    path = MODEL_ROOT / "provenance.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    provenance = load_provenance()
    errors: list[str] = []
    sys.path.insert(0, str(REPOSITORY / "backend"))
    from app.sigap.constants import (  # imported here so this script stays location-independent
        DISEASE_PREPROCESSING_VERSION,
        PEST_PREPROCESSING_VERSION,
    )

    print(f"TUAI Sigap offline preflight — Python {platform.python_version()}")
    print(f"Model root: {MODEL_ROOT}")

    disease = lock["models"]["disease"]
    for item in disease["files"]:
        ok, message = check_file(MODEL_ROOT / "disease" / item["path"], item["sha256"])
        print(message)
        if not ok:
            errors.append(message)
    disease_provenance = provenance.get("disease", {})
    if disease_provenance.get("revision") != disease["revision"]:
        errors.append("disease provenance is missing or does not match the locked revision")
    if disease["preprocessing_version"] != DISEASE_PREPROCESSING_VERSION:
        errors.append("disease runtime preprocessing does not match model-lock.json")
    if disease_provenance.get("preprocessing_version") != disease["preprocessing_version"]:
        errors.append("disease provenance preprocessing does not match model-lock.json")

    pest = lock["models"]["pest"]
    pest_path = MODEL_ROOT / "pest" / "model.onnx"
    pest_provenance = provenance.get("pest", {})
    expected_pest_hash = pest_provenance.get("artifact_sha256")
    if not expected_pest_hash:
        errors.append("pest conversion provenance/hash is missing")
    ok, message = check_file(pest_path, expected_pest_hash)
    print(message)
    if not ok:
        errors.append(message)
    if pest_provenance.get("revision") != pest["revision"]:
        errors.append("pest provenance is missing or does not match the locked revision")
    if pest["preprocessing_version"] != PEST_PREPROCESSING_VERSION:
        errors.append("pest runtime preprocessing does not match model-lock.json")
    if pest_provenance.get("preprocessing_version") != pest["preprocessing_version"]:
        errors.append("pest provenance preprocessing does not match model-lock.json")
    if (
        pest_provenance.get("validation_status")
        != "graph_and_fixture_and_runtime_parity_verified"
    ):
        errors.append(
            "pest ONNX has not passed source-vs-ONNX and backend-runtime fixture parity validation"
        )
    if pest_provenance.get("source_checkpoint_retained") is not False:
        errors.append("pest provenance does not confirm deletion of the pickle checkpoint")

    required_modules = ("fastapi", "PIL", "numpy", "torch", "transformers", "onnxruntime")
    for module in required_modules:
        available = importlib.util.find_spec(module) is not None
        print(f"runtime module {module}: {'ok' if available else 'missing'}")
        if not available:
            errors.append(f"runtime module missing: {module}")

    if os.environ.get("JAGAPADI_CV_OFFLINE", "1") not in {"1", "true", "TRUE"}:
        errors.append("JAGAPADI_CV_OFFLINE is not enabled")

    if errors:
        print("\nPreflight FAILED. Run the preparation/setup steps in README.md:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("\nPreflight passed. Both models and runtime dependencies are ready offline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

