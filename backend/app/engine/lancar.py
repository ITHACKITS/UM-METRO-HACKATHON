"""TUAI Lancar: which block gets irrigation water first, for the P3A chair.

Per block the FAO-56 water balance gives the water need and the day stress starts; TUAI Pantau
(Sentinel-2 vs the land around the block) is the cross-check. Both bad is red, one bad is yellow
and should be checked in the field. Red blocks that are flowering go first: rice is most sensitive
to water shortage at flowering.
"""

from datetime import date
from typing import Any

# Days from sowing to harvest, from the Balitbangtan variety descriptions (approximate).
VARIETIES = {
    "ciherang": 120,
    "inpari32": 120,
    "inpari42": 112,
    "ir64": 115,
    "mekongga": 120,
    "lainnya": 120,
}
NURSERY_DAYS = 21  # seedlings are transplanted about three weeks after sowing
RIPENING_DAYS = 30  # flowering to harvest
STRESS_WITHIN = 7
COLORS = ["merah", "kuning", "hijau"]


def days_after_transplant(planting_date: str | None, today: date | None = None) -> int | None:
    if not planting_date:
        return None
    return ((today or date.today()) - date.fromisoformat(planting_date)).days


def flowering_window(variety: str | None) -> tuple[int, int, int]:
    """(start, peak, end) of flowering in days after transplanting."""
    peak = VARIETIES.get((variety or "lainnya").lower().replace(" ", ""), 120) - RIPENING_DAYS - NURSERY_DAYS
    return peak - 10, peak, peak + 10


def assess(block: dict, a: dict) -> dict[str, Any]:
    """`a` is a services.analyze result run with this block's planting date and soil."""
    wb = a["waterbalance"]
    n = min(STRESS_WITHIN, len(wb["dates"]))
    etc = sum(e * k for e, k in zip(wb["et0"][:n], wb["kc"][:n]))
    perc = wb["params"]["percolation_mm"] * n
    rain = sum(wb["rain"]["p50"][:n])
    need_mm = max(0.0, etc + perc - rain - wb["initial_state"]["ponding_mm"])
    p_stress = max(wb["prob_stress"][:n]) if n else 0.0
    fs = wb["first_stress_day"]
    calc_bad = p_stress >= 0.5 or (fs.get("p50") is not None and fs["p50"] <= STRESS_WITHIN)

    sat_age = a["satellite"]["latest_clear_age_days"]
    signals = [s for s in a["satellite"]["anomalies"]["signals"] if s["kind"] in {"drought", "stress"}]
    pantau_known = sat_age is not None and sat_age <= 20
    pantau_bad = pantau_known and bool(signals)

    color = COLORS[0] if calc_bad and pantau_bad else COLORS[1] if calc_bad or pantau_bad else COLORS[2]
    dat = a["crop"]["days_after_transplant"]
    f0, fpeak, f1 = flowering_window(block.get("variety"))
    flowering = dat is not None and f0 <= dat <= f1

    reasons = [
        {
            "id": f"7 hari: kebutuhan air {etc:.0f} mm + rembesan {perc:.0f} mm, hujan median {rain:.0f} mm",
            "en": f"7 days: crop use {etc:.0f} mm + percolation {perc:.0f} mm, median rain {rain:.0f} mm",
        },
        {
            "id": f"peluang stres air dalam 7 hari {p_stress:.0%}" + (f", mulai hari ke-{fs['p50']}" if fs.get("p50") is not None else ""),
            "en": f"chance of water stress within 7 days {p_stress:.0%}" + (f", starting day {fs['p50']}" if fs.get("p50") is not None else ""),
        },
    ]
    if not pantau_known:
        reasons.append({"id": "TUAI Pantau: belum ada citra bersih ≤20 hari, cek langsung ke sawah", "en": "TUAI Pantau: no clear scene in 20 days, check the field"})
    elif signals:
        reasons += [s["text"] for s in signals]
    else:
        reasons.append({"id": "TUAI Pantau: tanaman tidak lebih kering dari lahan sekitar", "en": "TUAI Pantau: crop no drier than the land around it"})
    if flowering:
        reasons.append({"id": f"sedang berbunga (puncak sekitar hari ke-{fpeak} setelah tanam)", "en": f"flowering (peak around day {fpeak} after transplanting)"})

    return {
        "id": block["id"],
        "name": block.get("name"),
        "color": color,
        "flowering": flowering,
        "days_after_transplant": dat,
        "stage": a["crop"]["stage"],
        "need_mm_7d": round(need_mm, 1),
        "need_m3_7d": round(need_mm * a["field"]["area_ha"] * 10),
        "area_ha": a["field"]["area_ha"],
        "prob_stress_7d": round(p_stress, 3),
        "first_stress_p50": fs.get("p50"),
        "calc_bad": calc_bad,
        "pantau_bad": pantau_bad,
        "pantau_known": pantau_known,
        "soil": block.get("_soil"),
        "reasons": reasons,
        "check_field": color == "kuning",
    }


def rank(rows: list[dict]) -> list[dict]:
    def key(r):
        return (COLORS.index(r["color"]), not r["flowering"], -r["prob_stress_7d"], -r["need_mm_7d"])

    out = sorted(rows, key=key)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out
