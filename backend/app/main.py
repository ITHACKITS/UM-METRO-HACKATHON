import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import services
from app.config import BACKEND_DIR, DATA_DIR, settings
from app.engine import validation
from app.ingest.http import SourceUnavailable, source_status
from app.llm import chat

app = FastAPI(title="Jagapadi API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_analyses: dict[str, tuple[float, dict]] = {}
ANALYSIS_TTL = 1800


class AnalyzeRequest(BaseModel):
    geometry: dict
    days_after_transplant: int | None = Field(None, ge=-30, le=200)
    irrigation_mm_day: float | None = Field(None, ge=0, le=50)
    initial_ponding_mm: float | None = Field(None, ge=0, le=300)
    scenario: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    geometry: dict
    messages: list[dict] = Field(..., min_length=1, max_length=30)
    lang: str = "id"
    days_after_transplant: int | None = None


class SensorReading(BaseModel):
    token: str
    soil_moisture_m3m3: float | None = Field(None, ge=0, le=1)
    water_level_mm: float | None = Field(None, ge=-500, le=1500)
    measured_at: datetime | None = None


def _key(geom: dict, opts: dict) -> str:
    return hashlib.sha1(json.dumps([geom, opts], sort_keys=True).encode()).hexdigest()


def _analysis(geom: dict, opts: dict) -> dict:
    k = _key(geom, opts)
    hit = _analyses.get(k)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = services.analyze(geom, opts)
    except services.FieldError as e:
        raise HTTPException(422, str(e)) from e
    _analyses[k] = (time.time() + ANALYSIS_TTL, r)
    return r


def _opts(req: AnalyzeRequest | ChatRequest) -> dict:
    return {k: v for k, v in req.model_dump(exclude={"geometry", "messages", "lang"}).items() if v is not None}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "offline_replay": settings.offline,
        "llm": bool(settings.llm_provider and settings.llm_api_key),
        "openweather": bool(settings.openweather_key),
        "sources": source_status(),
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/api/demo-field")
def demo_field():
    return json.loads((BACKEND_DIR / "config" / "demo_field.json").read_text(encoding="utf-8"))


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return _analysis(req.geometry, _opts(req))


@app.post("/api/validate-field")
def validate_field(req: AnalyzeRequest):
    # A rejected drawing is an expected outcome, not an HTTP error.
    try:
        return {"valid": True, **services.validate_field(req.geometry)}
    except services.FieldError as e:
        return {"valid": False, "reason": str(e)}


@app.get("/api/validation")
def validation_endpoint(lat: float, lon: float):
    try:
        return validation.backtest(lat, lon)
    except SourceUnavailable as e:
        return {"status": "unavailable", "reason": str(e)}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    opts = _opts(req)
    base = _analysis(req.geometry, opts)
    if base.get("status") != "ok":
        return {"text": "Data cuaca belum tersedia untuk lahan ini, jadi saya belum bisa menjawab.", "engine": "none"}

    def rerun(extra: dict) -> dict:
        return _analysis(req.geometry, {**opts, **extra})

    msgs = [{"role": m.get("role"), "content": str(m.get("content", ""))[:2000]} for m in req.messages]
    return chat.answer(msgs, base, rerun, req.lang)


SENSOR_DIR = DATA_DIR / "sensors"


@app.post("/api/sensors/{field_id}")
def sensor_ingest(field_id: str, reading: SensorReading):
    tokens_file = BACKEND_DIR / "config" / "sensor_tokens.json"
    tokens = json.loads(tokens_file.read_text()) if tokens_file.exists() else {}
    if not field_id.isalnum() or tokens.get(field_id) != reading.token:
        raise HTTPException(403, "unknown field or bad token")
    SENSOR_DIR.mkdir(parents=True, exist_ok=True)
    rec = reading.model_dump(exclude={"token"})
    rec["received_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with (SENSOR_DIR / f"{field_id}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    return {"stored": True}


@app.get("/api/sensors/{field_id}")
def sensor_read(field_id: str):
    p = SENSOR_DIR / f"{field_id}.jsonl"
    if not field_id.isalnum() or not p.exists():
        return {"readings": [], "note": "no device has sent data for this field"}
    lines = p.read_text(encoding="utf-8").splitlines()[-200:]
    return {"readings": [json.loads(x) for x in lines]}


DIST = BACKEND_DIR.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str, request: Request):
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
