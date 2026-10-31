"""Generate an aggregate evidence report without inventing unavailable metrics."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import audit_manifest, canonical_manifest_hash


DISEASE_CLASSES = [
    "bacterial_leaf_blight",
    "blast",
    "brown_spot",
    "healthy",
    "tungro",
]
PEST_CLASSES = ["rice_leaf_roller", "yellow_rice_borer", "brown_plant_hopper"]


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return lines


def build_pending_report(manifest: dict[str, Any]) -> str:
    """Build a truthful coverage report before prediction evidence is available."""

    audit = audit_manifest(manifest)
    records = manifest["records"]
    counts = Counter(
        (record["mode"], record["canonical_label"], record["split"])
        for record in records
    )
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# TUAI Sigap aggregate validation report",
        "",
        f"Generated: `{generated}`",
        f"Manifest: `{manifest['manifest_id']}`",
        f"Canonical manifest SHA-256: `{canonical_manifest_hash(manifest)}`",
        f"Evidence state: **{manifest['claim_status']}**",
        "",
        "> This report contains no project accuracy claim. No final prediction file",
        "> was supplied to this command. Model-card numbers are not substituted.",
        "",
        "## Manifest integrity",
        "",
        f"- Records: {audit['record_count']}",
        f"- Group leakage findings: {len(audit['group_leakage'])}",
        f"- Near-duplicate findings: {len(audit['near_duplicates'])}",
        f"- Audit passed: {'yes' if audit['passed'] else 'no'}",
        "",
        "## Evidence coverage",
        "",
    ]
    coverage_rows: list[list[Any]] = []
    for mode, classes in (("disease", DISEASE_CLASSES), ("pest", PEST_CLASSES)):
        for label in classes:
            calibration = counts[(mode, label, "calibration")]
            test = counts[(mode, label, "test")]
            state = "pending" if calibration or test else "not_testable"
            coverage_rows.append([mode, label, calibration, test, state])
    lines.extend(
        _table(
            ["Mode", "Class", "Calibration n", "Final-test n", "State"],
            coverage_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Required next evidence",
            "",
            "- Freeze group-separated calibration and final-test partitions.",
            "- Record the manifest hash before selecting thresholds.",
            "- Run the locked model artifacts and save prediction provenance.",
            "- Select thresholds on calibration data only; do not tune on final test.",
            "- Have a PPL/agronomist approve terminology and guidance.",
            "- Report unsupported or undersized classes as `not_testable`.",
            "",
            "## Claim boundary",
            "",
            "Results are model indications, not diagnoses. An absent pest detection",
            "does not show that a plant is safe. No pesticide product, dose, or spray",
            "schedule may be inferred from this report.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(manifest: dict[str, Any], output: str | Path) -> None:
    Path(output).write_text(build_pending_report(manifest), encoding="utf-8")

