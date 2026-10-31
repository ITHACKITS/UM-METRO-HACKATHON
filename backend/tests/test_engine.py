import pytest

from app.ai import vegetation
from app.engine import pest
from app.engine.waterbalance import FieldParams, InitialState, ensemble_run, initial_state, kc_for, run, scs_runoff, stage_for
from app.services import FieldError, validate_field

SQUARE_10HA = {
    "type": "Polygon",
    "coordinates": [[[105.3350, -5.1000], [105.3379, -5.1000], [105.3379, -5.0971], [105.3350, -5.0971], [105.3350, -5.1000]]],
}


def test_kc_follows_fao56_rice_curve():
    assert kc_for(0) == pytest.approx(1.05)
    assert kc_for(70) == pytest.approx(1.20)
    assert kc_for(120) == pytest.approx(0.90)
    assert 1.05 < kc_for(40) < 1.20


def test_stage_names():
    assert stage_for(None) == "unknown"
    assert stage_for(-5) == "nursery"
    assert stage_for(10) == "initial"
    assert stage_for(60) == "mid-season"
    assert stage_for(130) == "harvest-ready"


def test_scs_runoff_zero_below_initial_abstraction():
    assert scs_runoff(5, 85) == 0.0
    assert scs_runoff(100, 85) > 40


def test_no_rain_depletes_and_stresses():
    p = FieldParams(days_after_transplant=40)
    out = run([0.0] * 30, [5.0] * 30, p, InitialState(ponding_mm=20))
    assert out["ponding"][0] < 20
    assert out["ks"][-1] < 1.0
    assert out["depletion"][-1] <= p.taw


def test_heavy_rain_ponds_and_drains_to_outlet():
    p = FieldParams(days_after_transplant=10, runon_factor=0)
    out = run([200.0] + [0.0] * 10, [4.0] * 11, p, InitialState(ponding_mm=50))
    assert max(out["ponding"]) <= p.bund_mm
    assert out["ponding"][-1] <= p.outlet_mm


def test_ensemble_percentiles_ordered():
    members = [[0.0] * 15, [5.0] * 15, [20.0] * 15]
    r = ensemble_run(members, [4.5] * 15, FieldParams(days_after_transplant=30), InitialState(), [f"d{i}" for i in range(15)])
    for i in range(15):
        assert r["ponding"]["p5"][i] <= r["ponding"]["p50"][i] <= r["ponding"]["p95"][i]
    assert 0 <= r["first_stress_day"]["share_of_members"] <= 1
    assert r["members"] == 3


def test_initial_state_ignores_stale_satellite():
    p = FieldParams()
    s = initial_state(p, 0.30, water_fraction=0.9, sat_age_days=40)
    assert s.ponding_mm == 0.0
    assert any("no recent" in b["en"] for b in s.basis)


def test_pest_unknown_without_weather():
    out = pest.assess([], "mid-season", None)
    assert all(p["level"] == "unknown" for p in out)


def test_pest_blast_high_in_humid_cool_nights():
    days = [{"tmean": 25, "tmin": 22, "rh": 95, "rain": 3, "wind": 10} for _ in range(7)]
    levels = {p["id"]: p["level"] for p in pest.assess(days, "development", 0.5)}
    assert levels["blast"] == "high"


def test_transplanting_needs_three_clear_scenes():
    r = vegetation.estimate_transplanting([])
    assert r["date"] is None and r["confidence"] == "none"


def test_transplanting_detects_flooded_start():
    def s(day, ndvi, water):
        return {"datetime": f"2026-0{day}T03:00:00Z", "field": {"usable": True, "ndvi_mean": ndvi, "ndmi_mean": 0, "water_fraction": water}}

    series = [s("7-01", 0.6, 0.0), s("7-20", 0.15, 0.6), s("8-10", 0.4, 0.1), s("9-01", 0.7, 0.0)]
    r = vegetation.estimate_transplanting(series)
    assert r["date"] == "2026-07-20"
    assert r["confidence"] == "medium"


def test_field_validation():
    meta = validate_field(SQUARE_10HA)
    assert 9 < meta["area_ha"] < 11
    with pytest.raises(FieldError):
        validate_field({"type": "Point", "coordinates": [105.3, -5.1]})
