import { Link } from "react-router-dom";
import { Logo } from "./Logo";

const ITEMS = [
  ["Copernicus Sentinel-2 L2A", "contains modified Copernicus Sentinel data, ESA; accessed via Element84 Earth Search on AWS Open Data"],
  ["Open-Meteo", "Forecast, Ensemble (ECMWF IFS), Historical (ERA5), Flood (GloFAS v4) and Elevation (Copernicus DEM GLO-90) APIs, CC BY 4.0"],
  ["OpenStreetMap", "© OpenStreetMap contributors, ODbL, via the Overpass API"],
  ["Esri World Imagery", "Esri, Maxar, Earthstar Geographics, and the GIS User Community"],
  ["Libraries", "React, Three.js, MapLibre GL JS, GSAP, Lenis, FastAPI, rasterio, shapely, numpy"],
  ["Mascot", "Si Padi, needle-felt mascot artwork supplied by the Jagapadi team"],
];

export default function Credits() {
  return (
    <main className="credits">
      <Link to="/" aria-label="Jagapadi">
        <Logo />
      </Link>
      <h1>Credits and data attribution</h1>
      <ul>
        {ITEMS.map(([k, v]) => (
          <li key={k}>
            <b>{k}</b>: {v}
          </li>
        ))}
      </ul>
      <p>Scientific estimation tool, not an official warning. For decisions follow BMKG, your extension officer (PPL) and BPBD.</p>
    </main>
  );
}
