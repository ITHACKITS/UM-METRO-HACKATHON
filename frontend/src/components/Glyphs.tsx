/* Simple hazard glyphs shared by the landing page and the app. */
export function IslandGlyph({ kind }: { kind: string }) {
  const common = { width: 44, height: 44, viewBox: "0 0 44 44", fill: "none", "aria-hidden": true } as const;
  if (kind === "drought")
    return (
      <svg {...common}>
        <circle cx="22" cy="17" r="7" fill="hsl(39 74% 56%)" />
        <path d="M8 33h28M12 38l4-5 3 3 4-4 3 3 4-4" stroke="hsl(28 80% 46%)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (kind === "flood")
    return (
      <svg {...common}>
        <path d="M22 6s-9 10-9 16a9 9 0 0 0 18 0c0-6-9-16-9-16Z" fill="hsl(205 70% 40%)" />
        <path d="M6 36c4-3 6 3 10 0s6 3 10 0 6 3 12 0" stroke="hsl(205 70% 40%)" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
    );
  if (kind === "pest")
    return (
      <svg {...common}>
        <ellipse cx="22" cy="24" rx="6" ry="9" fill="hsl(100 30% 32%)" />
        <path d="M16 18l-6-4M28 18l6-4M16 26h-7M28 26h7M17 31l-5 4M27 31l5 4M19 14l-2-5M25 14l2-5" stroke="hsl(150 18% 13%)" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg {...common}>
      <rect x="6" y="9" width="28" height="20" rx="10" fill="hsl(183 66% 32%)" />
      <path d="M14 29l-3 7 9-7" fill="hsl(183 66% 32%)" />
      <circle cx="15" cy="19" r="2" fill="hsl(44 66% 86%)" />
      <circle cx="21" cy="19" r="2" fill="hsl(44 66% 86%)" />
      <circle cx="27" cy="19" r="2" fill="hsl(44 66% 86%)" />
    </svg>
  );
}
