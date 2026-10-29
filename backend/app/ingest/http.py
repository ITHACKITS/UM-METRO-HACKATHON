"""Shared HTTP access for every ingest module.

Responses go through a TTL cache. With JAGAPADI_RECORD=1 each live response is also
written to data/replay with its capture time; with JAGAPADI_OFFLINE=1 only those
recorded responses are served, so a demo survives without network.
"""

import hashlib
import json
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import REPLAY_DIR, settings


class SourceUnavailable(Exception):
    def __init__(self, source: str, reason: str):
        super().__init__(f"{source}: {reason}")
        self.source = source
        self.reason = reason


_cache: dict[str, tuple[float, Any, str]] = {}
_lock = threading.Lock()
_status: dict[str, dict[str, Any]] = {}

_client = httpx.Client(
    timeout=httpx.Timeout(45.0, connect=10.0),
    headers={"User-Agent": settings.user_agent},
    follow_redirects=True,
)


def _key(source: str, method: str, url: str, params: Any, body: Any) -> str:
    raw = json.dumps([source, method, url, params, body], sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _undated(x: Any) -> Any:
    """The request with every date blanked, so a recording still matches on a later day."""
    if isinstance(x, str):
        return _DATE.sub("*", x)
    if isinstance(x, dict):
        return {k: _undated(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_undated(v) for v in x]
    return x


def _replay(source: str, key: str, ukey: str) -> dict | None:
    for name in (f"{source}-{key}.json", f"{source}-u{ukey}.json"):
        f = REPLAY_DIR / name
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    return None


def _mark(source: str, ok: bool, detail: str = "") -> None:
    _status[source] = {
        "ok": ok,
        "detail": detail,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def source_status() -> dict[str, dict[str, Any]]:
    return dict(_status)


def fetch_json(
    source: str,
    url: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
    method: str = "GET",
    ttl: int = 1800,
    retries: int = 2,
    timeout: float | None = None,
) -> tuple[Any, str]:
    """Return (payload, captured_at_iso). Raises SourceUnavailable."""
    key = _key(source, method, url, params, body)
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            return hit[1], hit[2]

    ukey = _key(source, method, url, _undated(params), _undated(body))
    if settings.offline:
        rec = _replay(source, key, ukey)
        if rec:
            return rec["payload"], rec["captured_at"]
        raise SourceUnavailable(source, "offline mode and no recorded response for this request")

    last_err = "unknown error"
    for attempt in range(retries + 1):
        try:
            if method == "POST":
                r = _client.post(url, json=body, params=params, timeout=timeout or _client.timeout)
            else:
                r = _client.get(url, params=params, timeout=timeout or _client.timeout)
            if r.status_code == 429 or r.status_code >= 500:
                last_err = f"HTTP {r.status_code}"
                time.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code >= 400:
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                break
            if not r.content.lstrip().startswith((b"{", b"[")):
                # Overpass answers rate limits with an HTML page and status 200.
                last_err = "non-JSON response (rate limited or server busy)"
                time.sleep(3.0 * (attempt + 1))
                continue
            payload = r.json()
            captured = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with _lock:
                _cache[key] = (now + ttl, payload, captured)
            _mark(source, True)
            if settings.record:
                REPLAY_DIR.mkdir(parents=True, exist_ok=True)
                rec = json.dumps({"source": source, "url": url, "captured_at": captured, "payload": payload})
                (REPLAY_DIR / f"{source}-{key}.json").write_text(rec, encoding="utf-8")
                # Latest recording of the same request on any day.
                (REPLAY_DIR / f"{source}-u{ukey}.json").write_text(rec, encoding="utf-8")
            return payload, captured
        except (httpx.HTTPError, ValueError) as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(1.0 * (attempt + 1))

    rec = _replay(source, key, ukey)
    if rec:
        _mark(source, False, f"live failed ({last_err}); served recording")
        return rec["payload"], rec["captured_at"]
    _mark(source, False, last_err)
    raise SourceUnavailable(source, last_err)
