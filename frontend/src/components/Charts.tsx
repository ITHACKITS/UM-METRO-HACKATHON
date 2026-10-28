import { useId } from "react";

type Pad = { t: number; r: number; b: number; l: number };
const PAD: Pad = { t: 12, r: 12, b: 26, l: 40 };

function scale(d0: number, d1: number, r0: number, r1: number) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v: number) => r0 + (v - d0) * k;
}

function ticks(min: number, max: number, n = 4) {
  const span = max - min || 1;
  const step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const err = span / n / step;
  const s = step * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
  const out: number[] = [];
  for (let v = Math.ceil(min / s) * s; v <= max + 1e-9; v += s) out.push(+v.toFixed(6));
  return out;
}

const shortDate = (d: string) => {
  const [, m, day] = d.split("-");
  return `${+day}/${+m}`;
};

export function FanChart({
  dates,
  p5,
  p50,
  p95,
  unit,
  label,
  color = "hsl(var(--teal))",
  line,
  lineLabel,
  day,
  yMin,
  yMax,
  extendedFrom,
}: {
  dates: string[];
  p5: number[];
  p50: number[];
  p95: number[];
  unit: string;
  label: string;
  color?: string;
  line?: number[] | number;
  lineLabel?: string;
  day?: number;
  yMin?: number;
  yMax?: number;
  extendedFrom?: number;
}) {
  const id = useId();
  const W = 420,
    H = 180;
  const n = p50.length;
  const lineArr = typeof line === "number" ? new Array(n).fill(line) : line;
  const lo = yMin ?? Math.min(0, ...p5);
  // A reference line (e.g. plant height) must not flatten the data: scale to the data first.
  const hi = yMax ?? Math.max(Math.max(...p95) * 1.25, lineArr ? Math.min(Math.max(...lineArr) * 1.08, Math.max(...p95) * 4 + 50) : 0, 1) + 1e-6;
  const x = scale(0, Math.max(1, n - 1), PAD.l, W - PAD.r);
  const y = scale(lo, hi, H - PAD.b, PAD.t);
  const band =
    p95.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("") +
    p5
      .map((_, j) => {
        const i = n - 1 - j;
        return `L${x(i).toFixed(1)},${y(p5[i]).toFixed(1)}`;
      })
      .join("") +
    "Z";
  const med = p50.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const every = Math.ceil(n / 6);
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{label}</title>
        {ticks(lo, hi).map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="tick">
              {v}
            </text>
          </g>
        ))}
        {extendedFrom !== undefined && extendedFrom < n && (
          <rect x={x(extendedFrom)} y={PAD.t} width={W - PAD.r - x(extendedFrom)} height={H - PAD.b - PAD.t} className="clim-zone" />
        )}
        <defs>
          <clipPath id={`${id}-clip`}>
            <rect x={PAD.l} y={PAD.t} width={W - PAD.l - PAD.r} height={H - PAD.b - PAD.t} />
          </clipPath>
        </defs>
        <g clipPath={`url(#${id}-clip)`}>
        <path d={band} fill={color} opacity={0.18} />
        <path d={med} fill="none" stroke={color} strokeWidth={2.4} strokeLinejoin="round" />
        {lineArr && (
          <path
            d={lineArr.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join("")}
            fill="none"
            stroke="hsl(var(--ink) / 0.55)"
            strokeDasharray="4 4"
            strokeWidth={1.4}
          />
        )}
        </g>
        {day !== undefined && day < n && (
          <g>
            <line x1={x(day)} x2={x(day)} y1={PAD.t} y2={H - PAD.b} stroke="hsl(var(--ink))" strokeWidth={1.2} />
            <circle cx={x(day)} cy={y(p50[day])} r={4} fill={color} stroke="white" strokeWidth={1.5} />
          </g>
        )}
        {dates.map((d, i) =>
          i % every === 0 ? (
            <text key={d} x={x(i)} y={H - 8} textAnchor="middle" className="tick">
              {shortDate(d)}
            </text>
          ) : null,
        )}
        <text x={PAD.l} y={PAD.t - 2} className="unit">
          {unit}
        </text>
      </svg>
      <figcaption>
        <span className="key band" style={{ background: color }} /> P5-P95 <span className="key med" style={{ background: color }} /> P50
        {lineArr && lineLabel && (
          <>
            <span className="key dash" /> {lineLabel}
          </>
        )}
        {extendedFrom !== undefined && extendedFrom < n && (
          <>
            <span className="key clim" /> {label.includes("·") ? label.split("·")[1] : "climatology"}
          </>
        )}
      </figcaption>
    </figure>
  );
}

export function ProbBars({ dates, values, color, label, day }: { dates: string[]; values: number[]; color: string; label: string; day?: number }) {
  const W = 420,
    H = 110;
  const n = values.length;
  const bw = (W - PAD.l - PAD.r) / Math.max(1, n);
  const y = scale(0, 1, H - PAD.b, PAD.t);
  const every = Math.ceil(n / 6);
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="tick">
              {v * 100}%
            </text>
          </g>
        ))}
        {values.map((v, i) => (
          <rect
            key={i}
            x={PAD.l + i * bw + 1}
            y={y(v)}
            width={Math.max(1, bw - 2)}
            height={Math.max(0, H - PAD.b - y(v))}
            rx={2}
            fill={color}
            opacity={day === i ? 1 : 0.65}
          />
        ))}
        {dates.map((d, i) =>
          i % every === 0 ? (
            <text key={d} x={PAD.l + i * bw + bw / 2} y={H - 8} textAnchor="middle" className="tick">
              {shortDate(d)}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption>{label}</figcaption>
    </figure>
  );
}

export function SeriesChart({
  points,
  label,
}: {
  points: { date: string; field?: number; neighbours?: number }[];
  label: string;
}) {
  const W = 420,
    H = 170;
  if (!points.length) return null;
  const t0 = Date.parse(points[0].date),
    t1 = Date.parse(points[points.length - 1].date);
  const x = scale(t0, t1, PAD.l, W - PAD.r);
  const y = scale(0, 1, H - PAD.b, PAD.t);
  const path = (k: "field" | "neighbours") =>
    points
      .filter((p) => p[k] !== undefined)
      .map((p, i) => `${i ? "L" : "M"}${x(Date.parse(p.date)).toFixed(1)},${y(p[k] as number).toFixed(1)}`)
      .join("");
  const every = Math.ceil(points.length / 5);
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="tick">
              {v}
            </text>
          </g>
        ))}
        <path d={path("neighbours")} fill="none" stroke="hsl(var(--ink) / 0.35)" strokeWidth={1.6} strokeDasharray="3 3" />
        <path d={path("field")} fill="none" stroke="hsl(var(--sage))" strokeWidth={2.4} />
        {points.map((p) =>
          p.field !== undefined ? <circle key={p.date} cx={x(Date.parse(p.date))} cy={y(p.field)} r={3.4} fill="hsl(var(--leaf))" /> : null,
        )}
        {points.map((p, i) =>
          i % every === 0 ? (
            <text key={`t${p.date}`} x={x(Date.parse(p.date))} y={H - 8} textAnchor="middle" className="tick">
              {shortDate(p.date)}
            </text>
          ) : null,
        )}
      </svg>
      <figcaption>
        <span className="key med" style={{ background: "hsl(var(--sage))" }} /> {label}
        <span className="key dash" /> ±650 m
      </figcaption>
    </figure>
  );
}
