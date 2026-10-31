"""What the user should do after a TUAI Sigap result.

Every step paraphrases the IRRI Rice Knowledge Bank fact sheet linked in its entry
(read 2026-10-31 through the Internet Archive copy, because the live site did not
respond). Nothing here is written from memory, and no entry names a pesticide product,
dose or spray schedule: chemical decisions always go to the local extension officer.
The text still needs the PPL sign-off in cv-prototype/docs/TERMINOLOGY_REVIEW.md.
"""

from __future__ import annotations

from .schemas import BilingualText, Recommendation

_BASE = "https://www.knowledgebank.irri.org/training/fact-sheets/pest-management"
_IRRI = "IRRI Rice Knowledge Bank"


def _t(indonesian: str, english: str) -> BilingualText:
    return BilingualText(id=indonesian, en=english)


_ASK_VARIETY = _t(
    "Musim berikutnya, pakai varietas tahan. Tanyakan daftar terbaru ke kantor pertanian setempat.",
    "Next season, plant a resistant variety. Ask the local agriculture office for the current list.",
)

_STEPS: dict[str, tuple[str, list[BilingualText]]] = {
    "bacterial_leaf_blight": (
        "diseases/item/bacterial-blight",
        [
            _t(
                "Pastikan drainase sawah dan persemaian baik.",
                "Make sure the field and nursery drain well.",
            ),
            _t(
                "Beri pupuk berimbang, terutama nitrogen.",
                "Use balanced fertilizer, especially nitrogen.",
            ),
            _t(
                "Bersihkan gulma inang, lalu benamkan jerami, tunggul, dan tanaman padi liar setelah panen.",
                "Remove weed hosts, then plow under straw, stubble and volunteer rice after harvest.",
            ),
            _ASK_VARIETY,
        ],
    ),
    "blast": (
        "diseases/item/blast-leaf-collar",
        [
            _t(
                "Jangan berlebihan memberi pupuk nitrogen; bagi menjadi dua kali pemberian atau lebih.",
                "Do not overuse nitrogen; split it into two or more applications.",
            ),
            _t(
                "Genangi sawah sesering mungkin bila air tersedia.",
                "Flood the field as often as possible when water is available.",
            ),
            _t(
                "Jangan memakai jerami dari tanaman yang terserang, karena jamurnya bisa bertahan di jerami.",
                "Do not reuse straw from infected plants, because the fungus can survive on it.",
            ),
            _t(
                "Tanyakan ke PPL sebelum memakai fungisida.",
                "Ask the extension officer before using any fungicide.",
            ),
            _ASK_VARIETY,
        ],
    ),
    "brown_spot": (
        "diseases/item/brown-spot",
        [
            _t(
                "Periksa kesuburan tanah dan beri pupuk sesuai kebutuhan; ini langkah pertama untuk bercak cokelat.",
                "Check soil fertility and apply the fertilizer it needs; this is the first step for brown spot.",
            ),
            _t(
                "Sebelum tanam berikutnya, rendam benih dalam air panas 53–54°C selama 10–12 menit.",
                "Before the next planting, treat seed in hot water at 53–54°C for 10–12 minutes.",
            ),
            _ASK_VARIETY,
        ],
    ),
    "tungro": (
        "diseases/item/tungro",
        [
            _t(
                "Tanaman yang sudah terinfeksi tungro tidak bisa disembuhkan. Segera laporkan ke PPL.",
                "A plant infected with tungro cannot be cured. Report it to the extension officer soon.",
            ),
            _t(
                "Semprotan untuk wereng hijau sering tidak efektif karena wereng terus berpindah antarpetak.",
                "Spraying green leafhoppers is often ineffective because they keep moving between fields.",
            ),
            _t(
                "Bajak tunggul yang terinfeksi segera setelah panen.",
                "Plow infected stubble right after harvest.",
            ),
            _t(
                "Musim berikutnya, tanam serempak dengan sawah sekitar dan pakai varietas tahan.",
                "Next season, plant at the same time as nearby farms and use a resistant variety.",
            ),
        ],
    ),
    "brown_plant_hopper": (
        "insects/item/planthopper",
        [
            _t(
                "Periksa pangkal 10–20 rumpun sambil berjalan menyilang petak. Tekuk rumpun pelan, ketuk dekat pangkalnya, dan lihat wereng yang jatuh ke air.",
                "Check the base of 10–20 hills while crossing the field diagonally. Bend a hill gently, tap near its base, and watch for hoppers falling onto the water.",
            ),
            _t(
                "Pada 1 wereng per batang atau kurang, masih ada waktu untuk bertindak bila jumlahnya naik.",
                "At 1 hopper per stem or fewer, there is still time to act if numbers rise.",
            ),
            _t(
                "Jangan menyemprot sembarangan: insektisida membunuh musuh alami dan dapat memicu ledakan wereng. Bila laba-laba dan musuh alami lain lebih banyak daripada wereng, risikonya rendah.",
                "Do not spray indiscriminately: insecticide kills natural enemies and can trigger outbreaks. If spiders and other natural enemies outnumber the hoppers, the risk is low.",
            ),
            _t("Bersihkan gulma di sawah dan sekitarnya.", "Remove weeds in and around the field."),
            _t(
                "Bila jumlahnya terus naik, hubungi PPL sebelum memakai insektisida.",
                "If numbers keep rising, call the extension officer before using insecticide.",
            ),
        ],
    ),
    "stem_borer": (
        "insects/item/stem-borer",
        [
            _t(
                "Di persemaian dan saat tanam, ambil dan musnahkan kelompok telur.",
                "In the seedbed and at transplanting, pick off and destroy egg masses.",
            ),
            _t(
                "Sesekali naikkan air irigasi untuk merendam telur di bagian bawah tanaman.",
                "Periodically raise the water level to submerge eggs on the lower plant.",
            ),
            _t(
                "Saat panen, potong rata tanah, lalu bersihkan tunggul, bajak, dan genangi sawah.",
                "Harvest at ground level, then remove stubble, plow and flood the field.",
            ),
            _t(
                "Bagi pupuk nitrogen sesuai dosis dan waktu anjuran, dan jaga musuh alami seperti tawon parasit dan laba-laba.",
                "Split nitrogen at the recommended rate and time, and protect natural enemies such as parasitic wasps and spiders.",
            ),
        ],
    ),
    "rice_leaf_roller": (
        "insects/item/rice-leaffolder",
        [
            _t(
                "Bersihkan gulma rumput di sawah dan pematang, dan pakai pupuk berimbang.",
                "Remove grassy weeds from the field and bunds, and use balanced fertilizer.",
            ),
            _t(
                "Jangan menyemprot pada awal pertumbuhan tanaman. Tanyakan ke PPL untuk kondisi sawah Anda.",
                "Do not spray during early crop stages. Ask the extension officer about your field.",
            ),
            _t(
                "Setelah panen, genangi dan bajak sawah bila memungkinkan, atau selingi tanaman lain atau masa bera.",
                "After harvest, flood and plow if possible, or follow rice with another crop or a fallow period.",
            ),
        ],
    ),
    "green_leafhopper": (
        "insects/item/green-leafhopper",
        [
            _t(
                "Wereng hijau menularkan tungro. Periksa daun menguning atau tanaman kerdil di sekitarnya, lalu laporkan ke PPL bila ada.",
                "Green leafhoppers spread tungro. Look nearby for yellowing leaves or stunted plants, and tell the extension officer if you find them.",
            ),
            _t(
                "Bersihkan gulma di sawah dan pematang.",
                "Control weeds in the field and on the bunds.",
            ),
            _t(
                "Beri nitrogen sesuai kebutuhan, jangan berlebihan.",
                "Apply nitrogen as needed and do not overuse it.",
            ),
            _t(
                "Di daerah tanpa sumber tungro, insektisida tidak diperlukan. Musim berikutnya, tanam serempak dan pakai varietas tahan.",
                "Where there is no tungro source, insecticide is not needed. Next season, plant at the same time as neighbours and use a resistant variety.",
            ),
        ],
    ),
    "rice_bug": (
        "insects/item/rice-bug",
        [
            _t(
                "Hitung walang sangit pada 20 rumpun di pagi atau sore hari sambil berjalan menyilang petak, dari sebelum berbunga sampai bulir mengeras.",
                "Count rice bugs on 20 hills in the early morning or late afternoon while crossing the field diagonally, from pre-flowering until the hard dough stage.",
            ),
            _t(
                "Lebih dari 10 ekor per 20 rumpun mungkin perlu pengendalian langsung. Hubungi PPL sebelum memakai pestisida.",
                "More than 10 bugs per 20 hills may need direct control. Contact the extension officer before using pesticide.",
            ),
            _t(
                "Bila jumlahnya masih sedikit, tangkap dengan jaring pada pagi atau sore hari.",
                "While numbers are low, catch them with a net in the early morning or late afternoon.",
            ),
            _t(
                "Bersihkan gulma di sawah dan sekitarnya; musim berikutnya, tanam serempak satu desa.",
                "Remove weeds in and around the field; next season, plant at the same time across the village.",
            ),
        ],
    ),
    "whorl_maggot": (
        "insects/item/rice-whorl-maggot",
        [
            _t(
                "Tanaman padi biasanya bisa pulih sendiri, dan gejalanya umumnya hilang saat anakan maksimum.",
                "Rice plants can usually recover, and symptoms generally disappear by maximum tillering.",
            ),
            _t(
                "Belum ada cara budi daya khusus untuk hama ini. Jaga musuh alami seperti tawon kecil dan laba-laba.",
                "There is no cultural control for this pest. Protect natural enemies such as small wasps and spiders.",
            ),
            _t(
                "Hubungi PPL bila tanaman tidak membaik.",
                "Contact the extension officer if the plants do not improve.",
            ),
        ],
    ),
}

# The local detector's narrower label shares the stem-borer guidance.
_ALIASES = {"yellow_rice_borer": "stem_borer"}

# General next steps; these are product behaviour rather than agronomic claims.
NO_SYMPTOM_STEPS = [
    _t(
        "Foto beberapa daun lain, terutama yang warnanya berbeda.",
        "Photograph a few other leaves, especially any that look different.",
    ),
    _t(
        "Hubungi PPL bila ada gejala yang tidak hilang atau meluas.",
        "Contact the extension officer if a symptom persists or spreads.",
    ),
]

UNCERTAIN_STEPS = [
    _t(
        "Foto ulang satu bagian dari dekat, dengan fokus tajam dan cahaya alami.",
        "Retake one area close up, in sharp focus and natural light.",
    ),
    _t(
        "Bila hasilnya tetap tidak pasti, tunjukkan tanamannya ke PPL atau petugas POPT.",
        "If it stays uncertain, show the plant to the extension officer or pest-control officer.",
    ),
]

# Scouting method from the planthopper fact sheet: an empty photo says little about
# insects at the base of the plant, so the user is told how to look.
NO_PEST_STEPS = [
    _t(
        "Periksa pangkal 10–20 rumpun sambil berjalan menyilang petak; ketuk dekat pangkalnya dan lihat serangga yang jatuh ke air.",
        "Check the base of 10–20 hills while crossing the field diagonally; tap near the base and watch for insects falling onto the water.",
    ),
    _t(
        "Bila melihat serangga, foto dari dekat dan periksa lagi.",
        "If you see an insect, photograph it close up and check again.",
    ),
]


def for_class(class_key: str, label: BilingualText) -> Recommendation | None:
    """Return the sourced guidance for a class key, or None when no sheet covers it."""
    entry = _STEPS.get(_ALIASES.get(class_key, class_key))
    if entry is None:
        return None
    path, steps = entry
    return Recommendation(
        label=label,
        steps=list(steps),
        source_name=_IRRI,
        source_url=f"{_BASE}/{path}",
    )
