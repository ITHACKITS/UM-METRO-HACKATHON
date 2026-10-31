import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Lang = "id" | "en";

const dict = {
  id: {
    nav_how: "Cara kerja",
    nav_features: "Fitur",
    nav_data: "Data",
    nav_open: "Buka peta",
    hero_l1: "Tahu risiko sawah",
    hero_l2: "sebelum",
    hero_l3: "terlambat.",
    hero_sub:
      "TUAI membaca citra satelit dan foto dari HP, lalu menandai tiap blok sawah hijau, kuning atau merah: kondisi tanaman, genangan, hama dan penyakit, giliran air, sampai perkiraan panen.",
    hero_cta: "Cek sawah saya",
    hero_cta2: "Lihat cara kerja",
    hero_strip: "Sentinel-2 · Sentinel-1 · BMKG · ECMWF ensemble · AI foto daun dan hama",
    problem_eyebrow: "Masalahnya",
    problem_title_a: "Gagal panen",
    problem_title_b: "datang tanpa tanda.",
    problem_body:
      "Petani dan P3A tidak tahu sejak awal kapan dan di blok mana sawahnya berisiko. Kurang air baru terlihat saat daun menggulung, wereng coklat hidup tersembunyi di pangkal batang, dan gejala blas, kresek dan tungro mirip bagi mata awam. Tindakan datang terlambat.",
    stat1: "hektare padi terkena banjir pada 2024 (50.142 ha puso), risiko terluas",
    stat2: "naiknya serangan wereng batang coklat di Lampung, 2022 ke 2024",
    stat3: "peluang hasil padi turun saat serangan hama naik, faktor terkuat dari 50.619 petak ubinan",
    how_eyebrow: "Cara kerja",
    how_title_a: "Tiga langkah,",
    how_title_b: "dua menit.",
    how1_t: "Gambar sawahmu",
    how1_b: "Ketuk sudut-sudut petak di peta satelit. Tidak perlu alat ukur.",
    how2_t: "Satelit dan kamera saling melengkapi",
    how2_b: "Satelit memantau seluruh hamparan: kehijauan (NDVI), kadar air tanaman (NDMI) dan genangan. Foto dari HP menangkap yang tidak terlihat satelit: penyakit di daun dan hama di pangkal batang.",
    how3_t: "Tahu apa yang harus dilakukan",
    how3_b: "Blok hijau, kuning atau merah dengan saran tindakan. Saran hama dan penyakit dicek PPL; sistem tidak langsung menyuruh menyemprot.",
    feat_eyebrow: "Lima fitur",
    feat_title_a: "Satu peta,",
    feat_title_b: "dari tanam sampai tuai.",
    f_pantau_t: "TUAI Pantau",
    f_pantau_b: "Kehijauan (NDVI) dan kadar air tanaman (NDMI) per blok dari Sentinel-2, dibanding lahan sekitar, plus fase tumbuh dari tanggal tanam.",
    f_siaga_t: "TUAI Siaga",
    f_siaga_b: "Prakiraan hujan BMKG dan peta genangan dari radar Sentinel-1 (metode UN-SPIDER): peringatan hujan lebat, blok tergenang, dan sudah berapa lama terendam.",
    f_sigap_t: "TUAI Sigap",
    f_sigap_b: "Foto daun atau pangkal rumpun dianalisis AI: blas, kresek, bercak coklat, tungro, jumlah wereng. Laporan yang dicek PPL jadi peta sebaran hama desa.",
    f_lancar_t: "TUAI Lancar",
    f_lancar_b: "Kebutuhan air tiap blok dihitung dengan FAO-56 dan dicek dengan TUAI Pantau. Ketua P3A mendapat urutan blok yang perlu dialiri lebih dulu.",
    f_taksir_t: "TUAI Taksir",
    f_taksir_b: "Riwayat kondisi tanaman, cuaca dan catatan serangan menjadi perkiraan panen per blok sebelum panen, dikalibrasi dengan hasil timbang mitra.",
    honest_eyebrow: "Angka nyata",
    honest_title_a: "Tidak ada angka",
    honest_title_b: "karangan.",
    honest_body:
      "Setiap angka di TUAI berasal dari sumber terbuka atau dihitung dari sumber itu, lengkap dengan waktu pengambilannya. Kalau citra tertutup awan atau server sedang mati, kami tulis begitu.",
    honest_note: "Ini alat perkiraan ilmiah, bukan peringatan resmi. Untuk keputusan, ikuti BMKG, PPL setempat dan BPBD.",
    final_title_a: "Gambar sawahmu.",
    final_title_b: "Lihat risikonya lebih awal.",
    final_cta: "Mulai sekarang",
    footer_made: "TUAI: tuai berarti memanen padi. Dibuat untuk petani Lampung dan seluruh Indonesia.",
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
    hero_l1: "Know the field's risks",
    hero_l2: "before",
    hero_l3: "it is too late.",
    hero_sub:
      "TUAI reads satellite images and phone photos, then marks each rice block green, yellow or red: crop condition, standing water, pests and diseases, water turns and the harvest estimate.",
    hero_cta: "Check my field",
    hero_cta2: "See how it works",
    hero_strip: "Sentinel-2 · Sentinel-1 · BMKG · ECMWF ensemble · leaf and pest photo AI",
    problem_eyebrow: "The problem",
    problem_title_a: "Crop failure",
    problem_title_b: "comes without warning.",
    problem_body:
      "Farmers and water-user groups (P3A) do not know early when and in which block their rice is at risk. Water shortage shows only when leaves roll, brown planthoppers hide at the stem base, and blast, blight and tungro look alike to the untrained eye. Action comes too late.",
    stat1: "hectares of rice hit by flooding in 2024 (50,142 ha lost), the largest risk",
    stat2: "rise in brown planthopper attacks in Lampung, 2022 to 2024",
    stat3: "odds of lower rice yield as pest attacks rise, the strongest factor across 50,619 crop-cut plots",
    how_eyebrow: "How it works",
    how_title_a: "Three steps,",
    how_title_b: "two minutes.",
    how1_t: "Draw your field",
    how1_b: "Tap the corners of your plot on the satellite map. No surveying tools.",
    how2_t: "Satellite and camera, together",
    how2_b: "The satellite watches the whole area: greenness (NDVI), crop moisture (NDMI) and standing water. Phone photos catch what it cannot: disease on the leaf and pests at the stem base.",
    how3_t: "Know what to do",
    how3_b: "Green, yellow or red blocks with the action to take. Pest and disease advice is checked by the PPL; the system never just says spray.",
    feat_eyebrow: "Five features",
    feat_title_a: "One map,",
    feat_title_b: "from planting to harvest.",
    f_pantau_t: "TUAI Pantau",
    f_pantau_b: "Greenness (NDVI) and crop moisture (NDMI) per block from Sentinel-2, against the land around it, plus the growth stage from the planting date.",
    f_siaga_t: "TUAI Siaga",
    f_siaga_b: "BMKG rain forecasts and standing water from Sentinel-1 radar (UN-SPIDER method): heavy-rain warnings, flooded blocks and how long they have been under water.",
    f_sigap_t: "TUAI Sigap",
    f_sigap_b: "AI reads photos of leaves or the base of a hill: blast, blight, brown spot, tungro, planthopper counts. Reports checked by the PPL become a village pest map.",
    f_lancar_t: "TUAI Lancar",
    f_lancar_b: "Each block's water need from FAO-56, checked against TUAI Pantau. The P3A chair gets the order in which blocks should be irrigated.",
    f_taksir_t: "TUAI Taksir",
    f_taksir_b: "The season's crop condition, weather and attack records become a harvest estimate per block before harvest, calibrated with the partners' weighed harvests.",
    honest_eyebrow: "Real numbers",
    honest_title_a: "No made-up",
    honest_title_b: "numbers.",
    honest_body:
      "Every number in TUAI comes from an open source or is calculated from one, with its capture time. When a scene is cloudy or a server is down, we say so.",
    honest_note: "A scientific estimation tool, not an official warning. For decisions follow BMKG, your extension officer (PPL) and BPBD.",
    final_title_a: "Draw your field.",
    final_title_b: "See the risks early.",
    final_cta: "Start now",
    footer_made: "TUAI: 'tuai' means to harvest rice. Made for farmers in Lampung and across Indonesia.",
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
