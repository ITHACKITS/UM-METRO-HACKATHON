"""Command-line entry points for safe evaluation preparation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .hashing import hash_file, perceptual_hash
from .manifest import audit_manifest, canonical_manifest_hash, load_manifest
from .report import write_report
from .thresholds import select_disease_thresholds, select_pest_thresholds


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jagapadi-eval")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate manifest invariants")
    validate.add_argument("manifest", type=Path)
    audit = commands.add_parser("audit-manifest", help="check leakage and duplicates")
    audit.add_argument("manifest", type=Path)
    audit.add_argument("--near-distance", type=int, default=4)
    hashing = commands.add_parser("hash-image", help="hash one private local image")
    hashing.add_argument("image", type=Path)
    report = commands.add_parser("report", help="write a pending aggregate report")
    report.add_argument("manifest", type=Path)
    report.add_argument("--output", type=Path, required=True)
    disease = commands.add_parser(
        "calibrate-disease", help="select disease thresholds from calibration JSON"
    )
    disease.add_argument("input", type=Path)
    pest = commands.add_parser(
        "calibrate-pest", help="select pest thresholds from calibration JSON"
    )
    pest.add_argument("input", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "hash-image":
        result = {
            "sha256": hash_file(args.image),
            "perceptual_hash": perceptual_hash(args.image),
            "perceptual_hash_algorithm": "dhash64-v1",
        }
        print(json.dumps(result, indent=2))
        return 0
    if args.command in {"calibrate-disease", "calibrate-pest"}:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if args.command == "calibrate-disease":
            thresholds = select_disease_thresholds(
                payload["samples"],
                classes=payload["classes"],
                max_selective_error=float(payload.get("max_selective_error", 0.10)),
                minimum_predictions=int(payload.get("minimum_predictions", 20)),
            )
        else:
            thresholds = select_pest_thresholds(
                payload["detections"],
                classes=payload["classes"],
                ground_truth_counts=payload["ground_truth_counts"],
                minimum_precision=float(payload.get("minimum_precision", 0.85)),
                minimum_ground_truth=int(payload.get("minimum_ground_truth", 20)),
            )
        print(
            json.dumps(
                {
                    "source_sha256": hash_file(args.input),
                    "partition": "calibration",
                    "thresholds": thresholds,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    manifest = load_manifest(args.manifest)
    if args.command == "validate":
        print(
            json.dumps(
                {
                    "valid": True,
                    "canonical_manifest_sha256": canonical_manifest_hash(manifest),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "audit-manifest":
        result = audit_manifest(manifest, args.near_distance)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 2
    if args.command == "report":
        write_report(manifest, args.output)
        print(f"wrote aggregate report: {args.output}")
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())

