"""Daily paddy water balance, FAO-56 style, with a ponding layer on top of the root zone.

State per day: ponding depth h (mm) above the soil and root-zone depletion Dr (mm).
While water is ponded the crop transpires at Kc * ET0 and the field loses water to
percolation. Once ponding is gone, the root zone depletes; stress starts when Dr
exceeds the readily available water (RAW) and Ks falls below 1 (FAO-56 eq. 84).
"""

from dataclasses import asdict, dataclass, field

import numpy as np

# FAO-56 Table 12 (rice) and Table 11 stage lengths scaled to a ~120-day variety
# such as Ciherang or Inpari 32, counted from transplanting.
STAGES = [("initial", 0, 25), ("development", 25, 55), ("mid-season", 55, 95), ("late-season", 95, 120)]
KC_INI, KC_MID, KC_END = 1.05, 1.20, 0.90
# Approximate canopy height used for the full-submergence test, mm.
PLANT_HEIGHT = [(0, 200), (20, 400), (45, 650), (70, 850), (200, 950)]


@dataclass
class FieldParams:
    days_after_transplant: int | None = 30
    theta_fc: float = 0.36  # field capacity, m3/m3 (clay loam default; see docs/DECISIONS.md)
    theta_wp: float = 0.20  # wilting point
    root_depth_m: float = 0.40
    p_depletion: float = 0.20  # FAO-56 Table 22, rice
    percolation_mm: float = 3.0  # seepage + percolation while ponded, puddled soil
    outlet_mm: float = 100.0  # spillway / outlet height kept by the farmer
    bund_mm: float = 250.0
    drainage_mm_day: float = 30.0  # field outlet capacity above the outlet height
    overflow_mm_day: float = 120.0  # loss rate once water tops the bunds
    irrigation_mm_day: float = 0.0  # 0 = rainfed, worst case for drought
    runon_factor: float = 0.0  # extra runoff from upslope, multiple of field-own SCS runoff
    curve_number: float = 85.0

    @property
    def taw(self) -> float:
        return 1000 * (self.theta_fc - self.theta_wp) * self.root_depth_m

    @property
    def raw(self) -> float:
        return self.p_depletion * self.taw


@dataclass
class InitialState:
    ponding_mm: float = 0.0
    depletion_mm: float = 0.0
    basis: list[dict] = field(default_factory=list)


def stage_for(dat: int | None) -> str:
    if dat is None:
        return "unknown"
    if dat < 0:
        return "nursery"
    for name, a, b in STAGES:
        if a <= dat < b:
            return name
    return "harvest-ready"


def kc_for(dat: int | None) -> float:
    if dat is None:
        return 1.10
    if dat < 25:
        return KC_INI
    if dat < 55:
        return KC_INI + (KC_MID - KC_INI) * (dat - 25) / 30
    if dat < 95:
        return KC_MID
    if dat < 120:
        return KC_MID + (KC_END - KC_MID) * (dat - 95) / 25
    return KC_END


def plant_height_mm(dat: int | None) -> float:
    if dat is None:
        return 650.0
    h = PLANT_HEIGHT[0][1]
    for d, v in PLANT_HEIGHT:
        if dat >= d:
            h = v
    return float(h)


def scs_runoff(p: float, cn: float) -> float:
    s = 25400 / cn - 254
    ia = 0.2 * s
    return (p - ia) ** 2 / (p - ia + s) if p > ia else 0.0


def run(rain: list[float], et0: list[float], params: FieldParams, init: InitialState) -> dict:
    h, dr = init.ponding_mm, init.depletion_mm
    taw, raw = params.taw, params.raw
    out = {k: [] for k in ("ponding", "depletion", "ks", "etc", "kc", "dat", "runon")}
    for i, (p, e) in enumerate(zip(rain, et0)):
        dat = None if params.days_after_transplant is None else params.days_after_transplant + i
        kc = kc_for(dat)
        runon = params.runon_factor * scs_runoff(p, params.curve_number)
        inflow = p + params.irrigation_mm_day + runon
        ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / (taw - raw))
        etc = kc * e * (ks if h <= 0 else 1.0)

        if h > 0 or dr <= 0:
            h += inflow - etc - params.percolation_mm
            if h < 0:
                dr += -h
                h = 0.0
        else:
            dr -= inflow
            if dr < 0:
                h, dr = -dr, 0.0
            dr += etc
        if h > params.bund_mm:
            h -= min(h - params.bund_mm, params.overflow_mm_day)
        if h > params.outlet_mm:
            h -= min(h - params.outlet_mm, params.drainage_mm_day)
        dr = min(max(dr, 0.0), taw)
        ks = 1.0 if dr <= raw else max(0.0, (taw - dr) / (taw - raw))
        out["ponding"].append(round(h, 1))
        out["depletion"].append(round(dr, 1))
        out["ks"].append(round(ks, 3))
        out["etc"].append(round(etc, 2))
        out["kc"].append(round(kc, 3))
        out["dat"].append(dat)
        out["runon"].append(round(runon, 1))
    return out


def ensemble_run(rain_members: list[list[float]], et0: list[float], params: FieldParams, init: InitialState, dates: list[str]) -> dict:
    runs = [run(m, et0[: len(m)], params, init) for m in rain_members]
    n = min(len(r["ks"]) for r in runs)
    ks = np.array([r["ks"][:n] for r in runs])
    pond = np.array([r["ponding"][:n] for r in runs])
    depl = np.array([r["depletion"][:n] for r in runs])
    rain = np.array([m[:n] for m in rain_members])
    heights = np.array([plant_height_mm(runs[0]["dat"][i]) for i in range(n)])

    stressed = ks < 1.0
    severe = ks < 0.6
    first_stress = []
    for row in stressed:
        idx = np.argmax(row) if row.any() else None
        first_stress.append(None if idx is None else int(idx))
    submerged = pond >= heights[None, :]
    # Longest run of full-submergence days per member.
    sub_runs = []
    for row in submerged:
        best = cur = 0
        for v in row:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        sub_runs.append(best)

    def pct(a, q):
        return np.percentile(a, q, axis=0).round(2).tolist()

    fs = [d for d in first_stress if d is not None]
    return {
        "dates": dates[:n],
        "members": len(runs),
        "ponding": {"p5": pct(pond, 5), "p50": pct(pond, 50), "p95": pct(pond, 95)},
        "depletion": {"p5": pct(depl, 5), "p50": pct(depl, 50), "p95": pct(depl, 95)},
        "ks": {"p5": pct(ks, 5), "p50": pct(ks, 50), "p95": pct(ks, 95)},
        "rain": {"p5": pct(rain, 5), "p50": pct(rain, 50), "p95": pct(rain, 95)},
        "prob_stress": stressed.mean(axis=0).round(3).tolist(),
        "prob_severe": severe.mean(axis=0).round(3).tolist(),
        "prob_submerged": submerged.mean(axis=0).round(3).tolist(),
        "plant_height_mm": heights.tolist(),
        "first_stress_day": {
            "share_of_members": round(len(fs) / len(runs), 3),
            "p5": None if not fs else int(np.percentile(fs, 5)),
            "p50": None if not fs else int(np.percentile(fs, 50)),
            "p95": None if not fs else int(np.percentile(fs, 95)),
        },
        "max_submergence_days": {
            "p50": int(np.percentile(sub_runs, 50)),
            "p95": int(np.percentile(sub_runs, 95)),
            "share_any": round(float(np.mean([s > 0 for s in sub_runs])), 3),
        },
        "kc": runs[0]["kc"][:n],
        "dat": runs[0]["dat"][:n],
        "params": asdict(params) | {"taw_mm": round(params.taw, 1), "raw_mm": round(params.raw, 1)},
    }


def initial_state(
    params: FieldParams,
    soil_theta: float | None,
    water_fraction: float | None,
    sat_age_days: int | None,
    sensor: tuple[str, str] = ("citra Sentinel-2 bersih", "clear Sentinel-2 scene"),
) -> InitialState:
    basis: list[dict] = []
    dr = 0.0
    if soil_theta is not None:
        dr = max(0.0, min(params.taw, 1000 * (params.theta_fc - soil_theta) * params.root_depth_m))
        basis.append(
            {
                "id": f"kekurangan air zona akar {dr:.0f} mm dari kelembapan tanah model {soil_theta:.3f} m³/m³ (9-27 cm)",
                "en": f"root-zone depletion {dr:.0f} mm from modelled soil moisture {soil_theta:.3f} m³/m³ (9-27 cm)",
            }
        )
    h = 0.0
    if water_fraction is not None and sat_age_days is not None and sat_age_days <= 12:
        h = round(50.0 * water_fraction, 1)
        basis.append(
            {
                "id": f"genangan {h:.0f} mm diasumsikan dari {water_fraction:.0%} piksel air terbuka pada {sensor[0]} berumur {sat_age_days} hari",
                "en": f"ponding {h:.0f} mm assumed from {water_fraction:.0%} open-water pixels in a {sat_age_days}-day-old {sensor[1]}",
            }
        )
        if h > 0:
            dr = 0.0
    else:
        basis.append(
            {
                "id": "tidak ada citra satelit bersih terbaru: genangan dimulai dari 0 mm (asumsi hati-hati untuk kekeringan)",
                "en": "no recent clear satellite scene: ponding starts at 0 mm (conservative for drought)",
            }
        )
    return InitialState(ponding_mm=h, depletion_mm=dr, basis=basis)
