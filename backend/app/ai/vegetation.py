"""Training-free reading of the Sentinel-2 series: crop stage and anomalies.

No model is trained here, so nothing claims a learned accuracy. Three signals:
1. Transplanting date: the latest flooded, low-NDVI scene before a sustained NDVI rise.
2. Self anomaly: field NDVI against a generic transplanted-rice NDVI curve for its age.
3. Neighbour anomaly: field NDVI/NDWI against the ring of land around it in the same scene,
   which cancels most atmosphere and season effects.
"""

from datetime import date, datetime
from typing import Any

import numpy as np

# Generic irrigated lowland rice NDVI by days after transplanting, piecewise linear.
# Shape follows published Sentinel-2 paddy phenology curves (flooded start, peak near
# heading, decline at ripening); values are a reference, not a calibrated model.
CURVE = [(0, 0.20), (20, 0.40), (45, 0.70), (75, 0.80), (95, 0.72), (115, 0.45), (130, 0.30)]


REASON_ID = {
    "fewer than 3 clear scenes": "kurang dari 3 citra bersih",
    "lowest NDVI in the window, no clear flooded scene": "NDVI terendah dalam periode, tidak ada citra tergenang yang jelas",
    "no flooded or bare scene found; the season may have started before the satellite window": "tidak ada citra tergenang atau lahan terbuka; musim tanam mungkin dimulai sebelum periode citra",
    "flooded or low-NDVI scene followed by a sustained NDVI rise": "citra tergenang atau NDVI rendah lalu NDVI naik terus",
    "satellite unavailable": "citra satelit tidak tersedia",
}


def expected_ndvi(dat: int) -> float:
    xs, ys = zip(*CURVE)
    return float(np.interp(dat, xs, ys))


def _d(s: str) -> date:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


def estimate_transplanting(series: list[dict]) -> dict[str, Any]:
    pts = [(s["datetime"], s["field"]) for s in series if s["field"].get("usable")]
    if len(pts) < 3:
        return {"date": None, "days_after": None, "confidence": "none", "reason": "fewer than 3 clear scenes"}
    best = None
    for i, (t, f) in enumerate(pts[:-1]):
        later = [g["ndvi_mean"] for _, g in pts[i + 1 :]]
        flooded = f.get("water_fraction", 0) >= 0.25 or f["ndvi_mean"] < 0.3
        rises = later and max(later) - f["ndvi_mean"] >= 0.25
        if flooded and rises:
            best = (t, f)
    if not best:
        # A season can start before the window: fall back to the NDVI minimum if it is low.
        t, f = min(pts, key=lambda p: p[1]["ndvi_mean"])
        if f["ndvi_mean"] < 0.3:
            best = (t, f)
            conf = "low"
            reason = "lowest NDVI in the window, no clear flooded scene"
        else:
            return {
                "date": None,
                "days_after": None,
                "confidence": "none",
                "reason": "no flooded or bare scene found; the season may have started before the satellite window",
            }
    else:
        conf = "medium" if best[1].get("water_fraction", 0) >= 0.25 else "low"
        reason = "flooded or low-NDVI scene followed by a sustained NDVI rise"
    d = _d(best[0])
    return {
        "date": d.isoformat(),
        "days_after": (date.today() - d).days,
        "confidence": conf,
        "reason": reason,
        "ndvi_at_start": best[1]["ndvi_mean"],
    }


def anomalies(series: list[dict], dat: int | None, stage_reliable: bool = True) -> dict[str, Any]:
    pts = [s for s in series if s["field"].get("usable")]
    if not pts:
        return {"signals": [], "latest": None}
    latest = pts[-1]
    f, n = latest["field"], latest["neighbours"]
    signals = []
    out: dict[str, Any] = {"latest": latest, "signals": signals}

    if n.get("usable"):
        dv = f["ndvi_mean"] - n["ndvi_mean"]
        dw = f["ndwi_mean"] - n["ndwi_mean"]
        out["vs_neighbours"] = {"ndvi_diff": round(dv, 3), "ndwi_diff": round(dw, 3)}
        if dw <= -0.05:
            signals.append(
                {
                    "kind": "drought",
                    "weight": min(0.3, -dw * 3),
                    "text": {
                        "id": f"air tajuk (NDWI) {abs(dw):.2f} di bawah lahan sekitar",
                        "en": f"canopy water (NDWI) {abs(dw):.2f} below surrounding land",
                    },
                }
            )
        if dv <= -0.08:
            signals.append(
                {
                    "kind": "stress",
                    "weight": min(0.25, -dv * 2),
                    "text": {"id": f"NDVI {abs(dv):.2f} di bawah lahan sekitar", "en": f"NDVI {abs(dv):.2f} below surrounding land"},
                }
            )

    # Comparing with the typical curve only makes sense when the field age is trusted.
    if dat is not None and 0 <= dat <= 130 and stage_reliable:
        exp_now = expected_ndvi(dat)
        diff = f["ndvi_mean"] - exp_now
        out["vs_expected"] = {"expected": round(exp_now, 3), "observed": f["ndvi_mean"], "diff": round(diff, 3)}
        if diff <= -0.12 and dat > 15:
            signals.append(
                {
                    "kind": "stress",
                    "weight": min(0.25, -diff),
                    "text": {
                        "id": f"NDVI {abs(diff):.2f} di bawah kurva normal untuk hari ke-{dat}",
                        "en": f"NDVI {abs(diff):.2f} below the typical curve for day {dat}",
                    },
                }
            )

    if len(pts) >= 2:
        prev = pts[-2]
        days = (_d(latest["datetime"]) - _d(prev["datetime"])).days or 1
        change = f["ndvi_mean"] - prev["field"]["ndvi_mean"]
        out["recent_change"] = {"ndvi": round(change, 3), "over_days": days}
        late = dat is not None and dat >= 95
        if change <= -0.08 and not late:
            pct = change / max(prev["field"]["ndvi_mean"], 0.05)
            signals.append(
                {
                    "kind": "stress",
                    "weight": 0.15,
                    "text": {
                        "id": f"NDVI turun {abs(pct):.0%} dalam {days} hari di luar fase pemasakan",
                        "en": f"NDVI fell {abs(pct):.0%} in {days} days outside the ripening stage",
                    },
                }
            )
        if f.get("water_fraction", 0) >= 0.5 and prev["field"].get("water_fraction", 0) >= 0.5 and dat and dat > 20:
            signals.append(
                {
                    "kind": "flood",
                    "weight": 0.2,
                    "text": {
                        "id": "air terbuka di sebagian besar lahan pada dua citra bersih berturut-turut",
                        "en": "open water on most of the field in two consecutive clear scenes",
                    },
                }
            )
    return out
