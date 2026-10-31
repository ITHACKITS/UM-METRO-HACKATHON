import type { Analysis } from "../lib/api";
import { tr } from "../lib/api";
import { useLang } from "../lib/i18n";
import { FanChart, ProbBars } from "../components/Charts";
import { LogoMark } from "../components/Logo";
import "./print.css";

const T = {
  id: {
    title: "Laporan Lahan",
    sub: "Pemantauan kekeringan, banjir dan hama padi",
    hypo: "HIPOTETIS: hasil uji skenario, bukan prakiraan",
    field: "Lahan",
    area: "Luas",
    coords: "Titik tengah",
    made: "Dibuat",
    stage: "Fase tanaman",
    dat: "Hari setelah tanam",
    scene: "Citra bersih terakhir",
    conf: "Keyakinan analisis",
    drought: "Kekeringan 14 hari",
    flood: "Banjir 14 hari",
    firstStress: "Stres air mulai",
    sub_: "Hari terendam penuh",
    day: "hari ke",
    none: "tidak ada skenario",
    map: "Peta lahan dan sumber air",
    mapMissing: "Cuplikan peta tidak tersedia. Batas lahan:",
    why: "Karena",
    actions: "Yang bisa dilakukan, urut dari paling mudah",
    feas: "Kemudahan",
    act: "Tindakan",
    reason: "Alasan",
    pests: "Kesesuaian cuaca untuk hama dan penyakit",
    pestNote: "Bukan deteksi. Tetap cek langsung di sawah.",
    pest: "Hama/penyakit",
    level: "Tingkat",
    water: "Sumber air terdekat (OpenStreetMap)",
    noWater: "Tidak ada sumber air terpetakan, atau OpenStreetMap tidak dapat diakses saat laporan dibuat.",
    name: "Nama",
    kind: "Jenis",
    dist: "Jarak",
    sources: "Sumber data dan waktu pengambilan",
    method: "Metode",
    unavailable: "Data yang tidak tersedia",
    ks: "Koefisien stres air Ks (1 = cukup air)",
    pond: "Genangan air (mm) dan tinggi tanaman",
    pStress: "Peluang stres air per hari",
    levels: { low: "rendah", medium: "sedang", high: "tinggi", unknown: "tidak diketahui" },
    stageNames: {
      initial: "awal (bibit)",
      development: "anakan",
      "mid-season": "bunting-berbunga",
      "late-season": "pemasakan",
      "harvest-ready": "siap panen",
      nursery: "persemaian",
      unknown: "belum diketahui",
    } as Record<string, string>,
    sign: "Diperiksa oleh (PPL / ketua kelompok tani)",
  },
  en: {
    title: "Field Report",
    sub: "Rice drought, flood and pest monitoring",
    hypo: "HYPOTHETICAL: scenario test, not a forecast",
    field: "Field",
    area: "Area",
    coords: "Centroid",
    made: "Generated",
    stage: "Crop stage",
    dat: "Days after transplanting",
    scene: "Latest clear scene",
    conf: "Analysis confidence",
    drought: "Drought, 14 days",
    flood: "Flood, 14 days",
    firstStress: "Water stress starts",
    sub_: "Days fully submerged",
    day: "day",
    none: "no member",
    map: "Field and water sources",
    mapMissing: "Map snapshot unavailable. Field boundary:",
    why: "Because",
    actions: "What to do, easiest first",
    feas: "Ease",
    act: "Action",
    reason: "Reason",
    pests: "Weather suitability for pests and diseases",
    pestNote: "Not detection. Still scout the field.",
    pest: "Pest/disease",
    level: "Level",
    water: "Nearest water sources (OpenStreetMap)",
    noWater: "No mapped water source, or OpenStreetMap was unreachable when this report was made.",
    name: "Name",
    kind: "Type",
    dist: "Distance",
    sources: "Data sources and capture times",
    method: "Method",
    unavailable: "Unavailable data",
    ks: "Water stress coefficient Ks (1 = enough water)",
    pond: "Standing water (mm) and plant height",
    pStress: "Daily chance of water stress",
    levels: { low: "low", medium: "medium", high: "high", unknown: "unknown" },
    stageNames: {
      initial: "initial (seedling)",
      development: "tillering",
      "mid-season": "booting-flowering",
      "late-season": "ripening",
      "harvest-ready": "harvest-ready",
      nursery: "nursery",
      unknown: "unknown",
    } as Record<string, string>,
    sign: "Reviewed by (extension officer / farmer group head)",
  },
};

const pct = (v: number) => `${Math.round(v * 100)}%`;

export function PrintReport({ a, mapImage }: { a: Analysis; mapImage: string | null }) {
  const { lang } = useLang();
  const t = T[lang];
  const wb = a.waterbalance;
  const fs = a.drought.risk.first_stress_day!;
  const sub = a.flood.risk.max_submergence_days!;
  const lc = a.satellite.latest_clear;
  const recs = [
    ...a.drought.recommendations.map((r) => ({ ...r, hazard: t.drought })),
    ...a.flood.recommendations.map((r) => ({ ...r, hazard: t.flood })),
  ].sort((x, y) => x.feasibility - y.feasibility);

  return (
    <article className="print-report" aria-hidden="true">
      <header className="pr-head">
        <div className="pr-brand">
          <LogoMark size={34} />
          <div>
            <p className="pr-word">tuai</p>
            <p className="pr-sub">{t.sub}</p>
          </div>
        </div>
        <div className="pr-title">
          <h1>{t.title}</h1>
          <p>
            {t.made}: {new Date(a.generated_at).toLocaleString(lang === "id" ? "id-ID" : "en-GB")}
          </p>
        </div>
      </header>
      {a.hypothetical && <p className="pr-stamp">{t.hypo}</p>}

      <section className="pr-meta">
        <dl>
          <div>
            <dt>{t.area}</dt>
            <dd>{a.field.area_ha} ha</dd>
          </div>
          <div>
            <dt>{t.coords}</dt>
            <dd>
              {a.field.lat.toFixed(5)}, {a.field.lon.toFixed(5)}
            </dd>
          </div>
          <div>
            <dt>{t.stage}</dt>
            <dd>{t.stageNames[a.crop.stage] ?? a.crop.stage}</dd>
          </div>
          <div>
            <dt>{t.dat}</dt>
            <dd>{a.crop.days_after_transplant ?? "–"}</dd>
          </div>
          <div>
            <dt>{t.scene}</dt>
            <dd>{lc ? `${lc.datetime.slice(0, 10)} · NDVI ${lc.field.ndvi_mean?.toFixed(2)}` : "–"}</dd>
          </div>
          <div>
            <dt>{t.conf}</dt>
            <dd>{t.levels[a.confidence]}</dd>
          </div>
        </dl>
      </section>

      <section className="pr-kpis">
        <div className={`pr-kpi lv-${a.drought.risk.level}`}>
          <p className="k">{t.drought}</p>
          <p className="v">
            {t.levels[a.drought.risk.level]} <span>{pct(a.drought.risk.probability)}</span>
          </p>
          <p className="d">
            {t.firstStress}: {fs.p50 !== null ? `${t.day} ${fs.p50} (P5–P95 ${fs.p5}–${fs.p95})` : t.none}
          </p>
        </div>
        <div className={`pr-kpi lv-${a.flood.risk.level}`}>
          <p className="k">{t.flood}</p>
          <p className="v">
            {t.levels[a.flood.risk.level]} <span>{pct(a.flood.risk.probability)}</span>
          </p>
          <p className="d">
            {t.sub_}: P50 {sub.p50} · P95 {sub.p95}
          </p>
        </div>
      </section>

      <section className="pr-grid">
        <figure className="pr-map">
          <figcaption>{t.map}</figcaption>
          {mapImage ? (
            <img src={mapImage} alt="" />
          ) : (
            <p className="pr-muted">
              {t.mapMissing} {a.field.lat.toFixed(4)}, {a.field.lon.toFixed(4)}
            </p>
          )}
        </figure>
        <div className="pr-why">
          <h2>{t.why}</h2>
          <ul>
            {[...a.drought.risk.drivers, ...a.flood.risk.drivers].map((d, i) => (
              <li key={i}>{tr(d, lang)}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="pr-charts">
        <FanChart dates={wb.dates} p5={wb.ks.p5} p50={wb.ks.p50} p95={wb.ks.p95} unit="Ks" label={t.ks} color="#c4571e" yMin={0} yMax={1.05} extendedFrom={wb.forecast_days_from_ensemble} />
        <FanChart dates={wb.dates} p5={wb.ponding.p5} p50={wb.ponding.p50} p95={wb.ponding.p95} unit="mm" label={t.pond} color="#1f6fa8" line={wb.plant_height_mm} extendedFrom={wb.forecast_days_from_ensemble} />
        <ProbBars dates={wb.dates} values={wb.prob_stress} color="#c4571e" label={t.pStress} />
      </section>

      <section className="pr-break">
        <h2>{t.actions}</h2>
        <table>
          <thead>
            <tr>
              <th>{t.feas}</th>
              <th>{t.act}</th>
              <th>{t.reason}</th>
            </tr>
          </thead>
          <tbody>
            {recs.map((r, i) => (
              <tr key={i}>
                <td className="c">
                  <span className={`pr-feas f${r.feasibility}`}>{r.feasibility}</span>
                  <small>{r.hazard}</small>
                </td>
                <td>{r.text[lang]}</td>
                <td className="muted">{r.why[lang]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>{t.pests}</h2>
        <p className="pr-muted">{t.pestNote}</p>
        <table>
          <thead>
            <tr>
              <th>{t.pest}</th>
              <th>{t.level}</th>
              <th>{t.reason}</th>
            </tr>
          </thead>
          <tbody>
            {a.pest.map((p) => (
              <tr key={p.id}>
                <td>{p.name[lang]}</td>
                <td>
                  <span className={`pr-pill lv-${p.level}`}>{t.levels[p.level]}</span>
                </td>
                <td className="muted">
                  {tr(p.reason, lang)}
                  {p.action ? ` · ${p.action[lang]}` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>{t.water}</h2>
        {a.water_sources.length === 0 ? (
          <p className="pr-muted">{t.noWater}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t.name}</th>
                <th>{t.kind}</th>
                <th>{t.dist}</th>
              </tr>
            </thead>
            <tbody>
              {a.water_sources.slice(0, 8).map((w) => (
                <tr key={w.osm_id}>
                  <td>{w.name || "–"}</td>
                  <td>{w.kind}</td>
                  <td className="num">{w.distance_m < 1000 ? `${w.distance_m} m` : `${(w.distance_m / 1000).toFixed(1)} km`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>{t.sources}</h2>
        <table className="pr-sources">
          <tbody>
            {a.sources.map((x, i) => (
              <tr key={i}>
                <td>{x.name}</td>
                <td className="num">{x.captured_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {a.unavailable.length > 0 && (
          <p className="pr-muted">
            <b>{t.unavailable}:</b> {a.unavailable.map((u) => `${u.name} (${u.reason})`).join("; ")}
          </p>
        )}
        <p className="pr-muted">
          <b>{t.method}:</b> FAO-56 paddy water balance (TAW {wb.params.taw_mm} mm, RAW {wb.params.raw_mm} mm) · {tr(wb.rain_basis, lang)} · {tr(a.crop.basis, lang)}
        </p>
      </section>

      <footer className="pr-foot">
        <p className="pr-disclaimer">{tr(a.disclaimer, lang)}</p>
        <div className="pr-sign">
          <span>{t.sign}</span>
          <span className="line" />
        </div>
      </footer>
    </article>
  );
}
