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


def test_gemini_tool_loop_grounds_answer_in_tool_results(monkeypatch):
    from types import SimpleNamespace

    from google import genai

    sent = []

    class FakeModels:
        def __init__(self):
            self.turn = 0

        def generate_content(self, model, contents, config):
            sent.append(contents[-1])
            self.turn += 1
            if self.turn == 1:
                call = SimpleNamespace(name="pest_outlook", args={})
                return SimpleNamespace(function_calls=[call], candidates=[SimpleNamespace(content="model-turn")], text=None)
            return SimpleNamespace(function_calls=None, candidates=[], text="Risiko kering tinggi (69%).")

    monkeypatch.setattr(genai, "Client", lambda api_key: SimpleNamespace(models=FakeModels()))
    r = chat._gemini_answer([{"role": "user", "content": "kering?"}], ANALYSIS, None)
    assert r["engine"] == "llm" and r["tools_used"] == ["pest_outlook"] and "69%" in r["text"]
    # The second request carried the tool result back to the model.
    fr = sent[1].parts[0].function_response
    assert sent[1].role == "user" and fr.name == "pest_outlook" and fr.response["result"]["stage"] == "unknown"


def test_gemini_failure_falls_back_to_template(monkeypatch):
    monkeypatch.setattr(chat, "settings", chat.settings.__class__(llm_provider="gemini", llm_api_key="x"))
    monkeypatch.setattr(chat, "_gemini_answer", lambda *a: (_ for _ in ()).throw(RuntimeError("quota")))
    r = chat.answer([{"role": "user", "content": "apakah sawah saya kekeringan?"}], ANALYSIS, None, "id")
    assert r["engine"] == "template" and "RuntimeError" in r["note"]


def test_gemini_switches_model_when_quota_is_used_up(monkeypatch):
    from types import SimpleNamespace

    from google import genai
    from google.genai import errors

    tried = []

    class FakeModels:
        def generate_content(self, model, contents, config):
            tried.append(model)
            if model == chat.GEMINI_DEFAULT_MODEL:
                raise errors.ClientError(429, {"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}})
            return SimpleNamespace(function_calls=None, candidates=[], text="Halo.")

    monkeypatch.setattr(chat, "_gemini_exhausted", {})
    monkeypatch.setattr(genai, "Client", lambda api_key: SimpleNamespace(models=FakeModels()))
    r = chat._gemini_answer([{"role": "user", "content": "halo"}], ANALYSIS, None)
    assert tried == [chat.GEMINI_DEFAULT_MODEL, chat.GEMINI_CHAIN[0]] and r["model"] == chat.GEMINI_CHAIN[0]
    # The used-up model is skipped on the next question instead of costing another request.
    tried.clear()
    chat._gemini_answer([{"role": "user", "content": "halo"}], ANALYSIS, None)
    assert tried == [chat.GEMINI_CHAIN[0]]


def test_llm_answer_without_sources_gets_them_appended(monkeypatch):
    monkeypatch.setattr(chat, "settings", chat.settings.__class__(llm_provider="gemini", llm_api_key="x"))
    monkeypatch.setattr(chat, "_gemini_answer", lambda *a: {"text": "Risiko tinggi 69%.", "tools_used": ["drought_outlook"], "engine": "llm"})
    r = chat.answer([{"role": "user", "content": "kering?"}], ANALYSIS, None, "id")
    assert r["text"].endswith("Sumber: Open-Meteo Forecast API")
