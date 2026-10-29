import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, API_DOWN, tr, type Txt, type Analysis, type Polygon, type Rec, type Risk, type Scenario, type WaterFeature } from "../lib/api";
import { LangToggle, useLang } from "../lib/i18n";
import { Logo } from "../components/Logo";
import { FanChart, ProbBars, SeriesChart } from "../components/Charts";
import { IslandGlyph } from "../components/Glyphs";
import { FieldMap } from "./FieldMap";
import { Chat } from "./Chat";
import { PrintReport } from "./PrintReport";
import { AlertButton, SimpleView } from "./Simple";
import { addField } from "../lib/watchlist";
import "./app.css";

type Tab = "summary" | "drought" | "flood" | "pest" | "water" | "data";

const L = {
  id: {
    summary: "Ringkasan",
    drought: "Kering",
    flood: "Banjir",
    pest: "Hama",
    water: "Air",
    data: "Data",
    real: "Kondisi nyata",
    test: "Uji skenario",
    draw: "Gambar lahan",
    drawHint: "Ketuk sudut-sudut sawah di peta. Ketuk dua kali atau tekan Selesai untuk menutup.",
    finish: "Selesai",
    cancel: "Batal",
    demo: "Pakai lahan contoh",
    viewSimple: "Petani",
    watch: "Pantau",
    watched: "Dipantau",
    officer: "Dasbor penyuluh",
    viewExpert: "Ahli",
    waterIn: "Air di sawah",
    ksPlain: ["cukup air", "mulai kurang air", "kurang air berat"],
    apiDown: "Server Jagapadi tidak menjawab. Jalankan `npm run dev` (API di port 8000), lalu coba lagi.",
    analyzing: "Membaca data lahan…",
    steps: ["Mencari citra Sentinel-2 bebas awan", "Mengambil 51 skenario hujan ECMWF", "Membaca debit sungai dan ketinggian lahan", "Menjalankan neraca air harian"],
    firstRun: "Analisis pertama butuh sekitar satu menit karena citra satelit dibaca langsung. Berikutnya lebih cepat.",
    empty_t: "Mulai dari sawahmu",
    empty_b: "Gambar batas petak di peta satelit, atau coba dulu dengan lahan contoh di Metro Utara.",
    risk14: "Risiko 14 hari",
    firstStress: "Stres air mulai",
    day: "hari ke",
    range: "rentang",
    ofMembers: "dari skenario cuaca",
    noStress: "Tidak ada skenario yang menunjukkan stres air dalam jangka ini.",
    drivers: "Karena",
    recs: "Yang bisa dilakukan",
    why: "Alasan",
    stage: "Fase tanaman",
    dat: "Hari setelah tanam",
    unknown: "belum diketahui",
    setDat: "Ubah",
    confidence: "Keyakinan",
    freshness: "Citra bersih terakhir",
    daysAgo: "hari lalu",
    noScene: "Tidak ada citra bersih: wilayah tertutup awan.",
    soil: "Kelembapan tanah 9-27 cm",
    unavailable: "Data yang tidak tersedia",
    ndvi: "NDVI lahan (hijau) vs sekitar (putus-putus)",
    ponding: "Genangan air di sawah · klimatologi",
    plantH: "Tinggi tanaman",
    ks: "Koefisien stres air Ks (1 = cukup air) · klimatologi",
    probStress: "Peluang stres air per hari",
    probSub: "Peluang padi terendam penuh per hari",
    river: "Debit sungai GloFAS · ambang banjir 2-tahunan",
    hand: "Tinggi lahan di atas saluran",
    radarT: "Radar Sentinel-1 (tembus awan)",
    radarV: (f: string, r: string, m: string, d: number) => `${f} air di lahan · sekitar ${r} (biasanya ${m}) · ${d} hari lalu`,
    subDays: "Hari terendam penuh (P50 / P95)",
    pestNote: "Kesesuaian cuaca 7 hari lalu dan 7 hari ke depan. Bukan deteksi hama: tetap cek langsung di sawah.",
    scout: "Cara mengecek",
    waterT: "Sumber air terdekat",
    waterNote: "Dari OpenStreetMap. Debit dan ketersediaan airnya tidak diketahui kecuali sungai besar yang terpantau GloFAS.",
    noWater: "Tidak ada sumber air terpetakan dalam 4 km, atau OpenStreetMap sedang tidak bisa diakses.",
    showRoute: "Tunjukkan di peta",
    sources: "Sumber dan waktu pengambilan",
    method: "Cara menghitung",
    hypo: "HIPOTETIS: hasil uji skenario, bukan prakiraan.",
    sim: "Simulator",
    rainF: "Faktor hujan",
    delay: "Hujan tertunda (hari)",
    heat: "Pemanasan (°C)",
    extra: "Hujan ekstrem (mm)",
    extraDay: "pada hari ke",
    irr: "Irigasi (mm/hari)",
    run: "Jalankan simulasi",
    reset: "Kembali ke kondisi nyata",
    print: "Cetak laporan",
    dayLabel: "Hari",
    play: "Putar",
    pause: "Jeda",
    pondNow: "genangan P50",
    ksNow: "Ks P50",
    level: { low: "rendah", medium: "sedang", high: "tinggi", unknown: "tidak diketahui" },
    stageNames: {
      initial: "awal (bibit)",
      development: "anakan",
      "mid-season": "bunting-berbunga",
      "late-season": "pemasakan",
      "harvest-ready": "siap panen",
      nursery: "persemaian",
      unknown: "belum diketahui",
    } as Record<string, string>,
    climNote: "Setelah hari ke-15 hujan memakai rata-rata 10 tahun (ERA5), bukan ramalan.",
    stressNow: "Sudah kekurangan air sekarang",
    legendT: "Arti warna lahan",
    lgOk: "air cukup",
    lgMild: "mulai stres air",
    lgSevere: "stres berat",
    lgPond: "tergenang",
    lgDeep: "tergenang dalam",
    lgSub: "terendam penuh",
    lgWater: "sumber air (OSM)",
    lgRoute: "garis ke sumber air",
    today: "hari ini",
    myField: "Lahan saya",
    sceneChip: "citra",
    confChip: "keyakinan",
    stepsT: ["Gambar batas petak di peta, atau pakai lahan contoh.", "Jagapadi membaca satelit, 51 skenario hujan, debit sungai dan ketinggian lahan.", "Lihat kapan kering, kapan tergenang, dan apa yang bisa dikerjakan."],
    irrAssume: "Asumsi: tanpa irigasi (kasus terburuk untuk kekeringan). Ubah di simulator kalau sawahmu dapat air irigasi.",
  },
  en: {
    summary: "Summary",
    drought: "Drought",
    flood: "Flood",
    pest: "Pests",
    water: "Water",
    data: "Data",
    real: "Real conditions",
    test: "Test scenario",
    draw: "Draw field",
    drawHint: "Tap the corners of your field on the map. Double-tap or press Done to close it.",
    finish: "Done",
    cancel: "Cancel",
    demo: "Use the sample field",
    viewSimple: "Farmer",
    watch: "Watch",
    watched: "Watching",
    officer: "Officer dashboard",
    viewExpert: "Expert",
    waterIn: "Water in field",
    ksPlain: ["enough water", "starting to dry", "severely dry"],
    apiDown: "The Jagapadi server is not responding. Run `npm run dev` (API on port 8000), then try again.",
    analyzing: "Reading field data…",
    steps: ["Finding cloud-free Sentinel-2 scenes", "Fetching 51 ECMWF rain scenarios", "Reading river flow and terrain", "Running the daily water balance"],
    firstRun: "The first analysis takes about a minute because satellite scenes are read live. It is faster after that.",
    empty_t: "Start with your field",
    empty_b: "Draw your plot boundary on the satellite map, or try the sample field in Metro Utara first.",
    risk14: "14-day risk",
    firstStress: "Water stress starts",
    day: "day",
    range: "range",
    ofMembers: "of weather members",
    noStress: "No weather member shows water stress in this window.",
    drivers: "Because",
    recs: "What you can do",
    why: "Why",
    stage: "Crop stage",
    dat: "Days after transplanting",
    unknown: "unknown",
    setDat: "Edit",
    confidence: "Confidence",
    freshness: "Latest clear scene",
    daysAgo: "days ago",
    noScene: "No clear scene: the area is cloud-covered.",
    soil: "Soil moisture 9-27 cm",
    unavailable: "Unavailable data",
    ndvi: "Field NDVI (green) vs surroundings (dashed)",
    ponding: "Standing water in the field · climatology",
    plantH: "Plant height",
    ks: "Water stress coefficient Ks (1 = enough water) · climatology",
    probStress: "Daily chance of water stress",
    probSub: "Daily chance of full submergence",
    river: "GloFAS river flow · 2-year flood threshold",
    hand: "Field height above channel",
    radarT: "Sentinel-1 radar (sees through cloud)",
    radarV: (f: string, r: string, m: string, d: number) => `${f} water in field · surroundings ${r} (usually ${m}) · ${d} days ago`,
    subDays: "Days fully submerged (P50 / P95)",
    pestNote: "Weather suitability over the last 7 and next 7 days. Not detection: still scout the field.",
    scout: "How to scout",
    waterT: "Nearest water sources",
    waterNote: "From OpenStreetMap. Flow and availability are unknown except for large rivers covered by GloFAS.",
    noWater: "No mapped water source within 4 km, or OpenStreetMap is unreachable right now.",
    showRoute: "Show on map",
    sources: "Sources and capture times",
    method: "Method",
    hypo: "HYPOTHETICAL: scenario test, not a forecast.",
    sim: "Simulator",
    rainF: "Rain factor",
    delay: "Rain delayed (days)",
    heat: "Warming (°C)",
    extra: "Extreme rain (mm)",
    extraDay: "on day",
    irr: "Irrigation (mm/day)",
    run: "Run simulation",
    reset: "Back to real conditions",
    print: "Print report",
    dayLabel: "Day",
    play: "Play",
    pause: "Pause",
    pondNow: "P50 water",
    ksNow: "P50 Ks",
    level: { low: "low", medium: "medium", high: "high", unknown: "unknown" },
    stageNames: {
      initial: "initial (seedling)",
      development: "tillering",
      "mid-season": "booting-flowering",
      "late-season": "ripening",
      "harvest-ready": "harvest-ready",
      nursery: "nursery",
      unknown: "unknown",
    } as Record<string, string>,
    climNote: "After day 15, rain uses the 10-year ERA5 mean, not a forecast.",
    stressNow: "Already short of water now",
    legendT: "What the field colour means",
    lgOk: "enough water",
    lgMild: "water stress starting",
    lgSevere: "severe stress",
    lgPond: "ponded",
    lgDeep: "deep water",
    lgSub: "fully submerged",
    lgWater: "water source (OSM)",
    lgRoute: "line to water source",
    today: "today",
    myField: "My field",
    sceneChip: "scene",
    confChip: "confidence",
    stepsT: ["Draw your plot on the map, or use the sample field.", "Jagapadi reads satellite, 51 rain scenarios, river flow and terrain.", "See when it runs dry, when it floods, and what to do."],
    irrAssume: "Assumes no irrigation (worst case for drought). Change it in the simulator if your field gets canal water.",
  },
};

const pct = (v: number) => `${Math.round(v * 100)}%`;
const levelColor = (l: string) => (l === "high" ? "hsl(var(--drought))" : l === "medium" ? "hsl(var(--grain))" : l === "low" ? "hsl(var(--ok))" : "hsl(var(--ink-3))");

export default function Workspace() {
  const { lang } = useLang();
  const s = L[lang];
  const [field, setField] = useState<Polygon | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<[number, number][]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("summary");
  const [mode, setMode] = useState<"real" | "test">("real");
  const [dat, setDat] = useState<number | null>(null);
  const [scenario, setScenario] = useState({ rain_factor: 1, delay_rain_days: 0, temp_delta_c: 0, extra_mm: 0, extra_day: 3, irrigation: 0 });
  const [day, setDay] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [routeTo, setRouteTo] = useState<WaterFeature | null>(null);
  const [focus, setFocus] = useState<[number, number] | null>(null);
  const [basemap, setBasemap] = useState<"esri" | "s2">("esri");
  const [mapImage, setMapImage] = useState<string | null>(null);
  const [fieldName, setFieldName] = useState<string | null>(null);
  const snapRef = useRef<(() => string | null) | null>(null);
  // Farmers see one status and one action; the charts stay one tap away.
  const [view, setViewState] = useState<"simple" | "expert">(() => {
    try {
      return localStorage.getItem("jagapadi-view") === "expert" ? "expert" : "simple";
    } catch {
      return "simple";
    }
  });
  const setView = (v: "simple" | "expert") => {
    setViewState(v);
    try {
      localStorage.setItem("jagapadi-view", v);
    } catch {
      /* storage blocked */
    }
  };
  const [telegram, setTelegram] = useState(false);
  const [watched, setWatched] = useState(false);
  useEffect(() => {
    api.health().then((h) => setTelegram(!!h.telegram), () => setTelegram(false));
  }, []);
  // Snapshot the live map into the report, then print once the image is in the DOM.
  const printReport = () => {
    setMapImage(snapRef.current?.() ?? null);
    window.setTimeout(() => window.print(), 250);
  };
  const abort = useRef<AbortController | null>(null);

  const run = async (geom: Polygon, opts: { dat?: number | null; scen?: Scenario | null; irr?: number | null } = {}) => {
    abort.current?.abort();
    const ac = new AbortController();
    abort.current = ac;
    setLoading(true);
    setError(null);
    try {
      const a = await api.analyze(
        geom,
        { days_after_transplant: opts.dat ?? undefined, scenario: opts.scen ?? undefined, irrigation_mm_day: opts.irr ?? undefined },
        ac.signal,
      );
      setAnalysis(a);
      setDay(0);
      if (a.water_sources?.length) setRouteTo(a.water_sources[0]);
    } catch (e) {
      if ((e as Error).name !== "AbortError") showError(e);
    } finally {
      setLoading(false);
    }
  };

  const showError = (e: unknown) => {
    const m = (e as Error).message;
    setError(m === API_DOWN ? s.apiDown : m);
  };

  const useDemo = async () => {
    setError(null);
    let d;
    try {
      d = await api.demoField();
    } catch (e) {
      showError(e);
      return;
    }
    setField(d.geometry);
    setFieldName(d.name.split(" (")[0]);
    setDraft([]);
    setDrawing(false);
    run(d.geometry, { dat });
  };

  const finishDraw = async () => {
    if (draft.length < 3) return;
    const ring = [...draft, draft[0]];
    const geom: Polygon = { type: "Polygon", coordinates: [ring] };
    setDrawing(false);
    try {
      const v = await api.validate(geom);
      if (!v.valid) {
        setError(v.reason ?? "invalid field");
        setDraft([]);
        return;
      }
      setField(geom);
      setFieldName(null);
      setDraft([]);
      run(geom, { dat });
    } catch (e) {
      showError(e);
    }
  };

  const runScenario = () => {
    if (!field) return;
    const scen: Scenario = {
      rain_factor: scenario.rain_factor,
      delay_rain_days: scenario.delay_rain_days,
      temp_delta_c: scenario.temp_delta_c,
      extra_rain: scenario.extra_mm > 0 ? [{ day: scenario.extra_day, mm: scenario.extra_mm }] : [],
    };
    run(field, { dat, scen, irr: scenario.irrigation });
  };

  const setModeAndRun = (m: "real" | "test") => {
    setMode(m);
    if (m === "test") setView("expert");
    if (m === "real" && field && analysis?.hypothetical) run(field, { dat });
  };

  // A field opened from the officer dashboard arrives as router state.
  const location = useLocation();
  useEffect(() => {
    const st = location.state as { geometry?: Polygon; name?: string; dat?: number | null } | null;
    if (!st?.geometry) return;
    setField(st.geometry);
    setFieldName(st.name ?? null);
    setDat(st.dat ?? null);
    run(st.geometry, { dat: st.dat ?? null });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);
  useEffect(() => setWatched(false), [field]);

  // Day player for the simulation timeline.
  const n = analysis?.waterbalance.dates.length ?? 0;
  useEffect(() => {
    if (!playing || !n) return;
    const id = window.setInterval(() => setDay((d) => (d + 1) % n), 650);
    return () => window.clearInterval(id);
  }, [playing, n]);

  const wb = analysis?.waterbalance;
  const fieldColor = useMemo(() => {
    if (!wb) return "#7fa35b";
    if (tab === "flood") {
      const depth = wb.ponding.p50[day] ?? 0;
      const h = wb.plant_height_mm[day] ?? 600;
      const r = Math.min(1, depth / h);
      return r > 0.85 ? "#1f5fa8" : r > 0.4 ? "#3a8fd0" : depth > 20 ? "#7cc3e6" : "#7fa35b";
    }
    const ks = wb.ks.p50[day] ?? 1;
    return ks < 0.6 ? "#c4571e" : ks < 0.95 ? "#e2a93b" : (wb.ponding.p50[day] ?? 0) > 5 ? "#5fb3c9" : "#7fa35b";
  }, [wb, day, tab]);

  return (
    <div className={`ws ${analysis?.hypothetical ? "is-hypo" : ""}`}>
      <header className="ws-top">
        <Link to="/" className="ws-logo" aria-label="Jagapadi, kembali ke beranda">
          <Logo size={28} />
        </Link>
        <div className="seg" role="group" aria-label={`${s.viewSimple} / ${s.viewExpert}`}>
          <button type="button" aria-pressed={view === "simple"} onClick={() => (setView("simple"), setModeAndRun("real"))}>
            {s.viewSimple}
          </button>
          <button type="button" aria-pressed={view === "expert"} onClick={() => setView("expert")}>
            {s.viewExpert}
          </button>
        </div>
        {view === "expert" && (
          <div className="seg" role="group" aria-label="Mode">
            <button type="button" aria-pressed={mode === "real"} onClick={() => setModeAndRun("real")}>
              {s.real}
            </button>
            <button type="button" aria-pressed={mode === "test"} onClick={() => setModeAndRun("test")}>
              {s.test}
            </button>
          </div>
        )}
        <div className="ws-top-right">
          {field && analysis?.status === "ok" && (
            <button
              type="button"
              className="btn btn-ghost small"
              aria-pressed={watched}
              onClick={() => (addField({ name: fieldName ?? s.myField, geometry: field, dat }), setWatched(true))}
            >
              {watched ? `✓ ${s.watched}` : `+ ${s.watch}`}
            </button>
          )}
          <Link to="/ppl" className="btn btn-ghost small">
            {s.officer}
          </Link>
          {analysis && (
            <button type="button" className="btn btn-ghost small" onClick={printReport}>
              {s.print}
            </button>
          )}
          <LangToggle />
        </div>
      </header>

      <div className="ws-body">
        <div className="ws-map">
          <FieldMap
            field={field}
            drawing={drawing}
            draft={draft}
            onAddPoint={(pt) => setDraft((d) => [...d, pt])}
            onFinish={finishDraw}
            water={analysis?.water_sources ?? []}
            routeTo={routeTo}
            fieldColor={fieldColor}
            fieldLabel=""
            focus={focus}
            basemap={basemap}
            onSnapshot={(fn) => (snapRef.current = fn)}
          />
          <div className="seg basemap-toggle" role="group" aria-label="Basemap">
            <button type="button" aria-pressed={basemap === "esri"} onClick={() => setBasemap("esri")}>
              Esri
            </button>
            <button type="button" aria-pressed={basemap === "s2"} onClick={() => setBasemap("s2")} title="Sentinel-2 cloudless 2023 (EOX)">
              S2 cloudless
            </button>
          </div>
          {wb && (
            <div className="legend felt" aria-label={s.legendT}>
              <p className="legend-t">{s.legendT}</p>
              {(tab === "flood"
                ? [
                    ["#7fa35b", s.lgOk],
                    ["#7cc3e6", s.lgPond],
                    ["#3a8fd0", s.lgDeep],
                    ["#1f5fa8", s.lgSub],
                  ]
                : [
                    ["#7fa35b", s.lgOk],
                    ["#e2a93b", s.lgMild],
                    ["#c4571e", s.lgSevere],
                  ]
              ).map(([c, t]) => (
                <p key={t}>
                  <span className="sw" style={{ background: c }} />
                  {t}
                </p>
              ))}
              <p>
                <span className="sw line" />
                {s.lgWater}
              </p>
              <p>
                <span className="sw dash" />
                {s.lgRoute}
              </p>
            </div>
          )}
          <div className="map-tools">
            {!drawing ? (
              <>
                <button type="button" className="btn btn-primary small" onClick={() => (setDrawing(true), setDraft([]))}>
                  {s.draw}
                </button>
                <button type="button" className="btn btn-ghost small" onClick={useDemo}>
                  {s.demo}
                </button>
              </>
            ) : (
              <>
                <p className="draw-hint felt">{s.drawHint}</p>
                <button type="button" className="btn btn-primary small" disabled={draft.length < 3} onClick={finishDraw}>
                  {s.finish} ({draft.length})
                </button>
                <button type="button" className="btn btn-ghost small" onClick={() => (setDrawing(false), setDraft([]))}>
                  {s.cancel}
                </button>
              </>
            )}
          </div>
          {wb && (
            <div className="player felt">
              <button type="button" className="play-btn" onClick={() => setPlaying((p) => !p)} aria-pressed={playing} aria-label={playing ? s.pause : s.play}>
                {playing ? (
                  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                    <rect x="3" y="2" width="3.5" height="12" rx="1" fill="currentColor" />
                    <rect x="9.5" y="2" width="3.5" height="12" rx="1" fill="currentColor" />
                  </svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="M4 2.5v11l9-5.5z" fill="currentColor" />
                  </svg>
                )}
              </button>
              <div className="player-main">
                <div className="player-top">
                  <span>
                    <b>
                      {s.dayLabel} {day}
                    </b>{" "}
                    · {wb.dates[day]} {day === 0 ? `· ${s.today}` : ""}
                  </span>
                  {view === "simple" ? (
                    <span className="player-read">
                      {s.waterIn} <b>{Math.round(wb.ponding.p50[day])} mm</b> · <b>{s.ksPlain[wb.ks.p50[day] < 0.6 ? 2 : wb.ks.p50[day] < 0.95 ? 1 : 0]}</b>
                    </span>
                  ) : (
                    <span className="player-read">
                      {s.pondNow} <b>{wb.ponding.p50[day]} mm</b> · {s.ksNow} <b>{wb.ks.p50[day]}</b>
                    </span>
                  )}
                </div>
                {/* Daily risk strip: darker cells are days more weather members put the field in trouble. */}
                <div className="heat" role="presentation" style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}>
                  {(tab === "flood" ? wb.prob_submerged : wb.prob_stress).map((v, i) => (
                    <span
                      key={i}
                      className={i === day ? "on" : ""}
                      style={{ ["--v" as string]: v, ["--c" as string]: tab === "flood" ? "var(--flood)" : "var(--drought)" }}
                      onClick={() => setDay(i)}
                    />
                  ))}
                </div>
                <input type="range" min={0} max={n - 1} value={day} onChange={(e) => setDay(+e.target.value)} aria-label={s.dayLabel} />
              </div>
            </div>
          )}
        </div>

        <aside className="drawer" aria-label="Analisis lahan">
          {analysis?.hypothetical && <p className="hypo-banner">{s.hypo}</p>}
          {mode === "test" && field && (
            <Simulator s={s} value={scenario} onChange={setScenario} onRun={runScenario} busy={loading} n={n || 30} />
          )}
          {error && <p className="error felt">{error}</p>}
          {loading && <Loading s={s} />}
          {!loading && !analysis && !error && (
            <div className="empty">
              <img src="/mascot/mascot-laptop-256.png" srcSet="/mascot/mascot-laptop-256@2x.png 2x" width={180} height={180} alt="" />
              <h2>{s.empty_t}</h2>
              <p>{s.empty_b}</p>
              <ol className="empty-steps">
                {s.stepsT.map((x, i) => (
                  <li key={i}>
                    <span>0{i + 1}</span>
                    {x}
                  </li>
                ))}
              </ol>
              <div className="empty-ctas">
                <button type="button" className="btn btn-primary" onClick={() => (setDrawing(true), setDraft([]))}>
                  {s.draw}
                </button>
                <button type="button" className="btn btn-ghost" onClick={useDemo}>
                  {s.demo}
                </button>
              </div>
            </div>
          )}
          {!loading && analysis?.status === "insufficient-data" && (
            <div className="felt pad">
              <p>Weather data unavailable: {analysis.unavailable.map((u) => `${u.name} (${u.reason})`).join(", ")}</p>
            </div>
          )}
          {!loading && analysis?.status === "ok" && field && view === "simple" && !analysis.hypothetical && (
            <>
              <FieldHeader a={analysis} s={s} name={fieldName ?? s.myField} />
              <SimpleView
                a={analysis}
                field={field}
                name={fieldName ?? s.myField}
                dat={dat}
                telegram={telegram}
                onDetails={() => (setView("expert"), setTab("summary"))}
              />
            </>
          )}
          {!loading && analysis?.status === "ok" && (view === "expert" || analysis.hypothetical) && (
            <>
              <FieldHeader a={analysis} s={s} name={fieldName ?? s.myField} />
              <nav className="tabs" role="tablist">
                {(["summary", "drought", "flood", "pest", "water", "data"] as Tab[]).map((k) => (
                  <button key={k} role="tab" type="button" aria-selected={tab === k} onClick={() => setTab(k)}>
                    <TabIcon tab={k} />
                    {s[k]}
                  </button>
                ))}
              </nav>
              <div className="tab-body" role="tabpanel">
                {tab === "summary" && <Summary a={analysis} s={s} dat={dat} setDat={(v) => (setDat(v), field && run(field, { dat: v }))} goto={setTab} />}
                {tab === "summary" && telegram && field && <AlertButton field={field} name={fieldName ?? s.myField} dat={dat} />}
                {tab === "drought" && <Drought a={analysis} s={s} day={day} />}
                {tab === "flood" && <Flood a={analysis} s={s} day={day} />}
                {tab === "pest" && <Pests a={analysis} s={s} />}
                {tab === "water" && (
                  <Water
                    a={analysis}
                    s={s}
                    onPick={(w) => {
                      setRouteTo(w);
                      setFocus(w.nearest_point);
                    }}
                  />
                )}
                {tab === "data" && <DataTab a={analysis} s={s} />}
              </div>
            </>
          )}
        </aside>
      </div>

      {field && analysis?.status === "ok" && <Chat field={field} dat={dat} />}
      {analysis?.status === "ok" && <PrintReport a={analysis} mapImage={mapImage} />}
    </div>
  );
}

type S = (typeof L)["id"];

function Loading({ s }: { s: S }) {
  return (
    <div className="loading felt pad" role="status" aria-live="polite">
      <img src="/mascot/mascot-laptop-256.png" srcSet="/mascot/mascot-laptop-256@2x.png 2x" width={120} height={120} alt="" className="bob" />
      <h2>{s.analyzing}</h2>
      <ul>
        {s.steps.map((x) => (
          <li key={x}>{x}</li>
        ))}
      </ul>
      <p className="muted small">{s.firstRun}</p>
    </div>
  );
}

/* Semicircle gauge: the arc fills with the 14-day probability; colour follows the level. */
function RiskCard({ title, risk, s, kind }: { title: string; risk: Risk; s: S; kind: string }) {
  const len = Math.PI * 38;
  return (
    <div className="risk felt" style={{ ["--lv" as string]: levelColor(risk.level) }}>
      <svg className="gauge" viewBox="0 0 100 58" aria-hidden="true">
        <path d="M12 50 A38 38 0 0 1 88 50" className="g-track" />
        <path d="M12 50 A38 38 0 0 1 88 50" className="g-fill" style={{ strokeDasharray: `${len * risk.probability} ${len}` }} />
      </svg>
      <div className="risk-text">
        <p className="risk-t">
          <IslandGlyph kind={kind} />
          {title}
        </p>
        <p className="risk-v">
          {pct(risk.probability)} <span>{s.level[risk.level]}</span>
        </p>
        <p className="risk-sub">{s.risk14}</p>
      </div>
    </div>
  );
}

function FieldHeader({ a, s, name }: { a: Analysis; s: S; name: string }) {
  const age = a.satellite.latest_clear_age_days;
  return (
    <header className="field-head">
      <div>
        <p className="eyebrow">{s.stageNames[a.crop.stage] ?? a.crop.stage}</p>
        <h2>{name}</h2>
        <p className="field-meta tabular">
          {a.field.area_ha} ha · {a.field.lat.toFixed(4)}, {a.field.lon.toFixed(4)}
        </p>
      </div>
      <div className="chips">
        <span className={`chip-s ${age !== null && age <= 10 ? "good" : "warn"}`}>
          {s.sceneChip} {age !== null ? `${age} ${s.daysAgo}` : "–"}
        </span>
        <span className={`chip-s c-${a.confidence}`}>
          {s.confChip} {s.level[a.confidence]}
        </span>
      </div>
    </header>
  );
}

function TabIcon({ tab }: { tab: Tab }) {
  const p = { width: 15, height: 15, viewBox: "0 0 16 16", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  switch (tab) {
    case "summary":
      return (
        <svg {...p}>
          <rect x="2" y="2" width="5" height="5" rx="1.2" />
          <rect x="9" y="2" width="5" height="5" rx="1.2" />
          <rect x="2" y="9" width="5" height="5" rx="1.2" />
          <rect x="9" y="9" width="5" height="5" rx="1.2" />
        </svg>
      );
    case "drought":
      return (
        <svg {...p}>
          <circle cx="8" cy="6" r="3" />
          <path d="M2 13h12M4 10.5l1 1M12 10.5l-1 1M8 1v1" />
        </svg>
      );
    case "flood":
      return (
        <svg {...p}>
          <path d="M8 1.5S4 6 4 8.5a4 4 0 0 0 8 0C12 6 8 1.5 8 1.5Z" />
          <path d="M1.5 14.5c1.5-1 2.5 1 4 0s2.5 1 4 0 2.5 1 5 0" />
        </svg>
      );
    case "pest":
      return (
        <svg {...p}>
          <ellipse cx="8" cy="9" rx="3" ry="4.5" />
          <path d="M5 6 2.5 4.5M11 6l2.5-1.5M5 10H2M11 10h3M6.5 4.5 6 2M9.5 4.5 10 2" />
        </svg>
      );
    case "water":
      return (
        <svg {...p}>
          <path d="M1.5 5c2-1.5 3 1.5 5 0s3 1.5 5 0 2 1 3 0M1.5 10c2-1.5 3 1.5 5 0s3 1.5 5 0 2 1 3 0" />
        </svg>
      );
    default:
      return (
        <svg {...p}>
          <ellipse cx="8" cy="3.5" rx="5.5" ry="2" />
          <path d="M2.5 3.5v9c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2v-9M2.5 8c0 1.1 2.5 2 5.5 2s5.5-.9 5.5-2" />
        </svg>
      );
  }
}

function Recs({ recs, s }: { recs: Rec[]; s: S }) {
  const { lang } = useLang();
  return (
    <section className="block">
      <h3>{s.recs}</h3>
      <ol className="recs">
        {recs.map((r, i) => (
          <li key={i}>
            <span className={`feas f${r.feasibility}`} aria-label={`feasibility ${r.feasibility}`}>
              {r.feasibility}
            </span>
            <div>
              <p>{r.text[lang]}</p>
              <p className="why">
                {s.why}: {r.why[lang]}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Drivers({ items, s }: { items: Txt[]; s: S }) {
  const { lang } = useLang();
  return (
    <section className="block">
      <h3>{s.drivers}</h3>
      <ul className="drivers">
        {items.map((d, i) => (
          <li key={i}>{tr(d, lang)}</li>
        ))}
      </ul>
    </section>
  );
}

function Summary({ a, s, dat, setDat, goto }: { a: Analysis; s: S; dat: number | null; setDat: (v: number | null) => void; goto: (t: Tab) => void }) {
  const { lang } = useLang();
  const [edit, setEdit] = useState(false);
  const [val, setVal] = useState<string>(String(a.crop.days_after_transplant ?? ""));
  const lc = a.satellite.latest_clear;
  const pts = a.satellite.series
    .filter((x) => x.field.usable || x.neighbours.usable)
    .map((x) => ({ date: x.datetime.slice(0, 10), field: x.field.ndvi_mean, neighbours: x.neighbours.ndvi_mean }));
  return (
    <>
      <div className="risk-row">
        <button type="button" className="as-card" onClick={() => goto("drought")}>
          <RiskCard title={s.drought} risk={a.drought.risk} s={s} kind="drought" />
        </button>
        <button type="button" className="as-card" onClick={() => goto("flood")}>
          <RiskCard title={s.flood} risk={a.flood.risk} s={s} kind="flood" />
        </button>
      </div>
      <dl className="facts felt pad">
        <div>
          <dt>{s.stage}</dt>
          <dd>{s.stageNames[a.crop.stage] ?? a.crop.stage}</dd>
        </div>
        <div>
          <dt>{s.dat}</dt>
          <dd>
            {edit ? (
              <form
                className="inline-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  setEdit(false);
                  setDat(val === "" ? null : Math.max(-30, Math.min(200, +val)));
                }}
              >
                <input type="number" inputMode="numeric" value={val} onChange={(e) => setVal(e.target.value)} aria-label={s.dat} autoFocus />
                <button className="btn btn-primary small" type="submit">
                  OK
                </button>
              </form>
            ) : (
              <>
                {a.crop.days_after_transplant ?? s.unknown}{" "}
                <button type="button" className="link" onClick={() => setEdit(true)}>
                  {s.setDat}
                </button>
              </>
            )}
            <small>{dat !== null ? "" : tr(a.crop.basis, lang)}</small>
          </dd>
        </div>
        <div>
          <dt>{s.freshness}</dt>
          <dd>{lc ? `${lc.datetime.slice(0, 10)} (${a.satellite.latest_clear_age_days} ${s.daysAgo})` : s.noScene}</dd>
        </div>
        {lc && (
          <div>
            <dt>NDVI / NDWI</dt>
            <dd>
              {lc.field.ndvi_mean?.toFixed(2)} / {lc.field.ndwi_mean?.toFixed(2)}
            </dd>
          </div>
        )}
        <div>
          <dt>{s.soil}</dt>
          <dd>{a.weather.soil_moisture_now !== null ? `${a.weather.soil_moisture_now.toFixed(3)} m³/m³` : s.unknown}</dd>
        </div>
        <div>
          <dt>{s.confidence}</dt>
          <dd>{s.level[a.confidence]}</dd>
        </div>
      </dl>
      {pts.length > 0 && <SeriesChart points={pts} label={s.ndvi} />}
      {a.unavailable.length > 0 && (
        <section className="block warn">
          <h3>{s.unavailable}</h3>
          <ul>
            {a.unavailable.map((u) => (
              <li key={u.name}>
                <b>{u.name}</b>: {u.reason}
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="disclaimer">{tr(a.disclaimer, lang)}</p>
    </>
  );
}

function Drought({ a, s, day }: { a: Analysis; s: S; day: number }) {
  const wb = a.waterbalance;
  const fs = a.drought.risk.first_stress_day!;
  return (
    <>
      <RiskCard title={s.drought} risk={a.drought.risk} s={s} kind="drought" />
      <section className="block">
        <h3>{s.firstStress}</h3>
        {fs.p50 === 0 && fs.p95 === 0 ? (
          <p className="big-read now">
            <b>{s.stressNow}</b>
            <small>
              {pct(fs.share_of_members)} {s.ofMembers}
            </small>
          </p>
        ) : fs.p50 !== null ? (
          <p className="big-read">
            {s.day} <b>{fs.p50}</b> <span>({s.range} {fs.p5}-{fs.p95})</span>
            <small>
              {pct(fs.share_of_members)} {s.ofMembers}
            </small>
          </p>
        ) : (
          <p>{s.noStress}</p>
        )}
      </section>
      <FanChart
        dates={wb.dates}
        p5={wb.ks.p5}
        p50={wb.ks.p50}
        p95={wb.ks.p95}
        unit="Ks"
        label={s.ks}
        color="hsl(var(--drought))"
        yMin={0}
        yMax={1.05}
        day={day}
        extendedFrom={wb.forecast_days_from_ensemble}
      />
      <ProbBars dates={wb.dates} values={wb.prob_stress} color="hsl(var(--drought))" label={s.probStress} day={day} />
      <p className="muted small">{s.climNote}</p>
      <Drivers items={[...a.drought.risk.drivers, ...wb.initial_state.basis, wb.rain_basis]} s={s} />
      {!a.hypothetical && <p className="note-inline">{s.irrAssume}</p>}
      <Recs recs={a.drought.recommendations} s={s} />
    </>
  );
}

function Flood({ a, s, day }: { a: Analysis; s: S; day: number }) {
  const wb = a.waterbalance;
  const sub = a.flood.risk.max_submergence_days!;
  return (
    <>
      <RiskCard title={s.flood} risk={a.flood.risk} s={s} kind="flood" />
      <FanChart
        dates={wb.dates}
        p5={wb.ponding.p5}
        p50={wb.ponding.p50}
        p95={wb.ponding.p95}
        unit="mm"
        label={s.ponding}
        color="hsl(var(--flood))"
        line={wb.plant_height_mm}
        lineLabel={s.plantH}
        day={day}
        extendedFrom={wb.forecast_days_from_ensemble}
      />
      <ProbBars dates={wb.dates} values={wb.prob_submerged} color="hsl(var(--flood))" label={s.probSub} day={day} />
      <dl className="facts felt pad">
        <div>
          <dt>{s.subDays}</dt>
          <dd>
            {sub.p50} / {sub.p95}
          </dd>
        </div>
        <div>
          <dt>{s.hand}</dt>
          <dd>{a.hand ? `${a.hand.height_above_channel_m} m · ${a.hand.channel} (${a.hand.channel_distance_m} m)` : s.unknown}</dd>
        </div>
        <div>
          <dt>{s.radarT}</dt>
          <dd>
            {a.radar?.latest.field.usable
              ? s.radarV(
                  pct(a.radar.latest.field.water_fraction ?? 0),
                  a.radar.ring_water_now === null ? "–" : pct(a.radar.ring_water_now),
                  a.radar.ring_water_median === null ? "–" : pct(a.radar.ring_water_median),
                  a.radar.latest_age_days,
                )
              : s.unknown}
          </dd>
        </div>
      </dl>
      {a.river && a.river.forecast_p50.length > 0 && (
        <FanChart
          dates={a.river.forecast_dates}
          p5={a.river.forecast_p50}
          p50={a.river.forecast_p50}
          p95={a.river.forecast_p95}
          unit="m³/s"
          label={s.river}
          color="hsl(var(--teal))"
          line={a.river.threshold_2y_m3s}
          lineLabel="2y"
        />
      )}
      {a.river && <p className="muted small">{a.river.note}</p>}
      <Drivers items={a.flood.risk.drivers} s={s} />
      <Recs recs={a.flood.recommendations} s={s} />
    </>
  );
}

function Pests({ a, s }: { a: Analysis; s: S }) {
  const { lang } = useLang();
  return (
    <>
      <p className="muted small">{s.pestNote}</p>
      <ul className="pests">
        {a.pest.map((p) => (
          <li key={p.id} className="felt pad" style={{ ["--lv" as string]: levelColor(p.level) }}>
            <div className="pest-head">
              <h3>{p.name[lang]}</h3>
              <span className="pill">{s.level[p.level]}</span>
            </div>
            <p className="small">{tr(p.reason, lang)}</p>
            <p className="small muted">{p.favourable}</p>
            {p.action && (
              <p className="small">
                <b>{s.scout}:</b> {p.action[lang]}
              </p>
            )}
            <p className="tiny muted">{p.reference}</p>
          </li>
        ))}
      </ul>
    </>
  );
}

function Water({ a, s, onPick }: { a: Analysis; s: S; onPick: (w: WaterFeature) => void }) {
  return (
    <>
      <h3 className="h3">{s.waterT}</h3>
      <p className="muted small">{s.waterNote}</p>
      {a.water_sources.length === 0 ? (
        <p className="felt pad">{s.noWater}</p>
      ) : (
        <ul className="water-list">
          {a.water_sources.slice(0, 12).map((w) => (
            <li key={w.osm_id} className="felt">
              <div>
                <b>{w.name || w.kind}</b>
                <span className="muted small">
                  {w.kind}
                  {w.intermittent ? " · musiman" : ""}
                </span>
              </div>
              <span className="dist">{w.distance_m < 1000 ? `${w.distance_m} m` : `${(w.distance_m / 1000).toFixed(1)} km`}</span>
              <button type="button" className="btn btn-ghost small" onClick={() => onPick(w)}>
                {s.showRoute}
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function DataTab({ a, s }: { a: Analysis; s: S }) {
  const { lang } = useLang();
  const p = a.waterbalance.params;
  return (
    <>
      <section className="block">
        <h3>{s.sources}</h3>
        <ul className="drivers">
          {a.sources.map((x, i) => (
            <li key={i}>
              {x.name} · <time>{x.captured_at}</time>
            </li>
          ))}
        </ul>
      </section>
      <section className="block">
        <h3>{s.method}</h3>
        <ul className="drivers small">
          <li>FAO-56 paddy water balance: TAW {p.taw_mm} mm, RAW {p.raw_mm} mm, percolation {p.percolation_mm} mm/day, outlet {p.outlet_mm} mm, bund {p.bund_mm} mm.</li>
          <li>{tr(a.waterbalance.rain_basis, lang)}; ET0 from Open-Meteo (FAO Penman-Monteith).</li>
          <li>Drought probability = 1 − (1 − physics) × (1 − satellite signals). Physics: {pct(a.drought.risk.physics_probability)}; satellite: {pct(a.drought.risk.satellite_adjustment)}.</li>
          <li>{a.terrain?.note}</li>
          <li>{tr(a.crop.basis, lang)}</li>
        </ul>
      </section>
      <p className="disclaimer">{tr(a.disclaimer, lang)}</p>
      <p className="tiny muted">generated {a.generated_at}</p>
    </>
  );
}

function Simulator({
  s,
  value,
  onChange,
  onRun,
  busy,
  n,
}: {
  s: S;
  value: { rain_factor: number; delay_rain_days: number; temp_delta_c: number; extra_mm: number; extra_day: number; irrigation: number };
  onChange: (v: typeof value) => void;
  onRun: () => void;
  busy: boolean;
  n: number;
}) {
  const set = (k: keyof typeof value) => (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: +e.target.value });
  const row = (k: keyof typeof value, label: string, min: number, max: number, step: number, fmt = (v: number) => String(v)) => (
    <label className="sim-row">
      <span>
        {label} <b>{fmt(value[k])}</b>
      </span>
      <input type="range" min={min} max={max} step={step} value={value[k]} onChange={set(k)} />
    </label>
  );
  return (
    <section className="sim felt pad" aria-label={s.sim}>
      <h3>{s.sim}</h3>
      {row("rain_factor", s.rainF, 0, 2, 0.1, (v) => `×${v.toFixed(1)}`)}
      {row("delay_rain_days", s.delay, 0, 20, 1)}
      {row("temp_delta_c", s.heat, 0, 4, 0.5, (v) => `+${v}`)}
      {row("extra_mm", s.extra, 0, 250, 10)}
      {value.extra_mm > 0 && row("extra_day", s.extraDay, 0, n - 1, 1)}
      {row("irrigation", s.irr, 0, 15, 1)}
      <button type="button" className="btn btn-primary" onClick={onRun} disabled={busy}>
        {s.run}
      </button>
    </section>
  );
}
