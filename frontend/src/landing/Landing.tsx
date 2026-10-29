import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { LangToggle, useLang, type Key } from "../lib/i18n";
import { Logo } from "../components/Logo";
import type { DioramaHandle, View, WaterMode } from "./Diorama";
import { IslandGlyph } from "../components/Glyphs";
import { PaddyLoader } from "../components/PaddyLoader";
import "./landing.css";

const ISLANDS = [
  { key: "drought", t: "f_drought_t", b: "f_drought_b", n: "01" },
  { key: "flood", t: "f_flood_t", b: "f_flood_b", n: "02" },
  { key: "pest", t: "f_pest_t", b: "f_pest_b", n: "03" },
  { key: "chat", t: "f_chat_t", b: "f_chat_b", n: "04" },
] as const;

const STATS = [
  { v: "2,29%", vEn: "2.29%", k: "stat1", src: "https://ekonomi.bisnis.com/read/20240301/99/1745543/bps-luas-panen-padi-2023-merosot-229-sepanjang-2023", by: "BPS via Bisnis.com, 1 Mar 2024" },
  { v: "440 ribu", vEn: "440,000", k: "stat2", src: "https://nasional.kontan.co.id/news/produksi-beras-nasional-turun-440000-ton-pada-2023-bps-terdampak-el-nino", by: "BPS via Kontan, 2024" },
  { v: "102.746", vEn: "102,746", k: "stat3", src: "https://finance.detik.com/berita-ekonomi-bisnis/d-4616392/9-300-hektare-sawah-gagal-panen", by: "Kementan via detikFinance, 2019" },
] as const;

const STAGES: Key[] = ["stage_0", "stage_1", "stage_2", "stage_3"];
const fmtHour = (h: number) => `${String(Math.floor(h)).padStart(2, "0")}:${String(Math.round((h % 1) * 60)).padStart(2, "0")}`;

// The built diorama outlives the page: coming back to the landing re-attaches it instantly.
let cachedDiorama: { canvas: HTMLCanvasElement; handle: DioramaHandle } | null = null;
// Its fps callback must reach whichever Landing is mounted now.
let statsListener: (f: number) => void = () => {};

type Scene = { view: View; water?: WaterMode; stage?: number; hour?: number };

/* One framing per chapter. The diorama acts out what each chapter says. */
function storyScenes(narrow: boolean): Scene[] {
  const s = (x: number, y: number) => (narrow ? { sx: 0, sy: y } : { sx: x, sy: 0.02 });
  return [
    { view: { free: true, ...s(-0.17, -0.14) } },
    { view: { theta: 1.15, el: 0.6, dist: narrow ? 22 : 25, ty: -0.2, ...s(-0.2, 0.2) }, water: "kering", stage: 1.2, hour: 13 },
    { view: { theta: 0.62, el: 1.32, dist: narrow ? 25 : 30, ty: -0.3, ...s(0.2, 0.2) }, water: "normal", stage: 0.12, hour: 10 },
    { view: { theta: 0.25, el: 0.5, dist: narrow ? 28 : 31, ty: 0, ...(narrow ? { sx: 0, sy: 0.22 } : { sx: 0, sy: 0.2 }) }, water: "banjir", stage: 1.6, hour: 15 },
    { view: { theta: 1.3, el: 0.42, dist: narrow ? 26 : 28, ty: -0.2, ...s(0.2, 0.2) }, water: "normal", stage: 2.4, hour: 17.6 },
  ];
}

export default function Landing() {
  const { t, lang } = useLang();
  const stageRef = useRef<HTMLDivElement>(null);
  const storyRef = useRef<HTMLDivElement>(null);
  const handle = useRef<DioramaHandle | null>(null);
  const [ready, setReady] = useState(() => cachedDiorama !== null);
  const [webgl, setWebgl] = useState(true);
  const [prog, setProg] = useState({ done: 0, total: 8, label: "" });
  const [water, setWater] = useState<WaterMode>("normal");
  const [stage, setStage] = useState(1);
  const [hour, setHour] = useState(14);
  const [fps, setFps] = useState<number | null>(null);
  const [chapter, setChapter] = useState(0);
  const [coarse] = useState(() => window.matchMedia("(pointer: coarse)").matches);
  // Latest dock choices, restored whenever the story scrolls back to the hero.
  const userState = useRef({ water: "normal" as WaterMode, stage: 1, hour: 14 });

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Layout and camera follow the viewport width; a touch screen on a laptop is still a wide screen.
    const narrow = window.matchMedia("(max-width: 760px)").matches;
    let disposed = false;
    let cleanup: (() => void) | undefined;
    statsListener = setFps;

    const attach = (h: DioramaHandle) => {
      handle.current = h;
      h.setActive(true);
      setReady(true);
      const idle = (window as unknown as { requestIdleCallback?: (f: () => void) => void }).requestIdleCallback ?? ((f: () => void) => setTimeout(f, 1500));
      idle(() => void import("../app/Workspace"));
      const story = storyRef.current;
      // Depth layers follow the pointer and the whole story's scroll, so the parallax carries across chapters.
      let px = 0, py = 0, sp = 0, tx = 0, ty = 0, praf = 0;
      const onMove = (e: PointerEvent) => {
        tx = (e.clientX / window.innerWidth) * 2 - 1;
        ty = (e.clientY / window.innerHeight) * 2 - 1;
      };
      const tick = () => {
        const span = story ? Math.max(1, story.offsetHeight - window.innerHeight) : 1;
        const ts = Math.min(1, Math.max(0, window.scrollY / span));
        px += (tx - px) * 0.08;
        py += (ty - py) * 0.08;
        sp += (ts - sp) * 0.1;
        story?.style.setProperty("--px", px.toFixed(4));
        story?.style.setProperty("--py", py.toFixed(4));
        story?.style.setProperty("--sp", sp.toFixed(4));
        h.setPointer(px, -py);
        praf = requestAnimationFrame(tick);
      };
      if (!reduced) {
        if (window.matchMedia("(hover: hover)").matches) window.addEventListener("pointermove", onMove);
        praf = requestAnimationFrame(tick);
      }
      // Each chapter crossing the middle of the screen sets the scene.
      const scenes = storyScenes(narrow);
      const sections = [...document.querySelectorAll<HTMLElement>("[data-chapter]")];
      const chapterIo = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (!e.isIntersecting) continue;
            const i = Number((e.target as HTMLElement).dataset.chapter);
            setChapter(i);
            const sc = scenes[i];
            h.setView(sc.view);
            const u = userState.current;
            h.setWater(sc.water ?? u.water);
            h.setStage(sc.stage ?? (u.stage === 0 ? 0.05 : u.stage));
            h.setHour(sc.hour ?? u.hour);
          }
        },
        { rootMargin: "-50% 0px -50% 0px" },
      );
      sections.forEach((s) => chapterIo.observe(s));
      // Render only while the stage is on screen.
      const io = new IntersectionObserver(([e]) => h.setActive(e.isIntersecting), { threshold: 0.01 });
      if (story) io.observe(story);
      cleanup = () => {
        io.disconnect();
        chapterIo.disconnect();
        cancelAnimationFrame(praf);
        window.removeEventListener("pointermove", onMove);
        h.setActive(false);
      };
    };

    if (cachedDiorama && stageRef.current) {
      stageRef.current.appendChild(cachedDiorama.canvas);
      attach(cachedDiorama.handle);
    } else {
      import("./Diorama")
        .then(async ({ createDiorama }) => {
          if (!stageRef.current || disposed) return;
          const canvas = document.createElement("canvas");
          stageRef.current.appendChild(canvas);
          const h = await createDiorama(canvas, {
            mobile: narrow,
            reducedMotion: reduced,
            onProgress: (done, total, label) => setProg({ done, total, label }),
            onStats: (f) => statsListener(f),
          });
          if (!h) {
            canvas.remove();
            setWebgl(false);
            setReady(true);
            return;
          }
          cachedDiorama = { canvas, handle: h };
          if (disposed) {
            h.setActive(false);
            return;
          }
          attach(h);
        })
        .catch((err) => {
          // Shown as "no WebGL"; log the cause so a real failure is not mistaken for an old browser.
          console.error("Diorama failed to start", err);
          setWebgl(false);
          setReady(true);
        });
    }

    let revealCleanup: (() => void) | undefined;
    if (!reduced) {
      Promise.all([import("gsap"), import("gsap/ScrollTrigger")]).then(([{ gsap }, { ScrollTrigger }]) => {
        if (disposed) return;
        gsap.registerPlugin(ScrollTrigger);
        const tweens = gsap.utils.toArray<HTMLElement>("[data-reveal]").map((el) =>
          gsap.fromTo(
            el,
            { y: 36, opacity: 0, filter: "blur(8px)" },
            {
              y: 0,
              opacity: 1,
              filter: "blur(0px)",
              duration: 0.9,
              ease: "power3.out",
              delay: Number(el.dataset.reveal || 0) * 0.1,
              scrollTrigger: { trigger: el, start: "top 85%", once: true },
              clearProps: "filter,transform",
            },
          ),
        );
        revealCleanup = () => {
          tweens.forEach((tw) => tw.kill());
          ScrollTrigger.getAll().forEach((s) => s.kill());
        };
      });
    }
    return () => {
      disposed = true;
      statsListener = () => {};
      cleanup?.();
      revealCleanup?.();
    };
  }, []);

  const pickWater = (m: WaterMode) => {
    setWater(m);
    userState.current.water = m;
    handle.current?.setWater(m);
  };
  const cycleStage = () => {
    const s = (stage + 1) % 4;
    setStage(s);
    userState.current.stage = s;
    handle.current?.setStage(s === 0 ? 0.05 : s);
  };
  const pickHour = (h: number) => {
    setHour(h);
    userState.current.hour = h;
    handle.current?.setHour(h);
  };
  const fullscreen = () => {
    const el = storyRef.current?.querySelector(".stage");
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else (el as HTMLElement).requestFullscreen?.();
  };
  const inHero = chapter === 0;

  return (
    <div className={`landing ${ready ? "is-ready" : ""} ${webgl ? "" : "no-webgl"}`}>
      <div className="grain" aria-hidden="true" />

      <header className="nav">
        <Link to="/" className="nav-logo" aria-label="Jagapadi">
          <Logo />
        </Link>
        <nav className="nav-links" aria-label="Utama">
          <a href="#masalah">{t("problem_eyebrow")}</a>
          <a href="#cara-kerja">{t("nav_how")}</a>
          <a href="#fitur">{t("nav_features")}</a>
          <a href="#data">{t("nav_data")}</a>
        </nav>
        <div className="nav-right">
          <span className="nav-loc">Metro, Lampung · 5°06′ S · 105°20′ E</span>
          <LangToggle />
          <Link to="/app" className="btn btn-primary nav-cta">
            {t("nav_open")}
          </Link>
        </div>
      </header>

      <div className="story" ref={storyRef}>
        {/* The stage stays pinned while the chapters scroll over it. */}
        <div className="stage">
          <TerraceContours />
          <div ref={stageRef} className={`diorama ${inHero ? "" : "is-story"}`} aria-label={t("hero_eyebrow")} role="img" />
          <RiceStalks />
          {!webgl && <p className="nowebgl felt">{t("nowebgl")}</p>}

          <div className={`loader ${ready ? "done" : ""}`} role="status" aria-live="polite" aria-hidden={ready}>
            <PaddyLoader done={prog.done} total={prog.total} />
            <div className="loader-copy">
              <p className="loader-title">{t("loader_title")}</p>
              <p className="loader-step">
                <span className="tabular">
                  {String(prog.done).padStart(2, "0")} / {String(prog.total).padStart(2, "0")}
                </span>{" "}
                {prog.label}
              </p>
              <p className="loader-note">{t("loader_note")}</p>
            </div>
            <img className="loader-mascot" src="/mascot/mascot-laptop-256.png" srcSet="/mascot/mascot-laptop-256@2x.png 2x" width={150} height={150} alt="" />
          </div>

          <p className="hero-caption" aria-hidden="true">
            {t("hero_caption")}
          </p>

          {webgl && (
            <div className={`dock enter ${inHero ? "" : "dock-away"}`} style={{ ["--i" as string]: 5 }} role="toolbar" aria-label="Diorama" aria-hidden={!inHero}>
              <button type="button" className="dock-icon" onClick={() => handle.current?.resetView()} aria-label={t("dock_reset")} title={t("dock_reset")} tabIndex={inHero ? 0 : -1}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M3.5 9a5.5 5.5 0 1 0 1.7-4M3 2.5v3.2h3.2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              <div className="dock-seg" role="group" aria-label="Air">
                {(["kering", "normal", "banjir"] as WaterMode[]).map((m) => (
                  <button key={m} type="button" aria-pressed={water === m} className={`w-${m}`} onClick={() => pickWater(m)} tabIndex={inHero ? 0 : -1}>
                    {t(`dock_${m}` as Key)}
                  </button>
                ))}
              </div>
              <button type="button" className="dock-stage" onClick={cycleStage} tabIndex={inHero ? 0 : -1}>
                <span className="dock-k">{t("dock_stage")}</span> {t(STAGES[stage])}
                <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
                  <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" />
                </svg>
              </button>
              <label className="dock-hour">
                <span className="dock-k">{t("dock_hour")}</span>
                <input type="range" min={6.5} max={18.5} step={0.25} value={hour} onChange={(e) => pickHour(+e.target.value)} aria-label={t("dock_hour")} tabIndex={inHero ? 0 : -1} />
                <span className="tabular">{fmtHour(hour)}</span>
              </label>
              <button type="button" className="dock-icon hide-sm" onClick={fullscreen} aria-label={t("dock_full")} title={t("dock_full")} tabIndex={inHero ? 0 : -1}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M3 7V3h4M15 7V3h-4M3 11v4h4M15 11v4h-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
                </svg>
              </button>
            </div>
          )}

          <div className="hero-foot">
            <span className="tabular">
              {String(chapter + 1).padStart(2, "0")} / 05 · {t(STAGES[stage])} · {fmtHour(hour)}
              {fps ? ` · ${fps} fps` : ""}
            </span>
            <span className={`hide-sm ${inHero ? "" : "fade-out"}`}>{coarse ? t("hint_touch") : t("hint_drag")}</span>
          </div>
        </div>

        <section className="chap chap-hero" data-chapter="0" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow enter" style={{ ["--i" as string]: 0 }}>
              {t("hero_eyebrow")}
            </p>
            <h1 id="hero-title" className="hero-title">
              <span className="enter line" style={{ ["--i" as string]: 1 }}>
                {t("hero_l1")}
              </span>
              <span className="enter line" style={{ ["--i" as string]: 2 }}>
                <em className="serif-accent">{t("hero_l2")}</em> {t("hero_l3")}
              </span>
            </h1>
            <p className="hero-sub enter" style={{ ["--i" as string]: 3 }}>
              {t("hero_sub")}
            </p>
            <div className="hero-ctas enter" style={{ ["--i" as string]: 4 }}>
              <Link to="/app" className="btn btn-primary">
                {t("hero_cta")}
                <span className="chip" aria-hidden="true">
                  <Arrow />
                </span>
              </Link>
              <a href="#cara-kerja" className="btn btn-ghost">
                {t("hero_cta2")}
              </a>
            </div>
          </div>
        </section>

        <section id="masalah" className="chap left" data-chapter="1" aria-labelledby="problem-title">
          <div className="felt chap-card" data-reveal="0">
            <p className="eyebrow">02 · {t("problem_eyebrow")}</p>
            <h2 id="problem-title" className="chapter-title">
              {t("problem_title_a")} <em className="serif-accent muted">{t("problem_title_b")}</em>
            </h2>
            <p className="chapter-body">{t("problem_body")}</p>
            <dl className="stats">
              {STATS.map((s) => (
                <div key={s.k} className="stat">
                  <dt>{lang === "id" ? s.v : s.vEn}</dt>
                  <dd>
                    {t(s.k)}
                    <a href={s.src} target="_blank" rel="noreferrer" className="cite">
                      {s.by}
                    </a>
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        <section id="cara-kerja" className="chap right" data-chapter="2" aria-labelledby="how-title">
          <div className="felt chap-card has-mascot" data-reveal="0">
            <img
              className="how-mascot"
              src="/mascot/mascot-laptop-256.png"
              srcSet="/mascot/mascot-laptop-512.png 2x"
              width={256}
              height={256}
              loading="lazy"
              alt=""
            />
            <p className="eyebrow">03 · {t("how_eyebrow")}</p>
            <h2 id="how-title" className="chapter-title">
              {t("how_title_a")} <em className="serif-accent muted">{t("how_title_b")}</em>
            </h2>
            <ol className="steps">
              {(["how1", "how2", "how3"] as const).map((k, i) => (
                <li key={k}>
                  <span className="step-n">0{i + 1}</span>
                  <div>
                    <h3>{t(`${k}_t` as Key)}</h3>
                    <p>{t(`${k}_b` as Key)}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="fitur" className="chap bottom" data-chapter="3" aria-labelledby="feat-title">
          <div className="chap-wide">
            <div className="felt chap-head" data-reveal="0">
              <p className="eyebrow">04 · {t("feat_eyebrow")}</p>
              <h2 id="feat-title" className="chapter-title">
                {t("feat_title_a")} <em className="serif-accent">{t("feat_title_b")}</em>
              </h2>
            </div>
            <div className="island-grid">
              {ISLANDS.map((f, i) => (
                <article key={f.key} className={`felt island-card isle-${f.key}`} data-reveal={i + 1}>
                  <span className="island-n">{f.n}</span>
                  <IslandGlyph kind={f.key} />
                  <h3>{t(f.t)}</h3>
                  <p>{t(f.b)}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="data" className="chap right" data-chapter="4" aria-labelledby="honest-title">
          <div className="felt chap-card" data-reveal="0">
            <p className="eyebrow">05 · {t("honest_eyebrow")}</p>
            <h2 id="honest-title" className="chapter-title">
              {t("honest_title_a")} <em className="serif-accent muted">{t("honest_title_b")}</em>
            </h2>
            <p className="chapter-body">{t("honest_body")}</p>
            <ul className="source-list">
              <li>
                <b>Sentinel-2 L2A</b> NDVI, NDWI · Copernicus / Element84 Earth Search
              </li>
              <li>
                <b>ECMWF IFS ensemble</b> 51 {lang === "id" ? "skenario hujan" : "rain scenarios"} · Open-Meteo
              </li>
              <li>
                <b>GloFAS v4</b> {lang === "id" ? "debit sungai" : "river discharge"} · Open-Meteo Flood API
              </li>
              <li>
                <b>Copernicus DEM GLO-90</b> {lang === "id" ? "ketinggian" : "elevation"} · <b>ERA5</b> {lang === "id" ? "iklim 10 tahun" : "10-year climate"}
              </li>
              <li>
                <b>OpenStreetMap</b> {lang === "id" ? "sungai, saluran, embung" : "rivers, canals, ponds"}
              </li>
            </ul>
            <p className="note">{t("honest_note")}</p>
          </div>
        </section>
      </div>

      <main>
        <section className="final" aria-labelledby="final-title">
          <img className="final-mascot" src="/mascot/mascot-waving-512.png" width={512} height={512} loading="lazy" alt="Si Padi melambaikan tangan" data-reveal="0" />
          <h2 id="final-title" className="final-title" data-reveal="1">
            {t("final_title_a")}
            <br />
            <em className="serif-accent">{t("final_title_b")}</em>
          </h2>
          <Link to="/app" className="btn btn-primary btn-lg" data-reveal="2">
            {t("final_cta")}
            <span className="chip" aria-hidden="true">
              <Arrow />
            </span>
          </Link>
        </section>
      </main>

      <footer className="footer">
        <Logo />
        <p>{t("footer_made")}</p>
        <p className="fine">
          {t("honest_note")} · <Link to="/credits">Credits</Link>
        </p>
      </footer>
    </div>
  );
}

/* Back layer: faint terrace contour lines on the paper, slowest in the parallax. */
function TerraceContours() {
  return (
    <svg className="layer-back" viewBox="0 0 1000 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
      {Array.from({ length: 9 }, (_, i) => {
        const rx = 120 + i * 62, ry = 70 + i * 38;
        const w = (k: number) => Math.sin(i * 1.7 + k) * (8 + i * 2);
        const d = `M ${640 - rx} ${380 + w(1)} C ${640 - rx} ${380 - ry + w(2)}, ${640 + rx} ${380 - ry + w(3)}, ${640 + rx} ${380 + w(4)} S ${640 - rx} ${380 + ry + w(5)}, ${640 - rx} ${380 + w(1)}`;
        return <path key={i} d={d} />;
      })}
    </svg>
  );
}

/* Front layer: out-of-focus rice stalks with golden panicles, fastest in the parallax. */
function Stalk({ x, h, bend }: { x: number; h: number; bend: number }) {
  const tipX = x + bend, tipY = 400 - h;
  const dir = Math.sign(bend || 1);
  return (
    <g>
      <path d={`M ${x} 400 Q ${x + bend * 0.2} ${400 - h * 0.6} ${tipX} ${tipY}`} className="stem" />
      <path d={`M ${x} 400 Q ${x - 30} ${400 - h * 0.45} ${x - 60} ${400 - h * 0.55}`} className="leaf" />
      <g className="grains">
        {Array.from({ length: 7 }, (_, i) => {
          const t = i / 6;
          const gx = tipX + t * 26 * dir, gy = tipY + t * t * 60;
          return <ellipse key={i} cx={gx} cy={gy} rx="5" ry="9" transform={`rotate(${(30 + t * 40) * dir} ${gx} ${gy})`} />;
        })}
      </g>
    </g>
  );
}

function RiceStalks() {
  return (
    <>
      <svg className="layer-front left" viewBox="0 0 220 400" aria-hidden="true">
        <Stalk x={70} h={300} bend={30} />
        <Stalk x={120} h={340} bend={40} />
        <Stalk x={160} h={260} bend={20} />
      </svg>
      <svg className="layer-front right" viewBox="0 0 220 400" aria-hidden="true">
        <Stalk x={60} h={280} bend={-30} />
        <Stalk x={110} h={330} bend={35} />
        <Stalk x={170} h={300} bend={25} />
      </svg>
    </>
  );
}

function Arrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
