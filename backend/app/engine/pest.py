"""Weather suitability for major rice pests and diseases.

These are suitability indices built from published favourable-condition ranges,
not detections. A high level means the weather favours outbreaks and the field
should be scouted; it does not mean the pest is present.
"""

from typing import Any

RULES: dict[str, dict[str, Any]] = {
    "blast": {
        "name": {"id": "Blas (Pyricularia oryzae)", "en": "Rice blast (Pyricularia oryzae)"},
        "favourable": "RH ≥ 90% (long leaf wetness) and night temperature 20-26 °C",
        "reference": "IRRI Rice Knowledge Bank, 'Blast (leaf and collar)'",
        "stages": {"development", "mid-season"},
    },
    "blb": {
        "name": {"id": "Hawar daun bakteri (Xanthomonas oryzae)", "en": "Bacterial leaf blight (Xanthomonas oryzae)"},
        "favourable": "mean temperature 25-34 °C, RH ≥ 80%, plus heavy rain ≥ 20 mm or strong wind ≥ 30 km/h that wounds leaves",
        "reference": "IRRI Rice Knowledge Bank, 'Bacterial blight'",
        "stages": {"development", "mid-season", "late-season"},
    },
    "bph": {
        "name": {"id": "Wereng batang cokelat (Nilaparvata lugens)", "en": "Brown planthopper (Nilaparvata lugens)"},
        "favourable": "mean temperature 25-30 °C with RH ≥ 80%; dense canopy (NDVI ≥ 0.6) raises the level",
        "reference": "IRRI Rice Knowledge Bank, 'Planthopper'",
        "stages": {"development", "mid-season", "late-season"},
    },
    "stemborer": {
        "name": {"id": "Penggerek batang (Scirpophaga incertulas)", "en": "Yellow stem borer (Scirpophaga incertulas)"},
        "favourable": "mean temperature 24-30 °C with rain on at least a third of days (moth activity)",
        "reference": "IRRI Rice Knowledge Bank, 'Stem borer'",
        "stages": {"initial", "development", "mid-season"},
    },
}


def _day_flags(d: dict[str, float | None], ndvi: float | None) -> dict[str, bool]:
    t, tmin, rh = d.get("tmean"), d.get("tmin"), d.get("rh")
    rain, wind = d.get("rain") or 0.0, d.get("wind") or 0.0
    if t is None or rh is None:
        return {}
    return {
        "blast": rh >= 90 and tmin is not None and 20 <= tmin <= 26,
        "blb": 25 <= t <= 34 and rh >= 80 and (rain >= 20 or wind >= 30),
        "bph": 25 <= t <= 30 and rh >= 80,
        "stemborer": 24 <= t <= 30 and rain >= 1,
    }


def assess(days: list[dict], stage: str, ndvi: float | None) -> list[dict]:
    """`days` is a list of {date, tmean, tmin, rh, rain, wind} for the window to judge."""
    out = []
    counts = {k: 0 for k in RULES}
    usable = 0
    for d in days:
        flags = _day_flags(d, ndvi)
        if not flags:
            continue
        usable += 1
        for k, v in flags.items():
            counts[k] += int(v)
    for key, rule in RULES.items():
        if usable == 0:
            out.append(
                {
                    "id": key,
                    **rule,
                    "level": "unknown",
                    "reason": {"id": "tidak ada data cuaca untuk periode ini", "en": "no weather data for the window"},
                }
            )
            continue
        share = counts[key] / usable
        if key == "stemborer":
            score = 2 if share >= 0.6 else 1 if share >= 0.33 else 0
        else:
            score = 2 if share >= 0.5 else 1 if share >= 0.25 else 0
        if key == "bph" and ndvi is not None and ndvi >= 0.6 and score < 2:
            score += 1
        in_stage = stage in rule["stages"] or stage == "unknown"
        if not in_stage and score > 0:
            score -= 1
        level = ["low", "medium", "high"][score]
        reason = {
            "id": f"{counts[key]} dari {usable} hari memenuhi kisaran cuaca yang disukai",
            "en": f"{counts[key]} of {usable} days met the favourable range",
        }
        if key == "bph" and ndvi is not None:
            reason = {k: v + (f"; NDVI lahan {ndvi:.2f}" if k == "id" else f"; field NDVI {ndvi:.2f}") for k, v in reason.items()}
        if not in_stage:
            reason = {
                "id": reason["id"] + f"; fase sekarang ({stage}) kurang rentan",
                "en": reason["en"] + f"; current stage ({stage}) is less susceptible",
            }
        out.append(
            {
                "id": key,
                "name": rule["name"],
                "favourable": rule["favourable"],
                "reference": rule["reference"],
                "level": level,
                "favourable_days": counts[key],
                "window_days": usable,
                "reason": reason,
            }
        )
    return out
