"""Telegram early warnings: a farmer links a field once, then gets a message every morning
while the field is at risk, and whenever its status changes.

Linking: the app asks for a one-time code, opens t.me/<bot>?start=<code>, and the bot binds
that code to the chat. The bot long-polls Telegram, so no public URL is needed. Run a single
API worker when alerts are on, otherwise each worker would poll and send.
"""

import json
import logging
import secrets
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app import services
from app.config import DATA_DIR, settings
from app.engine import verdict

log = logging.getLogger("jagapadi.alerts")

STORE = DATA_DIR / "alerts" / "subscriptions.json"
WIB = timezone(timedelta(hours=7))
PENDING_TTL = timedelta(days=2)
MAX_FIELDS_PER_CHAT = 5

_lock = threading.Lock()
_bot_username: str | None = None
_http = httpx.Client(timeout=httpx.Timeout(70.0, connect=10.0))

Send = Callable[[int, str], None]
Analyze = Callable[[dict, dict], dict]


def enabled() -> bool:
    return bool(settings.telegram_token)


def _api(method: str, **params: Any) -> Any:
    r = _http.post(f"https://api.telegram.org/bot{settings.telegram_token}/{method}", json=params)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method}: {data.get('description')}")
    return data["result"]


def send_telegram(chat_id: int, text: str) -> None:
    _api("sendMessage", chat_id=chat_id, text=text, disable_web_page_preview=True)


def bot_username() -> str | None:
    global _bot_username
    if _bot_username is None and enabled():
        try:
            _bot_username = _api("getMe")["username"]
        except Exception as e:
            log.warning("telegram getMe failed: %s", e)
    return _bot_username


def _load() -> list[dict]:
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else []


def _save(subs: list[dict]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(subs, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STORE)


def _now() -> datetime:
    return datetime.now(WIB)


def subscribe(geometry: dict, name: str, lang: str, dat: int | None) -> dict[str, Any]:
    services.validate_field(geometry)
    code = secrets.token_urlsafe(9)
    with _lock:
        subs = [s for s in _load() if s["chat_id"] or _now() - datetime.fromisoformat(s["created_at"]) < PENDING_TTL]
        subs.append(
            {
                "code": code,
                "geometry": geometry,
                "name": name[:60] or "Sawah",
                "lang": lang if lang in {"id", "en"} else "id",
                "days_after_transplant": dat,
                "chat_id": None,
                "created_at": _now().isoformat(timespec="seconds"),
                "last_status": None,
                "last_sent": None,
            }
        )
        _save(subs)
    user = bot_username()
    return {"enabled": True, "code": code, "link": f"https://t.me/{user}?start={code}" if user else None}


def _check(sub: dict, analyze: Analyze) -> dict | None:
    opts = {"days_after_transplant": sub["days_after_transplant"]} if sub.get("days_after_transplant") is not None else {}
    a = analyze(sub["geometry"], opts)
    return a.get("verdict") if a.get("status") == "ok" else None


def _text(sub: dict, key: str) -> str:
    t = {
        "linked": {
            "id": "Sawah \"{name}\" terhubung. Jagapadi akan mengirim pesan setiap pagi selama sawah berisiko, dan saat statusnya berubah.\n\nPerintah: /cek (cek sekarang), /stop (berhenti).",
            "en": "Field \"{name}\" is linked. Jagapadi will message you every morning while the field is at risk, and when its status changes.\n\nCommands: /cek (check now), /stop (unsubscribe).",
        },
        "nodata": {
            "id": "Data cuaca untuk \"{name}\" belum tersedia. Jagapadi akan mencoba lagi besok pagi.",
            "en": "Weather data for \"{name}\" is not available. Jagapadi will try again tomorrow morning.",
        },
    }[key]
    return t[sub["lang"]].format(name=sub["name"])


def _mark(code: str, status: str) -> None:
    with _lock:
        subs = _load()
        for s in subs:
            if s["code"] == code:
                s["last_status"] = status
                s["last_sent"] = _now().isoformat(timespec="seconds")
        _save(subs)


def _report(sub: dict, send: Send, analyze: Analyze) -> None:
    v = _check(sub, analyze)
    if v is None:
        send(sub["chat_id"], _text(sub, "nodata"))
        return
    send(sub["chat_id"], verdict.message(v, sub["name"], sub["lang"]))
    _mark(sub["code"], v["status"])


def handle_update(update: dict, send: Send, analyze: Analyze) -> None:
    msg = update.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id or not text.startswith("/"):
        return
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()

    # Change the store under the lock; run the slow analyses after releasing it.
    to_report: list[dict] = []
    with _lock:
        subs = _load()
        mine = [s for s in subs if s["chat_id"] == chat_id]
        if cmd == "/start" and arg:
            sub = next((s for s in subs if s["code"] == arg.strip() and s["chat_id"] is None), None)
            if sub is None:
                send(chat_id, 'Kode tidak dikenal atau sudah dipakai. Buka lagi Jagapadi dan tekan "Peringatan Telegram".')
                return
            if len(mine) >= MAX_FIELDS_PER_CHAT:
                send(chat_id, f"Satu akun bisa memantau paling banyak {MAX_FIELDS_PER_CHAT} sawah. Ketik /stop untuk mulai ulang.")
                return
            sub["chat_id"] = chat_id
            _save(subs)
            send(chat_id, _text(sub, "linked"))
            to_report = [sub]
        elif cmd == "/start":
            send(chat_id, 'Halo! Buka Jagapadi, pilih sawahmu, lalu tekan "Peringatan Telegram" untuk menghubungkannya ke sini.')
        elif cmd == "/cek":
            if not mine:
                send(chat_id, "Belum ada sawah yang terhubung. Hubungkan dari aplikasi Jagapadi.")
            to_report = mine
        elif cmd == "/stop":
            _save([s for s in subs if s["chat_id"] != chat_id])
            send(chat_id, f"Berhenti memantau {len(mine)} sawah. Sampai jumpa!")
        else:
            send(chat_id, "Perintah: /cek (cek sawah sekarang), /stop (berhenti).")
    for sub in to_report:
        _report(sub, send, analyze)


def run_daily(send: Send, analyze: Analyze) -> int:
    """Morning round: message every linked field that is at risk or whose status changed."""
    with _lock:
        linked = [s for s in _load() if s["chat_id"]]
    sent = 0
    for s in linked:
        try:
            v = _check(s, analyze)
        except Exception as e:
            log.warning("alert check failed for %s: %s", s["name"], e)
            continue
        if v is None or (v["status"] == "aman" and s["last_status"] in {None, "aman"}):
            continue
        send(s["chat_id"], verdict.message(v, s["name"], s["lang"]))
        _mark(s["code"], v["status"])
        sent += 1
    return sent


def _poll_loop(stop: threading.Event) -> None:
    offset = None
    while not stop.is_set():
        try:
            updates = _api("getUpdates", timeout=50, offset=offset, allowed_updates=["message"])
        except Exception as e:
            log.warning("telegram poll failed: %s", e)
            stop.wait(15)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                handle_update(u, send_telegram, services.analyze)
            except Exception as e:
                log.exception("telegram update failed: %s", e)


def _schedule_loop(stop: threading.Event) -> None:
    # The date of the last round is kept on disk so a restart does not send it twice.
    marker = STORE.parent / "last_round.txt"
    while not stop.is_set():
        now = _now()
        last_day = marker.read_text().strip() if marker.exists() else ""
        if now.hour >= settings.alert_hour and last_day != now.date().isoformat():
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(now.date().isoformat())
            try:
                log.info("morning alert round: %d sent", run_daily(send_telegram, services.analyze))
            except Exception as e:
                log.exception("morning alert round failed: %s", e)
        stop.wait(600)


def start() -> threading.Event | None:
    if not enabled():
        return None
    stop = threading.Event()
    for fn in (_poll_loop, _schedule_loop):
        threading.Thread(target=fn, args=(stop,), daemon=True, name=fn.__name__).start()
    log.info("telegram alerts on (bot @%s, morning round %02d:00 WIB)", bot_username(), settings.alert_hour)
    return stop
