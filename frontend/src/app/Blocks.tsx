import { useEffect, useState } from "react";
import { api, API_DOWN, type Decision, type LancarResult, type TaksirResult } from "../lib/api";
import { useLang } from "../lib/i18n";
import { toBlock, type WatchField } from "../lib/watchlist";

// Shared by the P3A dashboard tabs: block details, TUAI Lancar water turns, TUAI Taksir harvest estimate.

export const VARIETIES = ["ciherang", "inpari32", "inpari42", "ir64", "mekongga", "lainnya"];
const VARIETY_NAME: Record<string, string> = {
  ciherang: "Ciherang",
  inpari32: "Inpari 32",
  inpari42: "Inpari 42",
  ir64: "IR64",
  mekongga: "Mekongga",
  lainnya: "Lainnya / other",
};
export const SOILS: Record<string, { id: string; en: string }> = {
  "": { id: "Otomatis (SoilGrids)", en: "Automatic (SoilGrids)" },
  clay: { id: "Liat", en: "Clay" },
  clay_loam: { id: "Lempung berliat", en: "Clay loam" },
  silt_loam: { id: "Lempung berdebu", en: "Silt loam" },
  loam: { id: "Lempung", en: "Loam" },
  sandy_loam: { id: "Lempung berpasir", en: "Sandy loam" },
};
export const LANCAR_COLOR = { merah: "#c4571e", kuning: "#e2a93b", hijau: "#4f8a3a" } as const;
export const TAKSIR_COLOR = { di_bawah: "#c4571e", sekitar: "#e2a93b", di_atas: "#4f8a3a" } as const;

const T = {
  id: {
    planted: "Tanggal tanam (pindah tanam)",
    variety: "Varietas",
    soil: "Jenis tanah",
    save: "Simpan",
    missing: "Isi tanggal tanam di tab Status agar fase tumbuh tepat.",
    runL: "Hitung urutan giliran air",
    runT: "Taksir panen",
    running: "Menghitung… petak baru butuh sekitar satu menit.",
    color: { merah: "Merah", kuning: "Kuning", hijau: "Hijau" },
    flowering: "berbunga",
    checkField: "cek ke sawah",
    need: (mm: number, m3: number) => `butuh ${mm} mm (≈${m3.toLocaleString("id-ID")} m³) dalam 7 hari`,
    stress: (p: number) => `peluang stres air ${Math.round(p * 100)}%`,
    dat: (d: number | null) => (d === null ? "umur tidak diketahui" : `${d} hari setelah tanam`),
    skipped: "Tidak bisa dihitung",
    log: "Catatan keputusan P3A",
    season: "Musim",
    block: "Blok",
    decision: "Keputusan",
    outcome: "Hasil (boleh diisi nanti)",
    followed: "Sesuai urutan TUAI",
    record: "Catat",
    noLog: "Belum ada catatan untuk musim ini.",
    cls: { di_bawah: "Di bawah rata-rata", sekitar: "Sekitar rata-rata", di_atas: "Di atas rata-rata" },
    noClass: "Belum bisa dinilai",
    window: { "flowering-grainfill": "citra fase berbunga–pengisian bulir", "season-so-far": "sementara: citra musim ini sejauh ini", "latest-scenes": "citra terbaru (tanggal tanam kosong)" } as Record<string, string>,
    est: (e: { t_ha: number; low: number; high: number }) => `${e.t_ha} t/ha (rentang ${e.low}–${e.high})`,
    model: (m: NonNullable<TaksirResult["model"]>) => `Regresi linear dari ${m.n} catatan panen (${m.seasons.join(", ")}), galat ±${m.rmse_t_ha} t/ha, R² data latih ${m.r2_in_sample}.`,
    harvestT: "Catat hasil timbang panen",
    harvestB: (n: number, need: number, seasons: number) => `${n} catatan tersimpan. Angka ton/ha muncul setelah ${need} catatan dari ${seasons} musim.`,
    yield: "Hasil (ton gabah/ha)",
    saved: "Tersimpan.",
    apiDown: "Server TUAI tidak menjawab.",
  },
  en: {
    planted: "Transplanting date",
    variety: "Variety",
    soil: "Soil type",
    save: "Save",
    missing: "Fill in the transplanting date on the Status tab for an accurate growth stage.",
    runL: "Rank water turns",
    runT: "Estimate harvest",
    running: "Working… a new plot takes about a minute.",
    color: { merah: "Red", kuning: "Yellow", hijau: "Green" },
    flowering: "flowering",
    checkField: "check the field",
    need: (mm: number, m3: number) => `needs ${mm} mm (≈${m3.toLocaleString("en-GB")} m³) over 7 days`,
    stress: (p: number) => `chance of water stress ${Math.round(p * 100)}%`,
    dat: (d: number | null) => (d === null ? "age unknown" : `${d} days after transplanting`),
    skipped: "Could not be computed",
    log: "P3A decision log",
    season: "Season",
    block: "Block",
    decision: "Decision",
    outcome: "Outcome (can be filled later)",
    followed: "Followed the TUAI order",
    record: "Record",
    noLog: "No entries for this season yet.",
    cls: { di_bawah: "Below average", sekitar: "Around average", di_atas: "Above average" },
    noClass: "Cannot be rated yet",
    window: { "flowering-grainfill": "flowering to grain-filling scenes", "season-so-far": "provisional: this season's scenes so far", "latest-scenes": "latest scenes (no transplanting date)" } as Record<string, string>,
    est: (e: { t_ha: number; low: number; high: number }) => `${e.t_ha} t/ha (range ${e.low}–${e.high})`,
    model: (m: NonNullable<TaksirResult["model"]>) => `Linear regression on ${m.n} harvest records (${m.seasons.join(", ")}), error ±${m.rmse_t_ha} t/ha, training R² ${m.r2_in_sample}.`,
    harvestT: "Record a weighed harvest",
    harvestB: (n: number, need: number, seasons: number) => `${n} records stored. Tonnes per hectare appear after ${need} records from ${seasons} seasons.`,
    yield: "Yield (t grain/ha)",
    saved: "Saved.",
    apiDown: "The TUAI server is not responding.",
  },
};

const errText = (e: unknown, s: { apiDown: string }) => ((e as Error).message === API_DOWN ? s.apiDown : (e as Error).message);
// Rainy-season planting (MT1) runs about November to March in Lampung, the dry season (MT2) April to October.
const season0 = () => {
  const d = new Date();
  const m = d.getMonth();
  if (m >= 3 && m <= 9) return `MT2 ${d.getFullYear()}`;
  const start = m >= 10 ? d.getFullYear() : d.getFullYear() - 1;
  return `MT1 ${start}/${String(start + 1).slice(2)}`;
};

export function BlockForm({ f, onSave }: { f: WatchField; onSave: (p: Partial<WatchField>) => void }) {
  const { lang } = useLang();
  const s = T[lang];
  const [date, setDate] = useState(f.planting_date ?? "");
  const [variety, setVariety] = useState(f.variety ?? "ciherang");
  const [soil, setSoil] = useState(f.soil ?? "");
  return (
    <form
      className="blk-form"
      onSubmit={(e) => {
        e.preventDefault();
        const dat = date ? Math.round((Date.now() - new Date(date).getTime()) / 86_400_000) : f.dat ?? null;
        onSave({ planting_date: date || null, variety, soil: soil || null, dat });
      }}
    >
      <label>
        <span className="tiny muted">{s.planted}</span>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      <label>
        <span className="tiny muted">{s.variety}</span>
        <select value={variety} onChange={(e) => setVariety(e.target.value)}>
          {VARIETIES.map((v) => (
            <option key={v} value={v}>
              {VARIETY_NAME[v]}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="tiny muted">{s.soil}</span>
        <select value={soil} onChange={(e) => setSoil(e.target.value)}>
          {Object.entries(SOILS).map(([k, v]) => (
            <option key={k} value={k}>
              {v[lang]}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="btn btn-primary small">
        {s.save}
      </button>
    </form>
  );
}

export function LancarPanel({ fields, onColors }: { fields: WatchField[]; onColors: (c: Record<string, string>) => void }) {
  const { lang } = useLang();
  const s = T[lang];
  const [res, setRes] = useState<LancarResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.lancar(fields.map(toBlock));
      setRes(r);
      onColors(Object.fromEntries(r.order.map((o) => [o.id, LANCAR_COLOR[o.color]])));
    } catch (e) {
      setError(errText(e, s));
    } finally {
      setBusy(false);
    }
  };
  const missing = fields.some((f) => !f.planting_date);

  return (
    <>
      {missing && <p className="small warn-flag sg-flag">{s.missing}</p>}
      <button type="button" className="btn btn-primary small" onClick={run} disabled={busy || !fields.length}>
        {s.runL}
      </button>
      {busy && <p className="small muted">{s.running}</p>}
      {error && <p className="error felt">{error}</p>}
      {res && (
        <>
          <p className="tiny muted">{res.rule[lang]}</p>
          <ol className="off-list">
            {res.order.map((o) => (
              <li key={o.id} className="felt off-row" style={{ ["--st" as string]: LANCAR_COLOR[o.color] }}>
                <div className="off-row-top">
                  <span className="lc-rank tabular">{o.rank}</span>
                  <span className="off-badge">{s.color[o.color]}</span>
                  <h3>{o.name}</h3>
                  {o.flowering && <span className="chip-s">{s.flowering}</span>}
                  {o.check_field && <span className="chip-s">{s.checkField}</span>}
                </div>
                <p className="off-head-line">{s.need(o.need_mm_7d, o.need_m3_7d)}</p>
                <p className="tiny muted tabular">
                  {s.stress(o.prob_stress_7d)} · {s.dat(o.days_after_transplant)} · {o.area_ha} ha{o.soil ? ` · ${o.soil.name[lang]}` : ""}
                </p>
                <ul className="lc-why">
                  {o.reasons.map((r, i) => (
                    <li key={i} className="small">
                      {r[lang]}
                    </li>
                  ))}
                  {o.soil && <li className="tiny muted">{o.soil.basis[lang]}</li>}
                </ul>
              </li>
            ))}
          </ol>
          {res.skipped.length > 0 && (
            <p className="small muted">
              {s.skipped}: {res.skipped.map((x) => `${x.name ?? x.id} (${x.reason})`).join("; ")}
            </p>
          )}
        </>
      )}
      <DecisionLog fields={fields} />
    </>
  );
}

function DecisionLog({ fields }: { fields: WatchField[] }) {
  const { lang } = useLang();
  const s = T[lang];
  const [season, setSeason] = useState(season0);
  const [items, setItems] = useState<Decision[]>([]);
  const [block, setBlock] = useState(fields[0]?.id ?? "");
  const [text, setText] = useState("");
  const [outcome, setOutcome] = useState("");
  const [followed, setFollowed] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .decisions(season)
      .then((r) => setItems(r.decisions))
      .catch(() => setItems([]));
  }, [season]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const f = fields.find((x) => x.id === block);
    if (!f || !text.trim()) return;
    try {
      const d = await api.decide({
        season,
        block_id: f.id,
        block_name: f.name,
        date: new Date().toISOString().slice(0, 10),
        decision: text.trim(),
        outcome: outcome.trim(),
        followed_recommendation: followed,
        by: "Ketua P3A",
      });
      setItems((l) => [d, ...l]);
      setText("");
      setOutcome("");
    } catch (err) {
      setError(errText(err, s));
    }
  };

  return (
    <section className="felt pad lc-log">
      <h3>{s.log}</h3>
      <form className="blk-form" onSubmit={add}>
        <label>
          <span className="tiny muted">{s.season}</span>
          <input value={season} maxLength={30} onChange={(e) => setSeason(e.target.value)} />
        </label>
        <label>
          <span className="tiny muted">{s.block}</span>
          <select value={block} onChange={(e) => setBlock(e.target.value)}>
            {fields.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        <label className="wide">
          <span className="tiny muted">{s.decision}</span>
          <input value={text} maxLength={300} onChange={(e) => setText(e.target.value)} />
        </label>
        <label className="wide">
          <span className="tiny muted">{s.outcome}</span>
          <input value={outcome} maxLength={300} onChange={(e) => setOutcome(e.target.value)} />
        </label>
        <label className="check">
          <input type="checkbox" checked={followed} onChange={(e) => setFollowed(e.target.checked)} /> <span className="small">{s.followed}</span>
        </label>
        <button type="submit" className="btn btn-primary small" disabled={!text.trim()}>
          {s.record}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {items.length === 0 ? (
        <p className="small muted">{s.noLog}</p>
      ) : (
        <ul className="lc-why">
          {items.map((d, i) => (
            <li key={i} className="small">
              <b>{d.date}</b> · {d.block_name ?? d.block_id}: {d.decision}
              {d.outcome ? ` → ${d.outcome}` : ""}
              {d.followed_recommendation === false ? " (≠ TUAI)" : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function TaksirPanel({ fields, onColors }: { fields: WatchField[]; onColors: (c: Record<string, string>) => void }) {
  const { lang } = useLang();
  const s = T[lang];
  const [res, setRes] = useState<TaksirResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api.taksir(fields.map(toBlock));
      setRes(r);
      onColors(Object.fromEntries(r.blocks.filter((b) => b.class).map((b) => [b.id, TAKSIR_COLOR[b.class!]])));
    } catch (e) {
      setError(errText(e, s));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button type="button" className="btn btn-primary small" onClick={run} disabled={busy || !fields.length}>
        {s.runT}
      </button>
      {busy && <p className="small muted">{s.running}</p>}
      {error && <p className="error felt">{error}</p>}
      {res && (
        <>
          <p className="tiny muted">{res.note[lang]}</p>
          {res.model && <p className="small">{s.model(res.model)}</p>}
          <ol className="off-list">
            {res.blocks.map((b) => (
              <li key={b.id} className="felt off-row" style={{ ["--st" as string]: b.class ? TAKSIR_COLOR[b.class] : "#9aa39d" }}>
                <div className="off-row-top">
                  <span className="off-badge">{b.class ? s.cls[b.class] : s.noClass}</span>
                  <h3>{b.name}</h3>
                </div>
                {b.estimate && <p className="off-head-line">{s.est(b.estimate)}</p>}
                <p className="small">{b.class_reason[lang]}</p>
                <p className="tiny muted">
                  {s.window[b.features.window] ?? b.features.window} · {b.features.scenes} citra · {b.area_ha} ha
                </p>
              </li>
            ))}
          </ol>
        </>
      )}
      <HarvestForm fields={fields} stored={res?.harvest_records} needs={res?.needs} />
    </>
  );
}

function HarvestForm({ fields, stored, needs }: { fields: WatchField[]; stored?: number; needs?: { records: number; seasons: number } }) {
  const { lang } = useLang();
  const s = T[lang];
  const [block, setBlock] = useState(fields[0]?.id ?? "");
  const [season, setSeason] = useState(season0);
  const [y, setY] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const f = fields.find((x) => x.id === block);
    const v = Number(y.replace(",", "."));
    if (!f || !(v >= 0 && v <= 20)) return;
    try {
      await api.harvest(toBlock(f), season, v);
      setMsg(s.saved);
      setY("");
    } catch (err) {
      setMsg(errText(err, s));
    }
  };
  return (
    <section className="felt pad lc-log">
      <h3>{s.harvestT}</h3>
      {stored !== undefined && needs && <p className="tiny muted">{s.harvestB(stored, needs.records, needs.seasons)}</p>}
      <form className="blk-form" onSubmit={add}>
        <label>
          <span className="tiny muted">{s.block}</span>
          <select value={block} onChange={(e) => setBlock(e.target.value)}>
            {fields.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="tiny muted">{s.season}</span>
          <input value={season} maxLength={30} onChange={(e) => setSeason(e.target.value)} />
        </label>
        <label>
          <span className="tiny muted">{s.yield}</span>
          <input value={y} inputMode="decimal" onChange={(e) => (setY(e.target.value), setMsg(null))} />
        </label>
        <button type="submit" className="btn btn-primary small" disabled={!y}>
          {s.record}
        </button>
      </form>
      {msg && <p className="small">{msg}</p>}
    </section>
  );
}
