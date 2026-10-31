#!/usr/bin/env python3
"""Measure end-to-end warm API latency on the actual demo laptop."""

from __future__ import annotations

import argparse
import json
import mimetypes
import statistics
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot calculate a percentile without values")
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def multipart(image: Path, mode: str) -> tuple[bytes, str]:
    boundary = f"jagapadi-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(image.name)[0] or "application/octet-stream"
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"mode\"\r\n\r\n{mode}\r\n".encode(),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{image.name}\"\r\nContent-Type: {mime}\r\n\r\n"
        ).encode(),
        image.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), boundary


def analyze(url: str, image: Path, mode: str, timeout: float) -> tuple[float, dict[str, Any]]:
    body, boundary = multipart(image, mode)
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    return (time.perf_counter() - started) * 1000, payload


def resident_memory_mb(pid: int | None) -> float | None:
    if pid is None:
        return None
    status = Path(f"/proc/{pid}/status")
    if not status.is_file():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--mode", choices=("disease", "pest"), required=True)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/sigap/v1/analyze",
    )
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--server-pid", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.image.is_file():
        parser.error(f"image does not exist: {args.image}")
    if args.runs < 2:
        parser.error("--runs must be at least 2 (one cold request plus warm measurements)")

    latencies: list[float] = []
    statuses: list[str] = []
    peak_rss = resident_memory_mb(args.server_pid)
    try:
        for index in range(args.runs):
            latency, payload = analyze(args.url, args.image, args.mode, args.timeout)
            latencies.append(latency)
            statuses.append(str(payload.get("status", "missing")))
            rss = resident_memory_mb(args.server_pid)
            if rss is not None:
                peak_rss = max(peak_rss or 0, rss)
            print(f"run {index + 1}/{args.runs}: {latency:.1f} ms, status={statuses[-1]}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Benchmark failed: {exc}")
        return 1

    warm = latencies[1:]
    report = {
        "schema_version": 1,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "image_sha256_note": "Record the image in the private immutable evaluation manifest",
        "runs": args.runs,
        "cold_ms": latencies[0],
        "warm_mean_ms": statistics.fmean(warm),
        "warm_p50_ms": percentile(warm, 0.50),
        "warm_p95_ms": percentile(warm, 0.95),
        "peak_server_rss_mb": peak_rss,
        "statuses": statuses,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

