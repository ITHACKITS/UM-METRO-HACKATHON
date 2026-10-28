import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "id" | "en";

const dict = {
  id: {
    nav_how: "Cara kerja",
    nav_features: "Fitur",
    nav_data: "Data",
    nav_open: "Buka peta",
    hero_l1: "Jaga sawah",
    hero_l2: "sebelum",
    hero_l3: "kering atau banjir.",
    hero_sub:
      "Jagapadi membaca citra satelit, ramalan cuaca dan tinggi lahan, lalu memberi tahu kapan sawahmu kekurangan air, kapan terancam banjir, dan apa yang bisa dikerjakan minggu ini.",
    hero_cta: "Cek sawah saya",
    hero_cta2: "Lihat cara kerja",
    hero_strip: "Sentinel-2 · ECMWF ensemble · GloFAS · Copernicus DEM · OpenStreetMap",
    problem_eyebrow: "Masalahnya",
    problem_title_a: "Kemarau datang",
    problem_title_b: "lebih cepat dari kabar.",
    problem_body:
      "Petani biasanya tahu sawahnya kering saat tanah sudah retak. Data satelit dan cuaca sebenarnya sudah melihat tanda-tandanya beberapa hari sebelumnya, hanya saja datanya tidak sampai ke pematang.",
    stat1: "luas panen padi nasional 2023 turun, saat El Niño menguat",
    stat2: "ton beras hilang dari produksi nasional 2023",
    stat3: "hektare sawah terdampak kekeringan pada kemarau 2019, 9.358 ha puso",
    how_eyebrow: "Cara kerja",
    how_title_a: "Tiga langkah,",
    how_title_b: "dua menit.",
    how1_t: "Gambar sawahmu",
    how1_b: "Ketuk sudut-sudut petak di peta satelit. Tidak perlu alat ukur.",
    how2_t: "Kami baca langit dan tanah",
    how2_b: "Kehijauan dan kandungan air tanaman dari Sentinel-2, 51 skenario hujan ECMWF, debit sungai GloFAS, ketinggian lahan.",
    how3_t: "Kerjakan minggu ini",
    how3_b: "Kapan mulai stres air, kapan bisa tergenang, sumber air terdekat, dan langkah yang diurutkan dari yang paling mudah.",
    feat_eyebrow: "Empat pulau",
    feat_title_a: "Satu sawah,",
    feat_title_b: "empat penjaga.",
    f_drought_t: "Kering",
    f_drought_b: "Neraca air harian FAO-56 dijalankan di 51 anggota ensemble cuaca. Hasilnya rentang P5-P50-P95 hari mulai stres, ditambah sumber air terdekat dan rencana pompa.",
    f_flood_t: "Banjir",
    f_flood_b: "Hujan lebat, limpasan dari lahan yang lebih tinggi, dan debit sungai dibanding banjir 2-tahunan. Simulator menunjukkan kedalaman dan lama genangan per hari.",
    f_pest_t: "Hama",
    f_pest_b: "Kesesuaian cuaca untuk blas, hawar daun bakteri, wereng cokelat dan penggerek batang, dengan cara mengecek di lahan. Bukan deteksi, jadi tetap turun ke sawah.",
    f_chat_t: "Tanya Padi",
    f_chat_b: "Si Padi menjawab dari data lahanmu sendiri, menyebut sumbernya, dan bilang terus terang kalau datanya tidak ada.",
    honest_eyebrow: "Angka nyata",
    honest_title_a: "Tidak ada angka",
    honest_title_b: "karangan.",
    honest_body:
      "Setiap angka di Jagapadi berasal dari sumber terbuka atau dihitung dari sumber itu, lengkap dengan waktu pengambilannya. Kalau citra tertutup awan atau server sedang mati, kami tulis begitu.",
    honest_note: "Ini alat perkiraan ilmiah, bukan peringatan resmi. Untuk keputusan, ikuti BMKG, PPL setempat dan BPBD.",
    final_title_a: "Gambar sawahmu.",
    final_title_b: "Lihat dua minggu ke depan.",
    final_cta: "Mulai sekarang",
    footer_made: "Dibuat untuk petani Lampung dan seluruh Indonesia.",
    loading: "Menumbuhkan bibit…",
    hero_eyebrow: "Sawah dan air, dalam miniatur",
    hero_caption: "Studi air dan musim tanam",
    dock_reset: "Atur ulang tampilan",
    dock_kering: "Kering",
    dock_normal: "Normal",
    dock_banjir: "Banjir",
    dock_stage: "Fase",
    dock_hour: "Jam",
    dock_full: "Layar penuh",
    stage_0: "Tanam",
    stage_1: "Tumbuh",
    stage_2: "Menguning",
    stage_3: "Panen",
    hint_drag: "Seret untuk memutar · klik air untuk riak",
    hint_touch: "Ketuk air untuk riak",
    loader_title: "Menyiapkan sawah",
    loader_note: "Semua dibuat di peramban: tanpa model 3D unduhan.",
    nowebgl: "Peramban ini tidak mendukung WebGL 2, jadi diorama tidak ditampilkan. Semua fitur pemantauan tetap bisa dipakai.",
  },
  en: {
    nav_how: "How it works",
    nav_features: "Features",
    nav_data: "Data",
    nav_open: "Open map",
    hero_l1: "Guard the rice",
    hero_l2: "before",
    hero_l3: "drought or flood.",
    hero_sub:
      "Jagapadi reads satellite images, weather forecasts and terrain, then tells you when your field will run short of water, when it may flood, and what to do this week.",
    hero_cta: "Check my field",
    hero_cta2: "See how it works",
    hero_strip: "Sentinel-2 · ECMWF ensemble · GloFAS · Copernicus DEM · OpenStreetMap",
    problem_eyebrow: "The problem",
    problem_title_a: "Dry spells arrive",
    problem_title_b: "faster than the news.",
    problem_body:
      "Farmers usually learn a field is dry when the soil has already cracked. Satellite and weather data see the signs days earlier; the data just never reaches the paddy bund.",
    stat1: "drop in Indonesia's 2023 rice harvested area as El Niño strengthened",
    stat2: "tonnes of rice lost from national production in 2023",
    stat3: "hectares of paddy hit by drought in the 2019 dry season, 9,358 ha total crop failure",
    how_eyebrow: "How it works",
    how_title_a: "Three steps,",
    how_title_b: "two minutes.",
    how1_t: "Draw your field",
    how1_b: "Tap the corners of your plot on the satellite map. No surveying tools.",
    how2_t: "We read the sky and the soil",
    how2_b: "Greenness and crop water from Sentinel-2, 51 ECMWF rain scenarios, GloFAS river flow, terrain height.",
    how3_t: "Act this week",
    how3_b: "When water stress starts, when it may flood, the nearest water source, and steps ranked from easiest first.",
    feat_eyebrow: "Four islands",
    feat_title_a: "One field,",
    feat_title_b: "four guardians.",
    f_drought_t: "Drought",
    f_drought_b: "An FAO-56 daily water balance run across 51 weather ensemble members. You get a P5-P50-P95 range for the first stress day, plus the nearest water and a pumping plan.",
    f_flood_t: "Flood",
    f_flood_b: "Heavy rain, runoff from higher ground and river flow against the 2-year flood. The simulator shows water depth and duration day by day.",
    f_pest_t: "Pests",
    f_pest_b: "Weather suitability for blast, bacterial leaf blight, brown planthopper and stem borer, with field scouting steps. Not detection, so still walk the field.",
    f_chat_t: "Ask Padi",
    f_chat_b: "Padi answers from your own field data, names its sources, and says plainly when data is missing.",
    honest_eyebrow: "Real numbers",
    honest_title_a: "No made-up",
    honest_title_b: "numbers.",
    honest_body:
      "Every number in Jagapadi comes from an open source or is calculated from one, with its capture time. When a scene is cloudy or a server is down, we say so.",
    honest_note: "A scientific estimation tool, not an official warning. For decisions follow BMKG, your extension officer (PPL) and BPBD.",
    final_title_a: "Draw your field.",
    final_title_b: "See the next two weeks.",
    final_cta: "Start now",
    footer_made: "Made for farmers in Lampung and across Indonesia.",
    loading: "Growing a seedling…",
    hero_eyebrow: "Rice and water, in miniature",
    hero_caption: "A study of water and planting seasons",
    dock_reset: "Reset view",
    dock_kering: "Drought",
    dock_normal: "Normal",
    dock_banjir: "Flood",
    dock_stage: "Stage",
    dock_hour: "Time",
    dock_full: "Full screen",
    stage_0: "Planting",
    stage_1: "Growing",
    stage_2: "Ripening",
    stage_3: "Harvest",
    hint_drag: "Drag to orbit · click the water for ripples",
    hint_touch: "Tap the water for ripples",
    loader_title: "Preparing the rice field",
    loader_note: "Everything is generated in your browser: no downloaded 3D models.",
    nowebgl: "This browser does not support WebGL 2, so the diorama is hidden. Every monitoring feature still works.",
  },
} as const;

export type Key = keyof (typeof dict)["id"];

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string };
const LangContext = createContext<Ctx>({ lang: "id", setLang: () => {}, t: (k) => dict.id[k] });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const v = localStorage.getItem("jagapadi-lang");
      if (v === "id" || v === "en") return v;
    } catch {
      /* storage blocked: default to Indonesian */
    }
    return "id";
  });
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("jagapadi-lang", l);
    } catch {
      /* not persisted */
    }
  };
  return <LangContext.Provider value={{ lang, setLang, t: (k) => dict[lang][k] }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);

export function LangToggle({ className = "" }: { className?: string }) {
  const { lang, setLang } = useLang();
  return (
    <div className={`lang-toggle ${className}`} role="group" aria-label="Language / Bahasa">
      {(["id", "en"] as const).map((l) => (
        <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
