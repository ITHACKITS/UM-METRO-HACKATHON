"""BMKG public 3-day forecast (api.bmkg.go.id), the official source TUAI Siaga cites.

BMKG serves forecasts per village (adm4 code), not per coordinate, so the field is matched to the
nearest village in config/bmkg_adm4.json. BMKG requires attribution: "Sumber: BMKG".
"""

import json
import math
from typing import Any

from app.config import BACKEND_DIR
from app.ingest.http import SourceUnavailable, fetch_json

URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
MAX_KM = 15.0
# BMKG daily rainfall categories (mm/day).
CATEGORIES = [
    (150, "ekstrem", "extreme"),
    (100, "sangat lebat", "very heavy"),
    (50, "lebat", "heavy"),
    (20, "sedang", "moderate"),
    (0.5, "ringan", "light"),
]


def _areas() -> list[dict]:
    f = BACKEND_DIR / "config" / "bmkg_adm4.json"
    return json.loads(f.read_text(encoding="utf-8"))["areas"]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def nearest_area(lat: float, lon: float) -> tuple[dict, float]:
    best = min(_areas(), key=lambda a: _km(lat, lon, a["lat"], a["lon"]))
    return best, _km(lat, lon, best["lat"], best["lon"])


def category(mm: float) -> dict[str, str] | None:
    for lo, cid, cen in CATEGORIES:
        if mm >= lo:
            return {"id": cid, "en": cen}
    return None


def forecast(lat: float, lon: float) -> dict[str, Any]:
    area, km = nearest_area(lat, lon)
    if km > MAX_KM:
        raise SourceUnavailable("bmkg", f"no BMKG village code within {MAX_KM:.0f} km (nearest {area['desa']}, {km:.0f} km); add it to config/bmkg_adm4.json")
    payload, captured = fetch_json("bmkg", URL, params={"adm4": area["adm4"]}, ttl=3 * 3600)
    blocks = (payload.get("data") or [{}])[0].get("cuaca") or []
    steps = [s for day in blocks for s in day]
    if not steps:
        raise SourceUnavailable("bmkg", "BMKG returned no forecast steps")
    daily: dict[str, dict[str, Any]] = {}
    for s in steps:
        d = s["local_datetime"][:10]
        rec = daily.setdefault(d, {"date": d, "rain_mm": 0.0, "max_3h_mm": 0.0, "weather": []})
        tp = float(s.get("tp") or 0)
        rec["rain_mm"] += tp
        rec["max_3h_mm"] = max(rec["max_3h_mm"], tp)
        desc = s.get("weather_desc")
        if desc and desc not in rec["weather"]:
            rec["weather"].append(desc)
    days = []
    for d in sorted(daily.values(), key=lambda r: r["date"]):
        d["rain_mm"] = round(d["rain_mm"], 1)
        d["category"] = category(d["rain_mm"])
        days.append(d)
    return {
        "area": {**area, "distance_km": round(km, 1)},
        "days": days,
        "steps": [
            {"time": s["local_datetime"], "rain_mm": s.get("tp"), "weather": s.get("weather_desc"), "temp_c": s.get("t"), "rh": s.get("hu")}
            for s in steps
        ],
        "captured_at": captured,
        "source": "BMKG Prakiraan Cuaca Terbuka (api.bmkg.go.id). Sumber: BMKG",
    }
