// Mark drawn by scripts/brand_assets.py; rebuild the logo set there, not here.
export function LogoMark({ size = 32 }: { size?: number }) {
  return <img src="/logo/jagapadi-icon.svg" width={size} height={size} alt="" aria-hidden="true" />;
}

export function Logo({ size = 30 }: { size?: number }) {
  return (
    <span className="logo">
      <LogoMark size={size} />
      <span className="logo-word">jagapadi</span>
    </span>
  );
}
