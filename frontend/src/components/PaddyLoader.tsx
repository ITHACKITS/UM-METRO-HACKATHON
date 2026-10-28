/*
 * Loader: a block of paddy plots. With `done`/`total` each finished step floods its plots and rice sprouts
 * in them (real progress). Without them it loops, for waits whose length nobody can know in advance.
 */
export function PaddyLoader({ done, total, size = 168 }: { done?: number; total?: number; size?: number }) {
  const cells = 16;
  const looping = done === undefined || total === undefined;
  const filled = looping ? cells : Math.round((done / total) * cells);
  return (
    <svg className={`paddy-loader ${looping ? "looping" : ""}`} viewBox="0 0 168 168" width={size} height={size} aria-hidden="true">
      {Array.from({ length: cells }, (_, i) => {
        const x = 6 + (i % 4) * 40, y = 6 + Math.floor(i / 4) * 40;
        return (
          <g key={i} className={`plot ${i < filled ? "on" : ""}`} style={{ ["--d" as string]: `${(i % 4) * 60 + Math.floor(i / 4) * 40}ms` }}>
            <rect x={x} y={y} width="36" height="36" rx="6" className="soil" />
            <rect x={x + 3} y={y + 3} width="30" height="30" rx="4" className="water" />
            {[0, 1, 2].map((k) => (
              <path key={k} className="sprout" d={`M${x + 9 + k * 9} ${y + 28} q -2 -8 1 -14 M${x + 10 + k * 9} ${y + 22} q 4 -3 6 -8`} />
            ))}
          </g>
        );
      })}
    </svg>
  );
}
