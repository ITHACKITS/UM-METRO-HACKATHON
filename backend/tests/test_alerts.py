import pytest

from app import alerts
from app.engine import verdict

SQUARE_10HA = {
    "type": "Polygon",
    "coordinates": [[[105.3350, -5.1000], [105.3379, -5.1000], [105.3379, -5.0971], [105.3350, -5.0971], [105.3350, -5.1000]]],
}


def fake_analysis(p_drought: float, p_flood: float = 0.05, pest_high: bool = False) -> dict:
    def lvl(p):
        return "high" if p >= 0.5 else "medium" if p >= 0.2 else "low"

    rec = {"feasibility": 1, "text": {"id": "Tutup bocoran pematang.", "en": "Seal bund leaks."}, "why": {"id": "", "en": ""}}
    return {
        "status": "ok",
        "confidence": "medium",
        "waterbalance": {"dates": ["2026-10-29"]},
        "drought": {
            "risk": {
                "probability": p_drought,
                "level": lvl(p_drought),
                "first_stress_day": {"p50": 8, "p5": 5, "p95": 12, "share_of_members": 0.7},
                "drivers": [{"id": "hujan median 62 mm vs kebutuhan ECMWF 68 mm", "en": "median rain 62 mm vs ECMWF need 68 mm"}],
            },
            "recommendations": [rec],
        },
        "flood": {
            "risk": {
                "probability": p_flood,
                "level": lvl(p_flood),
                "max_submergence_days": {"p50": 0, "p95": 3, "share_any": 0.1},
                "drivers": [{"id": "hari terbasah 90 mm", "en": "wettest day 90 mm"}],
            },
            "recommendations": [rec],
        },
        "pest": [
            {
                "id": "blast",
                "level": "high" if pest_high else "low",
                "name": {"id": "Blas", "en": "Blast"},
                "reason": {"id": "lembap", "en": "humid"},
                "action": {"id": "Cek daun.", "en": "Check leaves."},
            }
        ],
    }


def test_verdict_levels_and_dates():
    v = verdict.build(fake_analysis(0.72))
    assert v["status"] == "bahaya" and v["threat"] == "drought"
    assert "6 Nov" in v["headline"]["id"] and "Nov 6" in v["headline"]["en"]
    # Acronyms in the driver text survive the capitalisation.
    assert "ECMWF" in v["why"]["id"]
    assert v["today"]["id"] == "Tutup bocoran pematang."

    assert verdict.build(fake_analysis(0.3))["status"] == "waspada"
    safe = verdict.build(fake_analysis(0.05))
    assert safe["status"] == "aman" and safe["threat"] is None

    pest = verdict.build(fake_analysis(0.05, pest_high=True))
    assert pest["status"] == "waspada" and pest["threat"] == "pest"
    assert pest["today"]["id"] == "Cek daun."


def test_flood_dominates_when_more_likely():
    v = verdict.build(fake_analysis(0.1, p_flood=0.6))
    assert v["threat"] == "flood" and v["status"] == "bahaya"
    assert "3 hari" in v["why"]["id"]


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(alerts, "STORE", tmp_path / "subs.json")
    monkeypatch.setattr(alerts, "_bot_username", "jagapadi_bot")
    return tmp_path


def test_link_check_daily_and_stop(store):
    sent: list[tuple[int, str]] = []
    state = {"p": 0.72}

    def send(chat, text):
        sent.append((chat, text))

    def analyze(geom, opts):
        a = fake_analysis(state["p"])
        return a | {"verdict": verdict.build(a)}

    r = alerts.subscribe(SQUARE_10HA, "Sawah Pak Budi", "id", None)
    assert r["link"] == f"https://t.me/jagapadi_bot?start={r['code']}"

    alerts.handle_update({"message": {"chat": {"id": 42}, "text": f"/start {r['code']}"}}, send, analyze)
    assert sent[0][0] == 42 and "terhubung" in sent[0][1]
    assert sent[1][1].startswith("🔴 BAHAYA · Sawah Pak Budi")

    # The same code cannot be reused by another chat.
    alerts.handle_update({"message": {"chat": {"id": 7}, "text": f"/start {r['code']}"}}, send, analyze)
    assert "tidak dikenal" in sent[-1][1]

    # Morning round: at risk -> message; safe after being at risk -> one all-clear; safe again -> silence.
    sent.clear()
    assert alerts.run_daily(send, analyze) == 1
    state["p"] = 0.05
    assert alerts.run_daily(send, analyze) == 1 and sent[-1][1].startswith("🟢 AMAN")
    assert alerts.run_daily(send, analyze) == 0

    alerts.handle_update({"message": {"chat": {"id": 42}, "text": "/stop"}}, send, analyze)
    assert alerts.run_daily(send, analyze) == 0
    assert "Berhenti memantau 1 sawah" in sent[-1][1]


def test_hindcast_scores():
    from app.engine import hindcast

    assert hindcast.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert hindcast.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert hindcast.auc([9, 8, 1, 2], [True, True, False, False]) == 1.0
    assert hindcast.auc([1, 2], [True, True]) is None
    # A rainless dry season must stress the rainfed crop on most days; a wet one never.
    dates = [f"2020-{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 32)]
    dry = hindcast.season_stress(dates, [0.0] * len(dates), [5.0] * len(dates), 2020)
    wet = hindcast.season_stress(dates, [15.0] * len(dates), [5.0] * len(dates), 2020)
    assert dry["stress_days"] > 60 and wet["stress_days"] == 0


def test_radar_flood_signal_needs_wet_surroundings():
    from app.ingest import sentinel1

    base = {"ring_history_scenes": 8, "latest_age_days": 3, "ring_water_median": 0.05}
    assert sentinel1.flood_signal(base | {"ring_water_now": 0.08}) is None
    sig = sentinel1.flood_signal(base | {"ring_water_now": 0.45})
    assert sig["kind"] == "flood" and sig["weight"] == 0.4
    # Old passes or too little history give no signal rather than a guess.
    assert sentinel1.flood_signal(base | {"ring_water_now": 0.45, "latest_age_days": 12}) is None
    assert sentinel1.flood_signal(base | {"ring_water_now": 0.45, "ring_history_scenes": 2}) is None


def test_offline_replay_matches_a_recording_from_another_day(tmp_path, monkeypatch):
    from app.ingest import http

    monkeypatch.setattr(http, "REPLAY_DIR", tmp_path)
    ukey = http._key("src", "GET", "https://x", http._undated({"start_date": "2026-10-28"}), None)
    (tmp_path / f"src-u{ukey}.json").write_text('{"payload": {"ok": 1}, "captured_at": "2026-10-28T00:00:00+00:00"}')
    monkeypatch.setattr(http, "settings", http.settings.__class__(offline=True))
    payload, captured = http.fetch_json("src", "https://x", params={"start_date": "2026-10-29"})
    assert payload == {"ok": 1} and captured.startswith("2026-10-28")
