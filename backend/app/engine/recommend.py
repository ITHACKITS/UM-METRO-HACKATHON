"""Ranked actions for drought and flood, tied to the computed risk and the field's situation.

Feasibility rank: 1 = cheap and doable this week by one farmer, 3 = needs a group,
money or the irrigation office. Every item says why it was chosen.
"""

from typing import Any


def _r(rank: int, id_: str, en: str, why_id: str, why_en: str, when: str | None = None) -> dict[str, Any]:
    return {"feasibility": rank, "text": {"id": id_, "en": en}, "why": {"id": why_id, "en": why_en}, "when": when}


def drought(risk: dict, stage: str, dat: int | None, water: list[dict], first_stress: dict) -> list[dict]:
    recs = []
    p = risk["probability"]
    near = [w for w in water if w["kind"] in {"river", "canal", "stream", "ditch", "reservoir", "pond", "basin", "water_well"}]
    nearest = near[0] if near else None
    day = first_stress.get("p50")

    if nearest and p >= 0.2:
        dist = nearest["distance_m"]
        name = nearest.get("name") or nearest["kind"]
        if dist <= 1500:
            recs.append(
                _r(
                    1 if dist <= 500 else 2,
                    f"Siapkan pompa dari {name} ({dist} m). Isi sawah 3-5 cm sebelum hari ke-{day if day is not None else '?'}.",
                    f"Prepare a pump from {name} ({dist} m). Fill the field to 3-5 cm before day {day if day is not None else '?'}.",
                    "Sumber air terdekat di OpenStreetMap; ketersediaan airnya belum terverifikasi.",
                    "Nearest water source in OpenStreetMap; its water availability is not verified.",
                    when=f"day {max(0, (day or 0) - 2)}",
                )
            )
    if p >= 0.2:
        recs.append(
            _r(
                1,
                "Pakai pengairan basah-kering (AWD): biarkan air turun sampai 15 cm di bawah tanah lalu airi lagi. Hemat air 15-30% tanpa menurunkan hasil.",
                "Use alternate wetting and drying (AWD): let water drop to 15 cm below the soil, then re-flood. Saves 15-30% water without yield loss.",
                "IRRI: AWD aman dimulai 1-2 minggu setelah tanam sampai berbunga.",
                "IRRI: AWD is safe from 1-2 weeks after transplanting until flowering.",
            )
            if stage in {"development", "late-season"}
            else _r(
                1,
                "Jaga genangan 3-5 cm. Saat berbunga padi paling peka kekeringan; jangan biarkan sawah kering di fase ini.",
                "Keep 3-5 cm of standing water. Flowering is the most drought-sensitive stage; do not let the field dry now.",
                "Tahap pertumbuhan saat ini sensitif terhadap kekurangan air.",
                "The current growth stage is sensitive to water shortage.",
            )
        )
        recs.append(
            _r(
                1,
                "Tutup retakan dan bocoran pematang, perbaiki saluran keluar supaya air tidak terbuang.",
                "Seal bund cracks and leaks, and close the outlet so water is not lost.",
                "Perkolasi dan rembesan adalah kehilangan air terbesar setelah evapotranspirasi.",
                "Percolation and seepage are the largest losses after evapotranspiration.",
            )
        )
    if p >= 0.4:
        recs.append(
            _r(
                2,
                "Mulsa jerami di pematang dan petak terbuka untuk mengurangi penguapan.",
                "Mulch rice straw on bunds and bare patches to cut evaporation.",
                "Risiko kekeringan sedang-tinggi dalam 14 hari.",
                "Moderate to high drought risk in the next 14 days.",
            )
        )
        recs.append(
            _r(
                3,
                "Koordinasi giliran air dengan P3A/GP3A dan petugas PPL; laporkan risiko ke Dinas Pertanian.",
                "Coordinate water rotation with the water users' association (P3A) and the extension officer (PPL).",
                "Kekurangan air biasanya dialami satu hamparan, bukan satu petak.",
                "Water shortage usually hits a whole block, not one plot.",
            )
        )
    if dat is not None and dat < 0 or stage in {"unknown", "harvest-ready"}:
        recs.append(
            _r(
                2,
                "Untuk musim berikutnya: geser tanam mengikuti awal hujan dan pilih varietas tahan kering (mis. Inpago, Inpari 38/39/41 Tadah Hujan).",
                "Next season: shift planting to the rain onset and choose drought-tolerant varieties (e.g. Inpago, Inpari 38/39/41 Tadah Hujan).",
                "Pencegahan gagal panen dimulai dari jadwal dan varietas.",
                "Preventing crop failure starts with timing and variety choice.",
            )
        )
    if not recs:
        recs.append(
            _r(
                1,
                "Risiko kekeringan rendah. Pertahankan genangan 3-5 cm dan cek lagi dalam 3 hari.",
                "Low drought risk. Keep 3-5 cm of water and check again in 3 days.",
                "Semua anggota ensemble cuaca menunjukkan air cukup.",
                "Weather ensemble members show enough water.",
            )
        )
    return sorted(recs, key=lambda r: r["feasibility"])


def flood(risk: dict, stage: str, dat: int | None, submergence: dict, river: dict | None) -> list[dict]:
    recs = []
    p = risk["probability"]
    if p >= 0.15:
        recs.append(
            _r(
                1,
                "Buka saluran pembuangan dan bersihkan sampah atau lumpur di saluran sekarang, sebelum hujan lebat.",
                "Open drains and clear trash or silt from channels now, before heavy rain.",
                "Kapasitas buang sawah menentukan berapa lama air menggenang.",
                "Drain capacity decides how long water stays on the field.",
            )
        )
        recs.append(
            _r(
                2,
                "Perkuat dan tinggikan pematang di sisi yang lebih rendah atau dekat sungai.",
                "Reinforce and raise bunds on the low side or the side facing the river.",
                "Medan sekitar dan jarak ke sungai dari DEM dan OpenStreetMap.",
                "Surrounding terrain and river distance from the DEM and OpenStreetMap.",
            )
        )
    if submergence.get("p95", 0) >= 3:
        recs.append(
            _r(
                2,
                "Padi biasa hanya tahan terendam penuh sekitar 4-7 hari. Siapkan pompa buang; untuk musim depan pakai varietas tahan rendam (Inpari 29/30 Ciherang Sub1, Inpari 42).",
                "Ordinary rice survives about 4-7 days of full submergence. Prepare a drainage pump; next season use submergence-tolerant varieties (Inpari 29/30 Ciherang Sub1, Inpari 42).",
                f"Skenario terburuk (P95): {submergence.get('p95')} hari terendam penuh.",
                f"Worst case (P95): {submergence.get('p95')} days fully submerged.",
            )
        )
    if p >= 0.3 and dat is not None and dat >= 95:
        recs.append(
            _r(
                1,
                "Bulir sudah menguning: pertimbangkan panen lebih awal sebelum puncak banjir.",
                "Grain is ripening: consider harvesting early before the flood peak.",
                "Tahap pemasakan; panen 1-2 minggu lebih awal kehilangannya lebih kecil daripada gabah terendam.",
                "Ripening stage; harvesting 1-2 weeks early loses less than submerged grain.",
            )
        )
    if river and river.get("exceed_prob", 0) >= 0.2:
        recs.append(
            _r(
                3,
                "Debit sungai diperkirakan di atas banjir 2-tahunan. Pantau peringatan BPBD dan koordinasikan dengan kelompok tani.",
                "River flow is forecast above the 2-year flood. Follow BPBD warnings and coordinate with the farmer group.",
                f"Peluang debit melampaui ambang: {river['exceed_prob']:.0%} anggota ensemble GloFAS.",
                f"Chance of exceeding the threshold: {river['exceed_prob']:.0%} of GloFAS ensemble members.",
            )
        )
    if not recs:
        recs.append(
            _r(
                1,
                "Risiko banjir rendah. Pastikan saluran buang tetap bersih.",
                "Low flood risk. Keep the drains clear.",
                "Ensemble hujan dan debit sungai tidak menunjukkan genangan berbahaya.",
                "Rain and river ensembles do not show harmful ponding.",
            )
        )
    return sorted(recs, key=lambda r: r["feasibility"])


PEST_ACTIONS = {
    "blast": {
        "id": "Periksa bercak belah ketupat di daun dan leher malai pagi hari. Kurangi pupuk N berlebih. Untuk fungisida, ikuti label dan arahan PPL.",
        "en": "Scout for diamond-shaped lesions on leaves and panicle necks in the morning. Avoid excess nitrogen. For fungicides follow the label and your extension officer.",
    },
    "blb": {
        "id": "Cari daun menguning dari ujung dengan tepi bergelombang. Keringkan sawah sebentar, jangan beri N berlebih, bersihkan gulma inang.",
        "en": "Look for leaves yellowing from the tip with wavy edges. Drain the field briefly, avoid excess N, and remove weed hosts.",
    },
    "bph": {
        "id": "Ketuk pangkal rumpun di atas nampan di 20 titik. Lebih dari 10 wereng per rumpun: hubungi PPL. Jangan semprot insektisida spektrum luas yang membunuh musuh alami.",
        "en": "Tap the base of hills over a tray at 20 spots. More than 10 hoppers per hill: call the extension officer. Avoid broad-spectrum insecticides that kill natural enemies.",
    },
    "stemborer": {
        "id": "Cari kelompok telur di daun dan gejala sundep/beluk. Kumpulkan kelompok telur; pasang perangkap feromon bila tersedia.",
        "en": "Look for egg masses on leaves and deadhearts or whiteheads. Collect egg masses; use pheromone traps if available.",
    },
}
