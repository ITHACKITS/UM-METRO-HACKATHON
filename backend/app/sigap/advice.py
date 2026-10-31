"""First advice per TUAI Sigap class: scouting and cultural steps only, never a spray instruction or dose.

The text is a draft from IRRI Rice Knowledge Bank guidance. Before the pilot it is replaced by
the Kementan pest-control guidelines and checked by the PPL (`checked_by_ppl`).
"""

from app.engine.recommend import PEST_ACTIONS

NAMES = {
    "kresek": {"id": "Kresek / hawar daun bakteri", "en": "Bacterial leaf blight"},
    "blas": {"id": "Blas", "en": "Rice blast"},
    "bercak_coklat": {"id": "Bercak coklat", "en": "Brown spot"},
    "tungro": {"id": "Tungro", "en": "Tungro"},
    "sehat": {"id": "Sehat", "en": "Healthy"},
    "wereng": {"id": "Wereng batang coklat", "en": "Brown planthopper"},
    "penggerek_batang": {"id": "Penggerek batang (sundep/beluk)", "en": "Stem borer (deadheart/whitehead)"},
    "hispa": {"id": "Hispa", "en": "Rice hispa"},
    "pelipat_daun": {"id": "Pelipat daun", "en": "Leaf folder"},
    "tikus": {"id": "Tikus sawah", "en": "Rice-field rat"},
}
KIND = {
    "kresek": "penyakit",
    "blas": "penyakit",
    "bercak_coklat": "penyakit",
    "tungro": "penyakit",
    "sehat": "sehat",
    "wereng": "hama",
    "penggerek_batang": "hama",
    "hispa": "hama",
    "pelipat_daun": "hama",
    "tikus": "hama",
}

ADVICE = {
    "kresek": PEST_ACTIONS["blb"],
    "blas": PEST_ACTIONS["blast"],
    "wereng": PEST_ACTIONS["bph"],
    "penggerek_batang": PEST_ACTIONS["stemborer"],
    "bercak_coklat": {
        "id": "Bercak coklat sering muncul di tanah kurang hara (kalium, silika) atau saat kurang air. Cek pemupukan berimbang dan kecukupan air; tanyakan PPL sebelum memakai fungisida.",
        "en": "Brown spot often follows poor soil (potassium, silicon) or water shortage. Check balanced fertiliser and water; ask the PPL before any fungicide.",
    },
    "tungro": {
        "id": "Tungro ditularkan wereng hijau dan bisa menyebar ke blok sekitar. Cabut dan benamkan rumpun bergejala, amati wereng hijau, segera lapor PPL.",
        "en": "Tungro is spread by green leafhoppers and can reach nearby blocks. Pull and bury affected hills, watch for leafhoppers, report to the PPL now.",
    },
    "hispa": {
        "id": "Kumbang hispa mengikis daun sehingga tampak garis putih. Potong ujung daun bergejala; lapor PPL bila meluas.",
        "en": "Hispa beetles scrape leaves into white streaks. Clip affected leaf tips; report to the PPL if it spreads.",
    },
    "pelipat_daun": {
        "id": "Ulat pelipat daun menggulung daun. Hitung daun terlipat per rumpun; musuh alami biasanya cukup, hubungi PPL bila banyak.",
        "en": "Leaf folder caterpillars roll the leaves. Count folded leaves per hill; natural enemies usually suffice, call the PPL if many.",
    },
    "tikus": {
        "id": "Kendalikan bersama satu hamparan: gropyok dan pengemposan liang serentak, bersihkan pematang dan semak. Koordinasikan lewat kelompok tani.",
        "en": "Act together across the area: hunt and fumigate burrows at the same time, clear bunds and scrub. Coordinate through the farmer group.",
    },
    "sehat": {"id": "Tidak terlihat gejala. Terus pantau seminggu sekali.", "en": "No symptoms seen. Keep checking weekly."},
}


def for_class(key: str) -> dict:
    return {
        "key": key,
        "name": NAMES.get(key, {"id": key, "en": key}),
        "kind": KIND.get(key, "hama"),
        "advice": ADVICE.get(key, {"id": "Tanyakan ke PPL setempat.", "en": "Ask the local PPL."}),
        "checked_by_ppl": False,
        "source": "IRRI Rice Knowledge Bank (draft; diganti pedoman Kementan dan dicek PPL sebelum pilot)",
    }
