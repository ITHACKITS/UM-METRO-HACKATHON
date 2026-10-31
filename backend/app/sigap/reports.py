"""TUAI Sigap field reports: photo results and quick rat reports, checked by the PPL, shown on the village map.

A block gets a warning when enough checked planthopper or rat reports fall near it within a week.
The radius and trigger count are starting assumptions to be tuned in the pilot.
"""

import json
import math
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import DATA_DIR

DIR = DATA_DIR / "sigap"
FILE = DIR / "reports.json"
PHOTOS = DIR / "photos"
WARN_RADIUS_M = float(os.getenv("SIGAP_WARN_RADIUS_M", "500"))
WARN_MIN_REPORTS = int(os.getenv("SIGAP_WARN_MIN_REPORTS", "2"))
WARN_DAYS = int(os.getenv("SIGAP_WARN_DAYS", "7"))
SPREADING = {"wereng", "tikus"}

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> list[dict]:
    return json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []


def _save(items: list[dict]) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, FILE)


def meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(a))


def create(rec: dict[str, Any], jpeg: bytes | None) -> dict[str, Any]:
    item = {
        "id": uuid.uuid4().hex[:12],
        "created_at": _now(),
        "status": "pending",
        "review": None,
        "photo": bool(jpeg),
        **rec,
    }
    with _lock:
        if jpeg:
            PHOTOS.mkdir(parents=True, exist_ok=True)
            (PHOTOS / f"{item['id']}.jpg").write_bytes(jpeg)
        items = _load()
        items.append(item)
        _save(items)
    return item


def photo_path(rid: str):
    p = PHOTOS / f"{rid}.jpg"
    return p if rid.isalnum() and p.exists() else None


def listing(days: int = 60) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return sorted((r for r in _load() if r["created_at"] >= since), key=lambda r: r["created_at"], reverse=True)


def review(rid: str, status: str, label: str | None, reviewer: str, note: str) -> dict | None:
    with _lock:
        items = _load()
        for r in items:
            if r["id"] == rid:
                r["status"] = status
                r["review"] = {"by": reviewer, "at": _now(), "note": note, "original_label": r.get("label")}
                if label:
                    r["label"] = label
                _save(items)
                return r
    return None


def warnings(blocks: list[dict]) -> dict[str, Any]:
    """`blocks` is [{id, lat, lon}]. Returns per-block counts of nearby checked reports in the window."""
    since = (datetime.now(timezone.utc) - timedelta(days=WARN_DAYS)).isoformat()
    recent = [r for r in _load() if r["status"] == "verified" and r.get("label") in SPREADING and r["created_at"] >= since]
    out = {}
    for b in blocks:
        near = [r for r in recent if meters(b["lat"], b["lon"], r["lat"], r["lon"]) <= WARN_RADIUS_M]
        by = {}
        for r in near:
            by[r["label"]] = by.get(r["label"], 0) + 1
        hits = {k: n for k, n in by.items() if n >= WARN_MIN_REPORTS}
        out[b["id"]] = {"warning": bool(hits), "counts": by, "triggered": sorted(hits)}
    return {
        "blocks": out,
        "rule": {"radius_m": WARN_RADIUS_M, "min_reports": WARN_MIN_REPORTS, "days": WARN_DAYS, "labels": sorted(SPREADING)},
        "note": {
            "id": "Jarak dan jumlah pemicu adalah asumsi awal yang diuji saat pilot.",
            "en": "Radius and trigger count are starting assumptions tested in the pilot.",
        },
    }
