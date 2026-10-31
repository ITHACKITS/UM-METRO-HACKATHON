import hashlib
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import alerts, blocks, services
from app.config import BACKEND_DIR, DATA_DIR, settings
from app.engine import validation
from app.ingest.http import SourceUnavailable, source_status
from app.llm import chat
from app.sigap import advice as sigap_advice
from app.sigap import models as sigap_models
from app.sigap import reports as sigap_reports


@asynccontextmanager
async def lifespan(_: FastAPI):
    stop = alerts.start()
    yield
    if stop:
        stop.set()


app = FastAPI(title="TUAI API", version="0.1.0", lifespan=lifespan)
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


class AlertRequest(BaseModel):
    geometry: dict
    name: str = Field("Sawah", max_length=60)
    lang: str = "id"
    days_after_transplant: int | None = Field(None, ge=-30, le=200)


class Block(BaseModel):
    id: str = Field(..., max_length=64)
    name: str | None = Field(None, max_length=60)
    geometry: dict
    planting_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    variety: str | None = Field(None, max_length=40)
    soil: str | None = Field(None, max_length=20)


class BlocksRequest(BaseModel):
    blocks: list[Block] = Field(..., min_length=1, max_length=40)


class SigapAnalyzeRequest(BaseModel):
    image: str = Field(..., max_length=15_000_000)
    part: Literal["daun", "pangkal", "gejala"] = "daun"


class SigapReport(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    label: str = Field(..., max_length=30)
    source: Literal["foto", "laporan_cepat"] = "foto"
    confidence: float | None = Field(None, ge=0, le=1)
    count: int | None = Field(None, ge=0, le=10000)
    severity: Literal["ringan", "sedang", "berat"] | None = None
    needs_review: bool = True
    block_id: str | None = Field(None, max_length=64)
    block_name: str | None = Field(None, max_length=60)
    reporter: str | None = Field(None, max_length=60)
    note: str | None = Field(None, max_length=400)
    image: str | None = Field(None, max_length=15_000_000)


class SigapReview(BaseModel):
    status: Literal["verified", "rejected"]
    label: str | None = Field(None, max_length=30)
    reviewer: str = Field("PPL", max_length=60)
    note: str = Field("", max_length=400)
    pin: str | None = None


class SigapWarningsRequest(BaseModel):
    blocks: list[dict] = Field(..., max_length=200)


class Decision(BaseModel):
    season: str = Field(..., max_length=30)
    block_id: str = Field(..., max_length=64)
    block_name: str | None = Field(None, max_length=60)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    decision: str = Field(..., max_length=300)
    outcome: str = Field("", max_length=300)
    followed_recommendation: bool | None = None
    by: str = Field("Ketua P3A", max_length=60)


class Harvest(BaseModel):
    block: Block
    season: str = Field(..., max_length=30)
    yield_t_ha: float = Field(..., ge=0, le=20)


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
        "telegram": alerts.enabled(),
        "sigap": sigap_models.status(),
        "sources": source_status(),
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/api/demo-field")
def demo_field():
    return json.loads((BACKEND_DIR / "config" / "demo_field.json").read_text(encoding="utf-8"))


@app.get("/api/demo-group")
def demo_group():
    return json.loads((BACKEND_DIR / "config" / "demo_group.json").read_text(encoding="utf-8"))


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return _analysis(req.geometry, _opts(req))


@app.post("/api/verdict")
def verdict_endpoint(req: AnalyzeRequest):
    """The short form of /api/analyze, for lists of many fields."""
    a = _analysis(req.geometry, _opts(req))
    if a.get("status") != "ok":
        return {"status": a.get("status"), "field": a.get("field"), "unavailable": a.get("unavailable", [])}
    return {
        "status": "ok",
        "field": a["field"],
        "verdict": a["verdict"],
        "drought": {k: a["drought"]["risk"][k] for k in ("probability", "level", "first_stress_day")},
        "flood": {k: a["flood"]["risk"][k] for k in ("probability", "level", "max_submergence_days")},
        "pest_high": [p["name"] for p in a["pest"] if p["level"] == "high"],
        "stage": a["crop"]["stage"],
        "scene_age_days": a["satellite"]["latest_clear_age_days"],
        "generated_at": a["generated_at"],
    }


@app.post("/api/alerts/subscribe")
def alerts_subscribe(req: AlertRequest):
    if not alerts.enabled():
        return {"enabled": False}
    try:
        return alerts.subscribe(req.geometry, req.name, req.lang, req.days_after_transplant)
    except services.FieldError as e:
        raise HTTPException(422, str(e)) from e


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


# TUAI Sigap: photo -> disease and pest models -> PPL check -> village map.


@app.get("/api/sigap/status")
def sigap_status():
    return {**sigap_models.status(), "classes": {k: sigap_advice.for_class(k) for k in sigap_advice.NAMES}}


@app.post("/api/sigap/analyze")
def sigap_analyze(req: SigapAnalyzeRequest):
    try:
        r = sigap_models.analyze(req.image, req.part)
    except sigap_models.ImageError as e:
        raise HTTPException(422, str(e)) from e
    r.pop("_jpeg", None)
    r["advice"] = sigap_advice.for_class(r["finding"]["key"]) if r["finding"] else None
    return r


@app.post("/api/sigap/reports")
def sigap_create(req: SigapReport):
    if req.label not in sigap_advice.NAMES:
        raise HTTPException(422, f"unknown label {req.label}")
    jpeg = None
    if req.image:
        try:
            _, jpeg = sigap_models.decode(req.image)
        except sigap_models.ImageError as e:
            raise HTTPException(422, str(e)) from e
    rec = req.model_dump(exclude={"image"})
    rec["kind"] = sigap_advice.KIND.get(req.label, "hama")
    return sigap_reports.create(rec, jpeg)


@app.get("/api/sigap/reports")
def sigap_list(days: int = 60):
    return {"reports": sigap_reports.listing(max(1, min(days, 365)))}


@app.get("/api/sigap/reports/{rid}/photo")
def sigap_photo(rid: str):
    p = sigap_reports.photo_path(rid)
    if not p:
        raise HTTPException(404, "no photo")
    return FileResponse(p, media_type="image/jpeg")


@app.post("/api/sigap/reports/{rid}/review")
def sigap_review(rid: str, req: SigapReview):
    if settings.ppl_pin and req.pin != settings.ppl_pin:
        raise HTTPException(403, "wrong PPL PIN")
    if req.label and req.label not in sigap_advice.NAMES:
        raise HTTPException(422, f"unknown label {req.label}")
    r = sigap_reports.review(rid, req.status, req.label, req.reviewer, req.note)
    if not r:
        raise HTTPException(404, "no such report")
    return r


@app.post("/api/sigap/warnings")
def sigap_warnings(req: SigapWarningsRequest):
    bl = [b for b in req.blocks if {"id", "lat", "lon"} <= b.keys()]
    return sigap_reports.warnings(bl)


# TUAI Lancar and TUAI Taksir work on the P3A chair's blocks.


def _blocks(req: BlocksRequest) -> list[dict]:
    out = []
    for b in req.blocks:
        try:
            services.validate_field(b.geometry)
        except services.FieldError as e:
            raise HTTPException(422, f"{b.name or b.id}: {e}") from e
        out.append(b.model_dump())
    return out


@app.post("/api/lancar/rank")
def lancar_rank(req: BlocksRequest):
    return blocks.water_turns(_blocks(req), _analysis)


@app.post("/api/lancar/decisions")
def lancar_decide(req: Decision):
    return blocks.record_decision(req.model_dump())


@app.get("/api/lancar/decisions")
def lancar_decisions(season: str | None = None):
    return {"decisions": blocks.decisions(season)}


@app.post("/api/taksir")
def taksir_estimate(req: BlocksRequest):
    return blocks.harvest_estimate(_blocks(req), _analysis)


@app.post("/api/taksir/harvest")
def taksir_harvest(req: Harvest):
    try:
        services.validate_field(req.block.geometry)
    except services.FieldError as e:
        raise HTTPException(422, str(e)) from e
    return blocks.record_harvest(req.block.model_dump(), req.season, req.yield_t_ha, _analysis)


@app.get("/api/taksir/harvest")
def taksir_harvests():
    return {"harvests": blocks.harvests()}


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
