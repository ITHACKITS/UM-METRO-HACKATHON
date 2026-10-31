"""Soil type per block: entered by the P3A chair, or read from ISRIC SoilGrids (CC BY 4.0) when left blank.

Water-holding values are mid-points of the FAO-56 Table 19 ranges. Percolation under puddled paddy
is a starting assumption per texture, to be checked in the pilot.
"""

from typing import Any

from app.ingest.http import SourceUnavailable, fetch_json

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"

# theta_fc, theta_wp (m3/m3, FAO-56 Table 19 mid-points) and percolation while ponded (mm/day, assumption).
SOILS: dict[str, dict[str, Any]] = {
    "clay": {"name": {"id": "Liat", "en": "Clay"}, "theta_fc": 0.36, "theta_wp": 0.22, "percolation_mm": 2.0},
    "clay_loam": {"name": {"id": "Lempung berliat", "en": "Clay loam"}, "theta_fc": 0.36, "theta_wp": 0.20, "percolation_mm": 3.0},
    "silt_loam": {"name": {"id": "Lempung berdebu", "en": "Silt loam"}, "theta_fc": 0.29, "theta_wp": 0.15, "percolation_mm": 4.0},
    "loam": {"name": {"id": "Lempung", "en": "Loam"}, "theta_fc": 0.25, "theta_wp": 0.12, "percolation_mm": 5.0},
    "sandy_loam": {"name": {"id": "Lempung berpasir", "en": "Sandy loam"}, "theta_fc": 0.23, "theta_wp": 0.11, "percolation_mm": 8.0},
}
DEFAULT = "clay_loam"


def texture(clay: float, sand: float, silt: float) -> str:
    """USDA texture triangle, collapsed to the five classes above (percentages)."""
    if clay >= 40:
        return "clay"
    if clay >= 27:
        return "clay_loam"
    if silt >= 50:
        return "silt_loam"
    if sand >= 52:
        return "sandy_loam"
    return "loam"


def soilgrids(lat: float, lon: float) -> dict[str, Any]:
    payload, captured = fetch_json(
        "soilgrids",
        URL,
        params={"lon": round(lon, 4), "lat": round(lat, 4), "property": ["clay", "sand", "silt"], "depth": ["0-5cm", "5-15cm", "15-30cm"], "value": "mean"},
        ttl=86400 * 30,
        timeout=30,
    )
    vals: dict[str, float] = {}
    for layer in payload.get("properties", {}).get("layers", []):
        means = [d["values"].get("mean") for d in layer.get("depths", []) if d["values"].get("mean") is not None]
        if means:
            # SoilGrids stores texture fractions in g/kg.
            vals[layer["name"]] = sum(means) / len(means) / 10
    if not {"clay", "sand", "silt"} <= vals.keys():
        raise SourceUnavailable("soilgrids", "no texture values at this point")
    return {
        "class": texture(vals["clay"], vals["sand"], vals["silt"]),
        "clay_pct": round(vals["clay"], 1),
        "sand_pct": round(vals["sand"], 1),
        "silt_pct": round(vals["silt"], 1),
        "captured_at": captured,
        "source": "ISRIC SoilGrids 2.0, 0-30 cm (CC BY 4.0)",
    }


def resolve(soil: str | None, lat: float, lon: float) -> dict[str, Any]:
    """Soil class with its basis: the P3A entry first, then SoilGrids, then the default."""
    if soil in SOILS:
        return {"class": soil, **SOILS[soil], "basis": {"id": "diisi ketua P3A", "en": "entered by the P3A chair"}}
    try:
        sg = soilgrids(lat, lon)
        return {**sg, **SOILS[sg["class"]], "basis": {"id": f"SoilGrids: liat {sg['clay_pct']}%, pasir {sg['sand_pct']}%", "en": f"SoilGrids: clay {sg['clay_pct']}%, sand {sg['sand_pct']}%"}}
    except SourceUnavailable as e:
        return {
            "class": DEFAULT,
            **SOILS[DEFAULT],
            "basis": {"id": f"nilai bawaan (SoilGrids tidak tersedia: {e.reason})", "en": f"default value (SoilGrids unavailable: {e.reason})"},
        }
