from app.llm import chat

ANALYSIS = {
    "field": {"area_ha": 10.5, "lat": -5.1, "lon": 105.33},
    "crop": {"days_after_transplant": None, "stage": "unknown"},
    "satellite": {"latest_clear": None, "latest_clear_age_days": None},
    "weather": {"soil_moisture_now": 0.28},
    "confidence": "low",
    "mode": "real",
    "sources": [{"name": "Open-Meteo Forecast API (best-match models)", "captured_at": "2026-10-28T00:00:00+00:00"}],
    "unavailable": [],
    "drought": {
        "risk": {"level": "high", "probability": 0.69, "first_stress_day": {"p5": 0, "p50": 9, "p95": 13, "share_of_members": 0.72}, "drivers": ["x"]},
        "recommendations": [{"text": {"id": "Pakai AWD", "en": "Use AWD"}}],
    },
    "flood": {"risk": {"level": "low", "probability": 0.0, "drivers": []}, "recommendations": []},
    "pest": [],
    "water_sources": [],
}


def test_template_answers_drought_from_data_only():
    r = chat._template_answer([{"role": "user", "content": "apakah sawah saya kekeringan?"}], ANALYSIS, "id")
    assert r["engine"] == "template"
    assert "69%" in r["text"] and "hari ke-9" in r["text"]


def test_template_says_unavailable_for_missing_water_sources():
    r = chat._template_answer([{"role": "user", "content": "di mana sumber air terdekat?"}], ANALYSIS, "id")
    assert "Tidak ada sumber air" in r["text"]


def test_tool_payload_water_sources_honest_when_empty():
    assert "no mapped water source" in chat.tool_payload("water_sources", ANALYSIS)
