"""TUAI Taksir: harvest estimate per block before harvest.

Season one has no real harvest weights, so the output is a class against the other blocks: below,
around or above average, from greenness (NDVI) and crop moisture (NDMI) between flowering and grain
filling, lowered by recorded events (drought, flooding, checked pest reports). Once the partners'
weighed harvests cover two seasons, a linear regression gives tonnes per hectare with a range.
Field work in Peru found that window and NDMI the strongest predictors and simple models the most
stable (Jarro-Espinal et al., 2025); district-level studies in Indonesia reach only R² ≈ 0.33
(Tribuana et al., 2026), so TUAI always shows a range, never a single exact number.
"""

from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Any

from app.engine.lancar import flowering_window

FILL_DAYS = 30  # flowering to the end of grain filling
MIN_RECORDS = 8
MIN_SEASONS = 2
FEATURES = ["ndvi", "ndmi", "events"]


def features(block: dict, a: dict, verified_reports: int) -> dict[str, Any]:
    """Season indicators for one block from its analysis and the checked Sigap reports near it."""
    planted = block.get("planting_date")
    f0, _, _ = flowering_window(block.get("variety"))
    scenes = [s for s in a["satellite"]["series"] if s["field"].get("usable")]
    window = "flowering-grainfill"
    if planted:
        start = date.fromisoformat(planted) + timedelta(days=f0)
        end = start + timedelta(days=10 + FILL_DAYS)
        sel = [s for s in scenes if start.isoformat() <= s["datetime"][:10] <= end.isoformat()]
        if not sel:
            # Before flowering: use what the season has so far and say so.
            sel = [s for s in scenes if s["datetime"][:10] >= planted][-3:]
            window = "season-so-far"
    else:
        sel = scenes[-3:]
        window = "latest-scenes"
    ndvi = [s["field"]["ndvi_mean"] for s in sel if s["field"].get("ndvi_mean") is not None]
    ndmi = [s["field"]["ndmi_mean"] for s in sel if s["field"].get("ndmi_mean") is not None]

    events = []
    if a["drought"]["risk"]["level"] == "high":
        events.append({"id": "risiko kering tinggi", "en": "high drought risk"})
    rf = (a.get("siaga") or {}).get("radar_flood") or {}
    if rf.get("days_observed", 0) >= 5 or a["flood"]["risk"]["max_submergence_days"]["p50"] >= 5:
        events.append({"id": "terendam ≥5 hari", "en": "submerged ≥5 days"})
    if verified_reports:
        events.append({"id": f"{verified_reports} laporan serangan terverifikasi", "en": f"{verified_reports} checked pest reports"})
    return {
        "ndvi": round(mean(ndvi), 3) if ndvi else None,
        "ndmi": round(mean(ndmi), 3) if ndmi else None,
        "events": len(events),
        "event_text": events,
        "scenes": len(sel),
        "window": window,
    }


def classify(rows: list[dict]) -> list[dict]:
    """Season-one classes relative to the group. `rows` items carry 'features'."""
    ok = [r for r in rows if r["features"]["ndvi"] is not None and r["features"]["ndmi"] is not None]

    def z(vals, v):
        sd = pstdev(vals)
        return 0.0 if sd < 1e-6 else (v - mean(vals)) / sd

    # Events count against the group too: a drought that hit every block does not make every block "below".
    ev_mean = mean(x["features"]["events"] for x in ok) if ok else 0.0
    for r in rows:
        f = r["features"]
        if r not in ok or len(ok) < 3:
            r["class"] = None
            r["class_reason"] = {
                "id": "butuh minimal 3 blok dengan citra bersih untuk membandingkan" if len(ok) < 3 else "belum ada citra bersih untuk blok ini",
                "en": "needs at least 3 blocks with clear scenes to compare" if len(ok) < 3 else "no clear scene for this block yet",
            }
            continue
        score = (z([x["features"]["ndvi"] for x in ok], f["ndvi"]) + z([x["features"]["ndmi"] for x in ok], f["ndmi"])) / 2 - 0.75 * (f["events"] - ev_mean)
        r["score"] = round(score, 2)
        r["class"] = "di_bawah" if score <= -0.5 else "di_atas" if score >= 0.5 else "sekitar"
        r["class_reason"] = {
            "id": f"NDVI {f['ndvi']}, NDMI {f['ndmi']} dibanding rata-rata {len(ok)} blok" + (f"; kejadian: {', '.join(e['id'] for e in f['event_text'])}" if f["events"] else ""),
            "en": f"NDVI {f['ndvi']}, NDMI {f['ndmi']} against the mean of {len(ok)} blocks" + (f"; events: {', '.join(e['en'] for e in f['event_text'])}" if f["events"] else ""),
        }
    return rows


def fit(harvests: list[dict]) -> dict[str, Any] | None:
    """Linear regression on weighed harvests, once there are enough records over two seasons."""
    rec = [h for h in harvests if all(h["features"].get(k) is not None for k in FEATURES)]
    if len(rec) < MIN_RECORDS or len({h["season"] for h in rec}) < MIN_SEASONS:
        return None
    import numpy as np
    from sklearn.linear_model import LinearRegression

    X = np.array([[h["features"][k] for k in FEATURES] for h in rec], dtype=float)
    y = np.array([h["yield_t_ha"] for h in rec], dtype=float)
    m = LinearRegression().fit(X, y)
    resid = y - m.predict(X)
    rmse = float(np.sqrt(np.mean(resid**2)))
    return {
        "model": m,
        "n": len(rec),
        "seasons": sorted({h["season"] for h in rec}),
        "rmse_t_ha": round(rmse, 2),
        "r2_in_sample": round(float(m.score(X, y)), 2),
        "coef": dict(zip(FEATURES, [round(float(c), 3) for c in m.coef_])),
    }


def predict(fitted: dict, f: dict) -> dict[str, Any] | None:
    if any(f.get(k) is None for k in FEATURES):
        return None
    p = float(fitted["model"].predict([[f[k] for k in FEATURES]])[0])
    # About an 80% band from the in-sample error; widened later with held-out seasons.
    half = 1.28 * fitted["rmse_t_ha"]
    return {"t_ha": round(p, 2), "low": round(max(0.0, p - half), 2), "high": round(p + half, 2)}
