import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Polygon, WaterFeature } from "../lib/api";

export const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    imagery: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      maxzoom: 19,
      attribution: "Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    },
    s2cloudless: {
      type: "raster",
      tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2023_3857/default/g/{z}/{y}/{x}.jpg"],
      tileSize: 256,
      maxzoom: 16,
      attribution: "Sentinel-2 cloudless 2023 by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2023), CC BY-NC-SA 4.0",
    },
    labels: {
      type: "raster",
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
      tileSize: 256,
      maxzoom: 19,
    },
  },
  layers: [
    { id: "imagery", type: "raster", source: "imagery", paint: { "raster-saturation": -0.12, "raster-contrast": 0.05 } },
    { id: "s2cloudless", type: "raster", source: "s2cloudless", layout: { visibility: "none" } },
    { id: "labels", type: "raster", source: "labels", paint: { "raster-opacity": 0.85 } },
  ],
};

const empty: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export type MapProps = {
  field: Polygon | null;
  drawing: boolean;
  draft: [number, number][];
  onAddPoint: (p: [number, number]) => void;
  onFinish: () => void;
  water: WaterFeature[];
  routeTo: WaterFeature | null;
  fieldColor: string;
  fieldLabel: string;
  focus: [number, number] | null;
  basemap: "esri" | "s2";
  onSnapshot?: (fn: () => string | null) => void;
};

export function FieldMap(p: MapProps) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const loaded = useRef(false);
  const latest = useRef(p);
  latest.current = p;

  useEffect(() => {
    if (!el.current) return;
    const m = new maplibregl.Map({
      container: el.current,
      style: STYLE,
      center: [105.3356, -5.0998],
      zoom: 14.5,
      attributionControl: { compact: true },
      cooperativeGestures: false,
      // Needed to copy the map into the printed report.
      canvasContextAttributes: { preserveDrawingBuffer: true },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    m.on("load", () => {
      m.addSource("water", { type: "geojson", data: empty });
      m.addSource("field", { type: "geojson", data: empty });
      m.addSource("draft", { type: "geojson", data: empty });
      m.addSource("route", { type: "geojson", data: empty });
      m.addLayer({
        id: "water-area",
        type: "fill",
        source: "water",
        filter: ["==", ["geometry-type"], "Polygon"],
        paint: { "fill-color": "#3aa6d8", "fill-opacity": 0.45 },
      });
      // line-dasharray cannot be data-driven, so seasonal channels get their own dashed layer.
      const waterPaint = {
        "line-color": ["match", ["get", "kind"], "river", "#2f8fd0", "canal", "#21b3c4", "#6cc4e6"],
        "line-width": ["match", ["get", "kind"], "river", 4, "canal", 3, 2],
      } as maplibregl.LineLayerSpecification["paint"];
      m.addLayer({
        id: "water-line",
        type: "line",
        source: "water",
        filter: ["all", ["==", ["geometry-type"], "LineString"], ["!", ["get", "intermittent"]]],
        paint: waterPaint,
      });
      m.addLayer({
        id: "water-line-seasonal",
        type: "line",
        source: "water",
        filter: ["all", ["==", ["geometry-type"], "LineString"], ["get", "intermittent"]],
        paint: { ...waterPaint, "line-dasharray": [2, 2] },
      });
      m.addLayer({
        id: "water-point",
        type: "circle",
        source: "water",
        filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 6, "circle-color": "#21b3c4", "circle-stroke-color": "#fff", "circle-stroke-width": 2 },
      });
      m.addLayer({ id: "field-fill", type: "fill", source: "field", paint: { "fill-color": "#7fa35b", "fill-opacity": 0.38 } });
      m.addLayer({
        id: "field-line",
        type: "line",
        source: "field",
        paint: { "line-color": "#f3e6c4", "line-width": 3, "line-dasharray": [2, 1.2] },
      });
      m.addLayer({
        id: "route",
        type: "line",
        source: "route",
        paint: { "line-color": "#f3e6c4", "line-width": 2.5, "line-dasharray": [1, 1.5] },
      });
      m.addLayer({
        id: "draft-line",
        type: "line",
        source: "draft",
        paint: { "line-color": "#e2a93b", "line-width": 3 },
      });
      m.addLayer({
        id: "draft-pts",
        type: "circle",
        source: "draft",
        filter: ["==", ["geometry-type"], "Point"],
        paint: { "circle-radius": 6, "circle-color": "#e2a93b", "circle-stroke-color": "#fff", "circle-stroke-width": 2 },
      });
      loaded.current = true;
      sync();
    });
    m.on("click", (e) => {
      if (latest.current.drawing) latest.current.onAddPoint([e.lngLat.lng, e.lngLat.lat]);
    });
    m.on("dblclick", (e) => {
      if (latest.current.drawing) {
        e.preventDefault();
        latest.current.onFinish();
      }
    });
    map.current = m;
    p.onSnapshot?.(() => {
      try {
        return m.getCanvas().toDataURL("image/jpeg", 0.88);
      } catch {
        // Tiles from a server without CORS taint the canvas; the report then shows coordinates instead.
        return null;
      }
    });
    return () => m.remove();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function sync() {
    const m = map.current;
    if (!m || !loaded.current) return;
    const s = latest.current;
    (m.getSource("field") as GeoJSONSource).setData(
      s.field ? { type: "Feature", properties: { label: s.fieldLabel }, geometry: s.field } : empty,
    );
    m.setPaintProperty("field-fill", "fill-color", s.fieldColor);
    const draftFeats: GeoJSON.Feature[] = s.draft.map((c) => ({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: c } }));
    if (s.draft.length > 1)
      draftFeats.push({ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [...s.draft, s.draft[0]] } });
    (m.getSource("draft") as GeoJSONSource).setData({ type: "FeatureCollection", features: draftFeats });
    (m.getSource("water") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features: s.water.map((w) => {
        const closed = w.geometry.length > 3 && w.geometry[0][0] === w.geometry.at(-1)![0] && w.geometry[0][1] === w.geometry.at(-1)![1];
        const geometry: GeoJSON.Geometry =
          w.geometry.length === 1
            ? { type: "Point", coordinates: w.geometry[0] }
            : closed
              ? { type: "Polygon", coordinates: [w.geometry] }
              : { type: "LineString", coordinates: w.geometry };
        return { type: "Feature", properties: { kind: w.kind, name: w.name, intermittent: w.intermittent }, geometry };
      }),
    });
    const c = s.field ? centroid(s.field) : null;
    (m.getSource("route") as GeoJSONSource).setData(
      c && s.routeTo ? { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [c, s.routeTo.nearest_point] } } : empty,
    );
    m.getCanvas().style.cursor = s.drawing ? "crosshair" : "";
    if (s.drawing) m.doubleClickZoom.disable();
    else m.doubleClickZoom.enable();
  }

  useEffect(sync, [p.field, p.draft, p.water, p.routeTo, p.fieldColor, p.drawing, p.fieldLabel]);

  useEffect(() => {
    const m = map.current;
    if (!m || !p.field) return;
    const xs = p.field.coordinates[0].map((c) => c[0]);
    const ys = p.field.coordinates[0].map((c) => c[1]);
    m.fitBounds(
      [
        [Math.min(...xs), Math.min(...ys)],
        [Math.max(...xs), Math.max(...ys)],
      ],
      { padding: { top: 80, bottom: 140, left: 60, right: window.innerWidth > 900 ? 520 : 60 }, maxZoom: 16.5, duration: 900 },
    );
  }, [p.field]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => m.setLayoutProperty("s2cloudless", "visibility", p.basemap === "s2" ? "visible" : "none");
    if (m.isStyleLoaded()) apply();
    else m.once("load", apply);
  }, [p.basemap]);

  useEffect(() => {
    if (p.focus && map.current) map.current.flyTo({ center: p.focus, zoom: 15.5, duration: 800 });
  }, [p.focus]);

  return <div ref={el} className="field-map" role="application" aria-label="Peta lahan / field map" />;
}

export function centroid(poly: Polygon): [number, number] {
  const ring = poly.coordinates[0].slice(0, -1);
  const x = ring.reduce((a, c) => a + c[0], 0) / ring.length;
  const y = ring.reduce((a, c) => a + c[1], 0) / ring.length;
  return [x, y];
}
