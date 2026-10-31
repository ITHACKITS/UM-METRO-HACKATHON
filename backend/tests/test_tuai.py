from datetime import date, timedelta

import pytest

from app.engine import lancar, siaga, taksir
from app.ingest import bmkg, soil
from app.sigap import models as sigap_models
from app.sigap import reports

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[105.3350, -5.1000], [105.3379, -5.1000], [105.3379, -5.0971], [105.3350, -5.0971], [105.3350, -5.1000]]],
}


def _s1(day: str, db: float, orbit: str = "ascending") -> dict:
    return {"datetime": f"{day}T11:00:00Z", "orbit": orbit, "field": {"usable": True, "vv_db_mean": db}}


def test_bmkg_categories_follow_daily_thresholds():
    assert bmkg.category(0.2) is None
    assert bmkg.category(10)["id"] == "ringan"
    assert bmkg.category(55)["id"] == "lebat"
    assert bmkg.category(120)["id"] == "sangat lebat"
    assert bmkg.category(160)["id"] == "ekstrem"


def test_bmkg_picks_nearest_metro_village():
    area, km = bmkg.nearest_area(-5.0995, 105.336)
    assert area["kotkab"] == "Kota Metro"
    assert km < 3


def test_radar_flood_uses_unspider_ratio_and_counts_days():
    series = [_s1("2026-08-01", -12), _s1("2026-08-13", -12.5), _s1("2026-08-25", -11.8), _s1("2026-10-20", -17), _s1("2026-10-27", -18)]
    rf = siaga.radar_flood(series, slope_deg=0.5, dat=60)
    assert rf["flooded_now"] is True
    assert rf["since"] == "2026-10-20"
    assert rf["days_observed"] == 7
    assert rf["history"][-1]["ratio"] > siaga.RATIO


def test_radar_flood_ignored_on_steep_land():
    series = [_s1("2026-08-01", -12), _s1("2026-08-13", -12), _s1("2026-10-27", -18)]
    assert siaga.radar_flood(series, slope_deg=5.0, dat=60)["flooded_now"] is False


def test_siaga_warns_on_bmkg_heavy_rain_and_long_flood():
    bm = {"days": [{"date": "2026-11-01", "rain_mm": 110.0, "category": {"id": "sangat lebat", "en": "very heavy"}}]}
    series = [_s1("2026-08-01", -12), _s1("2026-08-13", -12), _s1("2026-10-20", -17), _s1("2026-10-27", -18)]
    out = siaga.build(bm, series, 0.5, 60, {"p50": 0, "p95": 2})
    kinds = {w["kind"] for w in out["warnings"]}
    assert kinds == {"heavy_rain", "flooded"}
    assert out["level"] == "high"


def test_soil_texture_classes():
    assert soil.texture(45, 20, 35) == "clay"
    assert soil.texture(30, 30, 40) == "clay_loam"
    assert soil.texture(10, 20, 70) == "silt_loam"
    assert soil.texture(10, 65, 25) == "sandy_loam"
    assert soil.texture(18, 40, 42) == "loam"
    assert soil.resolve("loam", -5.1, 105.3)["basis"]["id"] == "diisi ketua P3A"


def test_flowering_window_scales_with_variety():
    assert lancar.flowering_window("Ciherang") == (59, 69, 79)
    assert lancar.flowering_window("inpari42")[1] == 61
    assert lancar.days_after_transplant((date.today() - timedelta(days=30)).isoformat()) == 30


def _analysis(p_stress: float, signals: list, dat: int, sat_age: int = 5) -> dict:
    n = 10
    return {
        "field": {"area_ha": 2.0},
        "crop": {"days_after_transplant": dat, "stage": "mid-season"},
        "satellite": {"latest_clear_age_days": sat_age, "anomalies": {"signals": signals}},
        "waterbalance": {
            "dates": [f"d{i}" for i in range(n)],
            "et0": [5.0] * n,
            "kc": [1.2] * n,
            "rain": {"p50": [0.0] * n},
            "prob_stress": [p_stress] * n,
            "first_stress_day": {"p50": 3 if p_stress >= 0.5 else None},
            "params": {"percolation_mm": 3.0},
            "initial_state": {"ponding_mm": 0.0},
        },
    }


def test_lancar_colors_and_flowering_first():
    dry_sig = [{"kind": "drought", "weight": 0.2, "text": {"id": "x", "en": "x"}}]
    rows = [
        lancar.assess({"id": "a", "variety": "ciherang"}, _analysis(0.8, dry_sig, 30)),
        lancar.assess({"id": "b", "variety": "ciherang"}, _analysis(0.8, dry_sig, 70)),
        lancar.assess({"id": "c", "variety": "ciherang"}, _analysis(0.8, [], 70)),
        lancar.assess({"id": "d", "variety": "ciherang"}, _analysis(0.0, [], 70)),
    ]
    assert [r["color"] for r in rows] == ["merah", "merah", "kuning", "hijau"]
    order = lancar.rank(rows)
    assert [r["id"] for r in order] == ["b", "a", "c", "d"]
    assert order[0]["flowering"] is True
    # 7 days x (5 x 1.2 + 3) mm over 2 ha
    assert order[0]["need_mm_7d"] == pytest.approx(63.0)
    assert order[0]["need_m3_7d"] == 1260


def test_lancar_stale_satellite_is_not_counted_as_bad():
    r = lancar.assess({"id": "a"}, _analysis(0.8, [{"kind": "drought", "weight": 0.2, "text": {}}], 30, sat_age=40))
    assert r["pantau_known"] is False
    assert r["color"] == "kuning"


def test_taksir_classes_against_group():
    rows = [{"features": {"ndvi": v, "ndmi": m, "events": e, "event_text": []}} for v, m, e in [(0.8, 0.4, 0), (0.6, 0.2, 0), (0.7, 0.3, 0), (0.7, 0.3, 1)]]
    taksir.classify(rows)
    assert rows[0]["class"] == "di_atas"
    assert rows[1]["class"] == "di_bawah"
    assert rows[2]["class"] == "sekitar"
    assert rows[3]["class"] == "di_bawah"


def test_taksir_needs_three_blocks():
    rows = [{"features": {"ndvi": 0.7, "ndmi": 0.3, "events": 0, "event_text": []}}] * 2
    taksir.classify(rows)
    assert rows[0]["class"] is None


def test_taksir_regression_needs_two_seasons():
    one = [{"season": "MT1", "yield_t_ha": 6.0, "features": {"ndvi": 0.7, "ndmi": 0.3, "events": 0}}] * 10
    assert taksir.fit(one) is None
    recs = []
    for i in range(10):
        ndvi = 0.55 + 0.03 * i
        recs.append({"season": f"MT{1 + i % 2}", "yield_t_ha": 2 + 6 * ndvi - 0.5 * (i % 3 == 0), "features": {"ndvi": ndvi, "ndmi": 0.2 + 0.01 * i, "events": int(i % 3 == 0)}})
    fitted = taksir.fit(recs)
    assert fitted and fitted["n"] == 10
    p = taksir.predict(fitted, {"ndvi": 0.7, "ndmi": 0.3, "events": 0})
    assert p["low"] <= p["t_ha"] <= p["high"]


def test_sigap_warning_needs_enough_verified_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(reports, "DIR", tmp_path)
    monkeypatch.setattr(reports, "FILE", tmp_path / "reports.json")
    monkeypatch.setattr(reports, "PHOTOS", tmp_path / "photos")
    a = reports.create({"lat": -5.1, "lon": 105.3, "label": "wereng"}, None)
    b = reports.create({"lat": -5.1005, "lon": 105.3, "label": "wereng"}, None)
    reports.create({"lat": -5.2, "lon": 105.3, "label": "wereng"}, None)
    block = [{"id": "x", "lat": -5.1002, "lon": 105.3}]
    assert reports.warnings(block)["blocks"]["x"]["warning"] is False  # still pending PPL check
    reports.review(a["id"], "verified", None, "PPL", "")
    reports.review(b["id"], "verified", None, "PPL", "")
    w = reports.warnings(block)["blocks"]["x"]
    assert w["warning"] is True and w["triggered"] == ["wereng"]


def test_sigap_low_confidence_goes_to_ppl(monkeypatch):
    from PIL import Image

    monkeypatch.setattr(sigap_models, "decode", lambda data: (Image.new("RGB", (100, 100)), b""))
    monkeypatch.setattr(sigap_models, "disease", lambda img: {"status": "ok", "top": {"key": "blas", "label": "Blast", "confidence": 0.55}})
    monkeypatch.setattr(sigap_models, "symptoms", lambda img: {"status": "unavailable", "reason": "not trained"})
    r = sigap_models.analyze("x", "daun")
    assert r["finding"]["key"] == "blas"
    assert r["needs_review"] is True


def test_sigap_disease_label_mapping():
    assert sigap_models._disease_key("Bacterialblight") == "kresek"
    assert sigap_models._disease_key("Brownspot") == "bercak_coklat"
    assert sigap_models._disease_key("Healthy") == "sehat"
