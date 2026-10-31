"""Manifest loading, canonical hashing, and leakage audits."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .hashing import hamming_distance


VALID_SPLITS = {"calibration", "test", "regression", "ood"}


class ManifestError(ValueError):
    """Raised when a manifest violates a safety or reproducibility invariant."""


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_manifest(data)
    return data


def canonical_manifest_hash(manifest: dict[str, Any]) -> str:
    """Hash canonical JSON, excluding a self-referential `manifest_sha256`."""

    copy = dict(manifest)
    copy.pop("manifest_sha256", None)
    payload = json.dumps(
        copy, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "manifest_id",
        "frozen_at",
        "claim_status",
        "models",
        "records",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise ManifestError(f"missing manifest keys: {', '.join(missing)}")
    if manifest["claim_status"] not in {
        "pending",
        "not_testable",
        "experimental",
        "tested",
    }:
        raise ManifestError("invalid claim_status")
    if not isinstance(manifest["records"], list):
        raise ManifestError("records must be a list")

    seen_ids: set[str] = set()
    seen_sha: dict[str, str] = {}
    for record in manifest["records"]:
        record_required = {
            "image_id",
            "sha256",
            "perceptual_hash",
            "perceptual_hash_algorithm",
            "group_id",
            "split",
            "mode",
            "source",
            "original_label",
            "canonical_label",
            "label_status",
            "supported",
            "rights",
            "capture",
        }
        absent = sorted(record_required - record.keys())
        if absent:
            raise ManifestError(
                f"record {record.get('image_id', '<unknown>')} missing: "
                + ", ".join(absent)
            )
        image_id = record["image_id"]
        if image_id in seen_ids:
            raise ManifestError(f"duplicate image_id: {image_id}")
        seen_ids.add(image_id)
        sha = record["sha256"]
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ManifestError(f"invalid SHA-256 for {image_id}")
        if sha in seen_sha:
            raise ManifestError(
                f"exact duplicate content: {seen_sha[sha]} and {image_id}"
            )
        seen_sha[sha] = image_id
        if record["split"] not in VALID_SPLITS:
            raise ManifestError(f"invalid split for {image_id}")
        if record["mode"] not in {"disease", "pest"}:
            raise ManifestError(f"invalid mode for {image_id}")
        if record["label_status"] not in {
            "expert_reviewed",
            "source_label_only",
            "unlabelled_negative",
        }:
            raise ManifestError(f"invalid label_status for {image_id}")
        rights = record["rights"]
        if not rights.get("basis"):
            raise ManifestError(f"rights basis is required for {image_id}")
        if record["source"]["kind"] == "local" and not rights.get(
            "consent_record_held_off_git", False
        ):
            raise ManifestError(f"local image lacks off-Git consent record: {image_id}")
    declared_hash = manifest.get("manifest_sha256")
    if declared_hash and declared_hash != canonical_manifest_hash(manifest):
        raise ManifestError("manifest_sha256 does not match canonical manifest content")


def audit_manifest(
    manifest: dict[str, Any], near_duplicate_distance: int = 4
) -> dict[str, Any]:
    """Audit exact/near duplicates and group leakage across partitions."""

    validate_manifest(manifest)
    records = manifest["records"]
    group_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        group_splits[record["group_id"]].add(record["split"])
    group_leakage = [
        {"group_id": group, "splits": sorted(splits)}
        for group, splits in sorted(group_splits.items())
        if len(splits) > 1
    ]

    near_duplicates: list[dict[str, Any]] = []
    for index, first in enumerate(records):
        for second in records[index + 1 :]:
            if first["perceptual_hash_algorithm"] != second["perceptual_hash_algorithm"]:
                continue
            distance = hamming_distance(
                first["perceptual_hash"], second["perceptual_hash"]
            )
            if distance <= near_duplicate_distance:
                near_duplicates.append(
                    {
                        "first": first["image_id"],
                        "second": second["image_id"],
                        "distance": distance,
                        "cross_split": first["split"] != second["split"],
                    }
                )

    return {
        "record_count": len(records),
        "manifest_sha256": canonical_manifest_hash(manifest),
        "group_leakage": group_leakage,
        "near_duplicates": near_duplicates,
        "passed": not group_leakage
        and not any(item["cross_split"] for item in near_duplicates),
    }

