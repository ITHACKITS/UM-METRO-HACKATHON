"""TUAI Sigap image models. Each one loads on first use and reports itself unavailable instead of failing.

1. Leaf disease: Hugging Face prithivMLmods/Rice-Leaf-Disease (SigLIP2, Apache-2.0), 5 classes.
   Its published 94.77% accuracy was likely measured on its own training data; it must be retested
   on field photos before anyone relies on it.
2. Brown planthopper (wereng) counter: a YOLO detector. Local Ultralytics weights at
   models/wereng.pt (trained by scripts/sigap/train_wereng.py on the Roboflow identification-planthopper
   set, CC BY 4.0), or the Roboflow hosted model when ROBOFLOW_API_KEY and ROBOFLOW_WERENG_MODEL are set.
3. Pest symptoms (stem borer deadheart, hispa, leaf folder): Ultralytics classifier at models/gejala_hama.pt,
   trained by scripts/sigap/train_gejala.py on Paddy Doctor.

Rats are not in any dataset used here, so they are reported through a quick form, not a model.
"""

import base64
import io
import os
import threading
from typing import Any

from app.config import BACKEND_DIR
from app.ingest.http import _client

MODELS_DIR = BACKEND_DIR / "models"
DISEASE_MODEL = os.getenv("SIGAP_DISEASE_MODEL", "prithivMLmods/Rice-Leaf-Disease")
# Pinned so the classes never change under the app.
DISEASE_REVISION = os.getenv("SIGAP_DISEASE_REVISION", "170d10e070c308e0e5337690d67371825591f35b")
ROBOFLOW_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL = os.getenv("ROBOFLOW_WERENG_MODEL", "")  # "<project>/<version>"
REVIEW_BELOW = float(os.getenv("SIGAP_REVIEW_BELOW", "0.70"))
WERENG_MIN_CONF = 0.35
MAX_SIDE = 1280

_lock = threading.Lock()
_loaded: dict[str, Any] = {}


class ImageError(ValueError):
    pass


def decode(data: str) -> tuple[Any, bytes]:
    """A data URL or bare base64 string to (PIL image, JPEG bytes), downscaled for speed and storage."""
    from PIL import Image, ImageOps

    raw = data.split(",", 1)[1] if data.startswith("data:") else data
    try:
        img = Image.open(io.BytesIO(base64.b64decode(raw, validate=False)))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as e:
        raise ImageError(f"not a readable image: {type(e).__name__}") from e
    if min(img.size) < 64:
        raise ImageError("image is too small; move closer to the leaf or stem")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return img, buf.getvalue()


def _get(name: str, loader):
    with _lock:
        if name not in _loaded:
            try:
                _loaded[name] = ("ok", loader())
            except Exception as e:
                _loaded[name] = ("unavailable", f"{type(e).__name__}: {e}"[:300])
        return _loaded[name]


# Model label -> TUAI class key.
def _disease_key(label: str) -> str | None:
    s = label.lower().replace(" ", "").replace("_", "")
    for needle, key in (("blight", "kresek"), ("blast", "blas"), ("brown", "bercak_coklat"), ("tungro", "tungro"), ("healthy", "sehat")):
        if needle in s:
            return key
    return None


SYMPTOM_KEYS = {
    "dead_heart": "penggerek_batang",
    "deadheart": "penggerek_batang",
    "stem_borer": "penggerek_batang",
    "white_head": "penggerek_batang",
    "hispa": "hispa",
    "leaf_folder": "pelipat_daun",
    "leaffolder": "pelipat_daun",
    "normal": "sehat",
    "healthy": "sehat",
}


def _load_disease():
    from transformers import pipeline

    return pipeline("image-classification", model=DISEASE_MODEL, revision=DISEASE_REVISION, device="cpu")


def _load_yolo(path):
    if not path.exists():
        raise FileNotFoundError(f"{path.relative_to(BACKEND_DIR)} not trained yet")
    from ultralytics import YOLO

    return YOLO(str(path))


def disease(img) -> dict[str, Any]:
    state, m = _get("disease", _load_disease)
    if state != "ok":
        return {"status": "unavailable", "reason": m}
    preds = m(img, top_k=5)
    ranked = [{"key": _disease_key(p["label"]), "label": p["label"], "confidence": round(float(p["score"]), 3)} for p in preds]
    ranked = [r for r in ranked if r["key"]]
    return {"status": "ok", "model": f"{DISEASE_MODEL}@{DISEASE_REVISION[:7]}", "top": ranked[0] if ranked else None, "ranked": ranked}


def symptoms(img) -> dict[str, Any]:
    state, m = _get("symptoms", lambda: _load_yolo(MODELS_DIR / "gejala_hama.pt"))
    if state != "ok":
        return {"status": "unavailable", "reason": m}
    r = m(img, verbose=False)[0]
    names = r.names
    probs = r.probs.data.tolist()
    ranked = sorted(
        ({"key": SYMPTOM_KEYS.get(names[i].lower()), "label": names[i], "confidence": round(p, 3)} for i, p in enumerate(probs)),
        key=lambda x: -x["confidence"],
    )
    ranked = [x for x in ranked if x["key"]]
    return {"status": "ok", "model": "models/gejala_hama.pt (Paddy Doctor)", "top": ranked[0] if ranked else None, "ranked": ranked[:5]}


def _roboflow(jpeg: bytes) -> dict[str, Any]:
    r = _client.post(
        f"https://detect.roboflow.com/{ROBOFLOW_MODEL}",
        params={"api_key": ROBOFLOW_KEY, "confidence": int(WERENG_MIN_CONF * 100)},
        content=base64.b64encode(jpeg),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=40,
    )
    r.raise_for_status()
    d = r.json()
    w, h = d["image"]["width"], d["image"]["height"]
    boxes = [
        {
            "x": (p["x"] - p["width"] / 2) / w,
            "y": (p["y"] - p["height"] / 2) / h,
            "w": p["width"] / w,
            "h": p["height"] / h,
            "confidence": round(p["confidence"], 3),
            "class": p.get("class", "wereng"),
        }
        for p in d.get("predictions", [])
    ]
    return {"status": "ok", "model": f"Roboflow {ROBOFLOW_MODEL}", "boxes": boxes}


def planthoppers(img, jpeg: bytes) -> dict[str, Any]:
    local = MODELS_DIR / "wereng.pt"
    if local.exists():
        state, m = _get("wereng", lambda: _load_yolo(local))
        if state != "ok":
            return {"status": "unavailable", "reason": m}
        r = m(img, conf=WERENG_MIN_CONF, verbose=False)[0]
        W, H = img.size
        boxes = [
            {"x": x1 / W, "y": y1 / H, "w": (x2 - x1) / W, "h": (y2 - y1) / H, "confidence": round(c, 3), "class": r.names[int(k)]}
            for (x1, y1, x2, y2), c, k in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist(), r.boxes.cls.tolist())
        ]
        out = {"status": "ok", "model": "models/wereng.pt (YOLO)", "boxes": boxes}
    elif ROBOFLOW_KEY and ROBOFLOW_MODEL:
        try:
            out = _roboflow(jpeg)
        except Exception as e:
            return {"status": "unavailable", "reason": f"Roboflow: {type(e).__name__}: {e}"[:300]}
    else:
        return {"status": "unavailable", "reason": "no planthopper detector: train models/wereng.pt or set ROBOFLOW_API_KEY and ROBOFLOW_WERENG_MODEL"}
    out["count"] = len(out["boxes"])
    out["note"] = {
        "id": "Angka perkiraan: satu foto tidak menangkap seluruh rumpun.",
        "en": "An estimate: one photo does not capture the whole hill.",
    }
    return out


def status() -> dict[str, Any]:
    """What each model can do right now, without loading the heavy ones."""
    try:
        import transformers  # noqa: F401

        disease_ok = "ok"
    except Exception as e:
        disease_ok = f"transformers not importable: {type(e).__name__}"
    if "disease" in _loaded:
        disease_ok = "ok" if _loaded["disease"][0] == "ok" else _loaded["disease"][1]
    wereng = (
        "ok (local YOLO)"
        if (MODELS_DIR / "wereng.pt").exists()
        else "ok (Roboflow hosted)"
        if ROBOFLOW_KEY and ROBOFLOW_MODEL
        else "not configured"
    )
    return {
        "disease": {"model": DISEASE_MODEL, "state": disease_ok},
        "planthopper": {"state": wereng},
        "symptoms": {"state": "ok" if (MODELS_DIR / "gejala_hama.pt").exists() else "not trained"},
        "review_below": REVIEW_BELOW,
    }


def analyze(data: str, part: str) -> dict[str, Any]:
    """`part` is what the photo shows: 'daun' (leaf), 'pangkal' (base of the hill) or 'gejala' (other symptom)."""
    img, jpeg = decode(data)
    res: dict[str, Any] = {}
    if part in {"daun", "gejala"}:
        res["disease"] = disease(img)
        res["symptoms"] = symptoms(img)
    if part in {"pangkal", "gejala"}:
        res["planthopper"] = planthoppers(img, jpeg)

    candidates = []
    for k in ("disease", "symptoms"):
        r = res.get(k)
        if r and r["status"] == "ok" and r["top"]:
            candidates.append(r["top"])
    ph = res.get("planthopper")
    if ph and ph["status"] == "ok" and ph["count"] > 0:
        mean_conf = sum(b["confidence"] for b in ph["boxes"]) / ph["count"]
        candidates.append({"key": "wereng", "label": "planthopper", "confidence": round(mean_conf, 3), "count": ph["count"]})
    # A pest or disease beats "healthy" from the other model, which only knows its own classes.
    sick = [c for c in candidates if c["key"] != "sehat"]
    finding = max(sick or candidates, key=lambda c: c["confidence"]) if candidates else None

    reasons = []
    if not finding:
        reasons.append({"id": "tidak ada model yang bisa membaca foto ini", "en": "no model could read this photo"})
    elif finding["confidence"] < REVIEW_BELOW:
        reasons.append(
            {"id": f"keyakinan model {finding['confidence']:.0%} di bawah {REVIEW_BELOW:.0%}", "en": f"model confidence {finding['confidence']:.0%} is below {REVIEW_BELOW:.0%}"}
        )
    if sick and any(c["key"] == "sehat" and c["confidence"] >= REVIEW_BELOW for c in candidates):
        reasons.append({"id": "model saling berbeda (sehat vs bergejala)", "en": "models disagree (healthy vs symptoms)"})
    return {"part": part, "finding": finding, "needs_review": bool(reasons), "review_reasons": reasons, "models": res, "_jpeg": jpeg}
