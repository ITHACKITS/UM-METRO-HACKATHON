"""TUAI Siaga: heavy-rain warnings from BMKG, standing water from Sentinel-1, and how long a block has been under water.

Radar change detection follows the UN-SPIDER Recommended Practice for flood mapping with Sentinel-1
(rewritten, not copied): a pass counts as flooded when its backscatter in dB divided by the pre-event
reference exceeds 1.25 (water is darker, so the negative dB value grows), on terrain flatter than 5%.
UN-SPIDER works per pixel on VH; here it runs on the field mean of VV, the band already read for the field.
"""

import math
from datetime import date, datetime
from statistics import median
from typing import Any

RATIO = 1.25  # UN-SPIDER difference threshold
MAX_SLOPE_PCT = 5.0  # UN-SPIDER masks slopes above 5%
REF_GAP_DAYS = 30  # scenes older than this, from the same orbit direction, form the pre-event reference
SUBMERGED_DAMAGE_DAYS = 5  # ordinary rice is badly damaged after about 5 days fully under water


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def radar_flood(series: list[dict], slope_deg: float | None, dat: int | None) -> dict[str, Any] | None:
    usable = [s for s in series if s["field"].get("usable") and s["field"].get("vv_db_mean") is not None]
    if len(usable) < 3:
        return None
    usable.sort(key=lambda s: s["datetime"])
    latest_t = _dt(usable[-1]["datetime"])
    flags = []
    for s in usable:
        t = _dt(s["datetime"])
        ref = [r["field"]["vv_db_mean"] for r in usable if r["orbit"] == s["orbit"] and (t - _dt(r["datetime"])).days >= REF_GAP_DAYS]
        if len(ref) < 2:
            continue
        before = median(ref)
        ratio = s["field"]["vv_db_mean"] / before if before < 0 else 0.0
        flags.append({"date": s["datetime"][:10], "orbit": s["orbit"], "vv_db": s["field"]["vv_db_mean"], "reference_db": round(before, 2), "ratio": round(ratio, 2), "flooded": ratio > RATIO})
    if not flags:
        return None
    steep = slope_deg is not None and slope_deg > 0 and 100 * math.tan(math.radians(slope_deg)) > MAX_SLOPE_PCT
    run: list[dict] = []
    for f in reversed(flags):
        if not f["flooded"]:
            break
        run.append(f)
    flooded_now = bool(run) and not steep and _dt(flags[-1]["date"] + "T00:00:00+00:00").date() == latest_t.date()
    days = (date.fromisoformat(run[0]["date"]) - date.fromisoformat(run[-1]["date"])).days if flooded_now else 0
    puddling = dat is not None and dat <= 10
    return {
        "flooded_now": flooded_now,
        "since": run[-1]["date"] if flooded_now else None,
        "days_observed": days,
        "passes": len(run) if flooded_now else 0,
        "puddling_stage": puddling,
        "slope_masked": steep,
        "history": flags[-8:],
        "method": {
            "id": f"deteksi perubahan radar ala UN-SPIDER: dB lintasan / dB acuan (median lintasan arah sama ≥{REF_GAP_DAYS} hari sebelumnya) > {RATIO}; lereng > {MAX_SLOPE_PCT:.0f}% diabaikan",
            "en": f"UN-SPIDER style radar change detection: pass dB / reference dB (median of same-direction passes ≥{REF_GAP_DAYS} days earlier) > {RATIO}; slopes > {MAX_SLOPE_PCT:.0f}% ignored",
        },
    }


def build(bmkg: dict | None, radar_series: list[dict] | None, slope_deg: float | None, dat: int | None, submergence: dict | None) -> dict[str, Any]:
    warnings: list[dict] = []
    heavy = []
    if bmkg:
        heavy = [d for d in bmkg["days"] if d["rain_mm"] >= 50]
        for d in heavy:
            warnings.append(
                {
                    "kind": "heavy_rain",
                    "level": "high" if d["rain_mm"] >= 100 else "medium",
                    "date": d["date"],
                    "text": {
                        "id": f"BMKG: hujan {d['category']['id']} {d['rain_mm']:.0f} mm pada {d['date']}. Buka saluran pembuangan dan turunkan genangan.",
                        "en": f"BMKG: {d['category']['en']} rain, {d['rain_mm']:.0f} mm on {d['date']}. Open the drains and lower the water.",
                    },
                }
            )
    rf = radar_flood(radar_series or [], slope_deg, dat)
    if rf and rf["flooded_now"] and not rf["puddling_stage"]:
        long_ = rf["days_observed"] >= SUBMERGED_DAMAGE_DAYS
        warnings.append(
            {
                "kind": "flooded",
                "level": "high" if long_ else "medium",
                "date": rf["history"][-1]["date"],
                "text": {
                    "id": f"Radar Sentinel-1: blok tergenang sejak {rf['since']} ({rf['days_observed']} hari, {rf['passes']} lintasan)."
                    + (" Sudah melewati 5 hari: padi biasa mulai rusak, buang air sekarang." if long_ else ""),
                    "en": f"Sentinel-1 radar: block under water since {rf['since']} ({rf['days_observed']} days, {rf['passes']} passes)."
                    + (" Past 5 days: ordinary rice is being damaged, drain now." if long_ else ""),
                },
            }
        )
    if submergence and submergence.get("p95", 0) >= SUBMERGED_DAMAGE_DAYS:
        warnings.append(
            {
                "kind": "submergence_forecast",
                "level": "medium",
                "date": None,
                "text": {
                    "id": f"Hitungan neraca air: padi bisa terendam penuh sampai {submergence['p95']} hari pada skenario hujan terbasah.",
                    "en": f"Water balance: the rice could be fully submerged for up to {submergence['p95']} days in the wettest scenario.",
                },
            }
        )
    level = "high" if any(w["level"] == "high" for w in warnings) else "medium" if warnings else "low"
    return {"level": level, "warnings": warnings, "bmkg": bmkg, "radar_flood": rf, "damage_threshold_days": SUBMERGED_DAMAGE_DAYS}
