"""One plain-language verdict per field: status, a reason a farmer can read, and one thing to do today.

Shared by the simple (Petani) view, the Telegram alerts and the extension-officer dashboard,
so all three always say the same thing.
"""

from datetime import date, timedelta
from typing import Any

RANK = {"low": 0, "medium": 1, "high": 2}
STATUS = ["aman", "waspada", "bahaya"]
MONTHS_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _when(day: int, start: date) -> dict[str, str]:
    if day <= 0:
        return {"id": "sekarang", "en": "now"}
    d = start + timedelta(days=day)
    return {"id": f"sekitar {d.day} {MONTHS_ID[d.month - 1]} ({day} hari lagi)", "en": f"around {MONTHS_EN[d.month - 1]} {d.day} (in {day} days)"}


def build(a: dict[str, Any]) -> dict[str, Any]:
    """Expects the dict returned by services.analyze with status 'ok'."""
    start = date.fromisoformat(a["waterbalance"]["dates"][0])
    dr, fl = a["drought"]["risk"], a["flood"]["risk"]
    pests_high = [p for p in a["pest"] if p["level"] == "high"]

    threat = "drought" if dr["probability"] >= fl["probability"] else "flood"
    risk = dr if threat == "drought" else fl
    rank = RANK[risk["level"]]
    if pests_high and rank == 0:
        rank, threat = 1, "pest"
    status = STATUS[rank]

    pct = round(risk["probability"] * 100)
    if status == "aman":
        headline = {"id": "Sawah aman untuk 2 minggu ke depan.", "en": "The field looks safe for the next 2 weeks."}
        why = {
            "id": f"Peluang kering {round(dr['probability'] * 100)}%, peluang terendam {round(fl['probability'] * 100)}%.",
            "en": f"Drought chance {round(dr['probability'] * 100)}%, flooding chance {round(fl['probability'] * 100)}%.",
        }
    elif threat == "drought":
        fs = dr["first_stress_day"]
        when = _when(fs["p50"], start) if fs.get("p50") is not None else {"id": "dalam 2 minggu", "en": "within 2 weeks"}
        headline = {"id": f"Sawah bisa kekurangan air {when['id']}.", "en": f"The field may run short of water {when['en']}."}
        why = {"id": f"{pct}% kemungkinan kering. {_cap(dr['drivers'][0]['id'])}.", "en": f"{pct}% chance of drought. {_cap(dr['drivers'][0]['en'])}."}
    elif threat == "flood":
        sub = fl["max_submergence_days"]
        headline = {"id": "Sawah bisa tergenang dalam 2 minggu.", "en": "The field may flood within 2 weeks."}
        why = {
            "id": f"{pct}% kemungkinan padi terendam, bisa sampai {sub['p95']} hari. {_cap(fl['drivers'][0]['id'])}.",
            "en": f"{pct}% chance the rice is submerged, for up to {sub['p95']} days. {_cap(fl['drivers'][0]['en'])}.",
        }
    else:
        p = pests_high[0]
        headline = {"id": f"Cuaca cocok untuk {p['name']['id']}.", "en": f"The weather suits {p['name']['en']}."}
        why = p["reason"] if isinstance(p["reason"], dict) else {"id": p["reason"], "en": p["reason"]}

    recs = a["drought" if threat == "drought" else "flood"]["recommendations"] if threat != "pest" else []
    if status == "aman":
        today = {"id": "Cek pematang dan saluran seperti biasa. Buka lagi Jagapadi minggu depan.", "en": "Check bunds and channels as usual. Open Jagapadi again next week."}
    elif threat == "pest":
        act = pests_high[0].get("action")
        today = act or {"id": "Cek daun dan batang padi di beberapa titik sawah.", "en": "Check leaves and stems at several spots in the field."}
    elif recs:
        today = recs[0]["text"]
    else:
        today = {"id": "Tanyakan ke penyuluh (PPL) setempat.", "en": "Ask your local extension officer (PPL)."}

    return {
        "status": status,
        "threat": threat if status != "aman" else None,
        "probability": risk["probability"],
        "headline": headline,
        "why": why,
        "today": today,
        "confidence": a["confidence"],
    }


def message(v: dict[str, Any], name: str, lang: str = "id") -> str:
    """Short text for a chat alert."""
    label = {"aman": ("🟢 AMAN", "🟢 SAFE"), "waspada": ("🟡 WASPADA", "🟡 WATCH"), "bahaya": ("🔴 BAHAYA", "🔴 DANGER")}[v["status"]]
    i = 0 if lang == "id" else 1
    todo = "Yang bisa dilakukan" if lang == "id" else "What to do"
    foot = (
        "Perkiraan ilmiah, bukan peringatan resmi. Ikuti BMKG dan PPL."
        if lang == "id"
        else "Scientific estimate, not an official warning. Follow BMKG and your PPL."
    )
    return f"{label[i]} · {name}\n{v['headline'][lang]}\n{v['why'][lang]}\n\n{todo}: {v['today'][lang]}\n\n{foot}"
