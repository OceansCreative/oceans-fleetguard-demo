"use client";

import maplibregl from "maplibre-gl";
import { useEffect, useRef, useState } from "react";

import {
  MAP_AERIAL_URL,
  MAP_ATTRIBUTION,
  MAP_CENTER,
  MAP_STYLE_URL,
  MAP_STYLE_URL_DARK,
  MAP_ZOOM,
} from "@/lib/config";
import { highestSeverity } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { CALM_COLOR, SEVERITY_COLOR } from "@/components/severity";
import { useT } from "@/lib/i18n";
import type { MessageKey } from "@/lib/i18n";

import "maplibre-gl/dist/maplibre-gl.css";

const EMPTY: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

/** Vehicles moving above this speed (m/s) use the directional arrow marker. */
const MOVING_THRESHOLD_MPS = 0.5;

/** Duration of the position-tween animation in milliseconds. */
const TWEEN_DURATION_MS = 800;

type Theme = "light" | "dark";
type BasemapId = "light" | "dark" | "aerial";

const PALETTE: Record<Theme, Record<string, string>> = {
  light: {
    sea: "#a7cde4",
    land: "#f4f1ea",
    coastHalo: "#ffffff",
    coast: "#8aa6bb",
    railBed: "#c2c5d4",
    railLine: "#5c627a",
    stationFill: "#ffffff",
    stationStroke: "#5c627a",
  },
  dark: {
    sea: "#0e1622",
    land: "#1c2532",
    coastHalo: "#2b3a4d",
    coast: "#46586c",
    railBed: "#2b3543",
    railLine: "#6b7d93",
    stationFill: "#0e1622",
    stationStroke: "#7d90a6",
  },
};

// A self-contained vector style drawn from the bundled GeoJSON, used when no
// remote style is configured. No glyphs are referenced (place names are HTML
// markers), so it needs no fonts and works fully offline. Cartographic
// conventions — soft sea, a haloed coastline, railway hatching — make the
// limited offline data read as a deliberately designed map.
function offlineStyle(theme: Theme): maplibregl.StyleSpecification {
  const c = PALETTE[theme];
  return {
    version: 8,
    sources: {
      land: { type: "geojson", data: "/basemap.geojson" },
      rail: { type: "geojson", data: "/rail.geojson" },
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": c.sea } },
      {
        id: "land",
        type: "fill",
        source: "land",
        paint: { "fill-color": c.land },
      },
      {
        id: "coast-halo",
        type: "line",
        source: "land",
        paint: {
          "line-color": c.coastHalo,
          "line-width": 3.5,
          "line-blur": 1.5,
        },
      },
      {
        id: "coast",
        type: "line",
        source: "land",
        paint: { "line-color": c.coast, "line-width": 1.1 },
      },
      {
        id: "rail-bed",
        type: "line",
        source: "rail",
        filter: ["==", ["get", "kind"], "rail"],
        layout: { "line-cap": "round" },
        paint: { "line-color": c.railBed, "line-width": 3 },
      },
      {
        id: "rail-line",
        type: "line",
        source: "rail",
        filter: ["==", ["get", "kind"], "rail"],
        paint: {
          "line-color": c.railLine,
          "line-width": 1.3,
          "line-dasharray": [2, 2.5],
        },
      },
      {
        id: "stations",
        type: "circle",
        source: "rail",
        filter: ["==", ["get", "kind"], "station"],
        paint: {
          "circle-radius": 2.2,
          "circle-color": c.stationFill,
          "circle-stroke-color": c.stationStroke,
          "circle-stroke-width": 1.1,
        },
      },
    ],
  };
}

// Resolve a basemap choice to a MapLibre style: a remote URL when configured,
// otherwise the bundled offline style. Aerial has no offline equivalent.
function resolveStyle(id: BasemapId): maplibregl.StyleSpecification | string {
  if (id === "aerial") return MAP_AERIAL_URL ?? offlineStyle("dark");
  if (id === "dark") return MAP_STYLE_URL_DARK ?? offlineStyle("dark");
  return MAP_STYLE_URL ?? offlineStyle("light");
}

// Whether a basemap renders from the bundled offline GeoJSON (so we draw our
// own labels) and, if so, with which label theme.
function offlineTheme(id: BasemapId): Theme | null {
  if (id === "light" && MAP_STYLE_URL === null) return "light";
  if (id === "dark" && MAP_STYLE_URL_DARK === null) return "dark";
  return null;
}

const BASEMAP_CONFIGS: { id: BasemapId; labelKey: MessageKey }[] = [
  { id: "light", labelKey: "map.light" },
  { id: "dark", labelKey: "map.dark" },
  { id: "aerial", labelKey: "map.aerial" },
];

/** Approximate a metres-radius circle as a polygon (for the geofence). */
function circleFeature(
  lat: number,
  lon: number,
  radiusM: number,
  steps = 72,
): GeoJSON.Feature {
  const ring: [number, number][] = [];
  const earth = 6378137;
  const latRad = (lat * Math.PI) / 180;
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * 2 * Math.PI;
    const dLon =
      ((radiusM * Math.cos(a)) / (earth * Math.cos(latRad))) * (180 / Math.PI);
    const dLat = ((radiusM * Math.sin(a)) / earth) * (180 / Math.PI);
    ring.push([lon + dLon, lat + dLat]);
  }
  return {
    type: "Feature",
    geometry: { type: "Polygon", coordinates: [ring] },
    properties: {},
  };
}

/**
 * Build GeoJSON features for all vehicles, including the `moving` flag and
 * `course` property used by the directional arrow layer.
 */
function vehicleData(
  vehicles: Vehicle[],
  selectedId: string | null,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: vehicles.map((vehicle) => {
      const severity = highestSeverity(vehicle);
      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [vehicle.position.lon, vehicle.position.lat],
        },
        properties: {
          id: vehicle.id,
          color: severity === null ? CALM_COLOR : SEVERITY_COLOR[severity],
          selected: vehicle.id === selectedId,
          moving: vehicle.position.speed_mps > MOVING_THRESHOLD_MPS,
          course: vehicle.position.course_deg,
        },
      };
    }),
  };
}

function geofenceData(
  vehicles: Vehicle[],
  selectedId: string | null,
): GeoJSON.FeatureCollection {
  const selected = vehicles.find((vehicle) => vehicle.id === selectedId);
  const fence = selected?.geofence;
  if (!fence) return EMPTY;
  return {
    type: "FeatureCollection",
    features: [circleFeature(fence.lat, fence.lon, fence.radius_m)],
  };
}

// ---------------------------------------------------------------------------
// Arrow icon: a simple SDF chevron/arrow pointing up (north = 0°).
// Rendered as a 17×17 pixel canvas ImageData so MapLibre can tint it via the
// `icon-color` paint property when loaded as an SDF image.
// ---------------------------------------------------------------------------

/** Draw a filled upward-pointing arrow into a canvas and return its ImageData. */
function buildArrowImageData(size: number): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return new ImageData(size, size);
  }
  const half = size / 2;
  const tip = size * 0.1;
  const base = size * 0.88;
  const wingLeft = size * 0.15;
  const wingRight = size * 0.85;
  const notchY = size * 0.62;
  const notchDepth = size * 0.78;

  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(half, tip);
  ctx.lineTo(wingRight, base);
  ctx.lineTo(half, notchY);
  ctx.lineTo(wingLeft, base);
  ctx.lineTo(half, tip);
  ctx.fill();
  // Draw the notch by clearing the tail indent
  ctx.globalCompositeOperation = "destination-out";
  ctx.beginPath();
  ctx.moveTo(wingLeft, base);
  ctx.lineTo(half, notchDepth);
  ctx.lineTo(wingRight, base);
  ctx.lineTo(half, notchY);
  ctx.closePath();
  ctx.fill();

  return ctx.getImageData(0, 0, size, size);
}

// ---------------------------------------------------------------------------
// Position tween: smoothly interpolate each vehicle's lon/lat across frames.
// ---------------------------------------------------------------------------

interface TweenEntry {
  fromLon: number;
  fromLat: number;
  toLon: number;
  toLat: number;
  startTime: number;
  rafId: number;
}

/** Linear interpolation between two numbers. */
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Given a tween entry and the current time, return the interpolated [lon, lat].
 */
function tweenCoords(entry: TweenEntry, now: number): [number, number] {
  const elapsed = now - entry.startTime;
  const t = Math.min(elapsed / TWEEN_DURATION_MS, 1);
  // ease-out cubic
  const eased = 1 - Math.pow(1 - t, 3);
  return [
    lerp(entry.fromLon, entry.toLon, eased),
    lerp(entry.fromLat, entry.toLat, eased),
  ];
}

// ---------------------------------------------------------------------------
// Pulsing glow animation for the selected vehicle.
// ---------------------------------------------------------------------------

interface GlowState {
  rafId: number;
  phase: number;
}

/** Animate the vehicle-glow layer radius and opacity using requestAnimationFrame. */
function startGlowAnimation(map: maplibregl.Map, state: GlowState): void {
  const GLOW_MIN_RADIUS = 16;
  const GLOW_MAX_RADIUS = 26;
  const GLOW_MIN_OPACITY = 0.12;
  const GLOW_MAX_OPACITY = 0.26;
  const GLOW_PERIOD_MS = 1600;

  function tick(): void {
    state.phase = (state.phase + 1) % GLOW_PERIOD_MS;
    const t = (Math.sin((state.phase / GLOW_PERIOD_MS) * 2 * Math.PI) + 1) / 2;
    const radius = lerp(GLOW_MIN_RADIUS, GLOW_MAX_RADIUS, t);
    const opacity = lerp(GLOW_MIN_OPACITY, GLOW_MAX_OPACITY, t);
    if (map.getLayer("vehicle-glow")) {
      map.setPaintProperty("vehicle-glow", "circle-radius", radius);
      map.setPaintProperty("vehicle-glow", "circle-opacity", opacity);
    }
    state.rafId = requestAnimationFrame(tick);
  }

  state.rafId = requestAnimationFrame(tick);
}

/**
 * True when the user has asked the OS to minimise non-essential motion. The
 * position tween and the selected-vehicle glow pulse are disabled in that case
 * (positions snap; the glow stays static), matching the CSS reduced-motion
 * handling for the rest of the dashboard.
 */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function FleetMap({
  vehicles,
  selectedId,
  onSelect,
}: {
  vehicles: Vehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}): React.JSX.Element {
  const t = useT();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  const [basemap, setBasemap] = useState<BasemapId>("light");
  // Keep the latest props/selection reachable from the (stable) map callbacks.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const dataRef = useRef({ vehicles, selectedId });
  dataRef.current = { vehicles, selectedId };
  const basemapRef = useRef<BasemapId>("light");
  const pannedTo = useRef<string | null>(null);
  // Re-attach overlays after a runtime style change (set up by the init effect).
  const reattachRef = useRef<() => void>(() => {});

  // Per-vehicle active tweens (keyed by vehicle id).
  const tweensRef = useRef<Map<string, TweenEntry>>(new Map());
  // Previous known positions (keyed by vehicle id), used to start tweens.
  const prevPositionsRef = useRef<Map<string, [number, number]>>(new Map());
  // Glow animation state (one RAF loop while a vehicle is selected).
  const glowRef = useRef<GlowState | null>(null);

  useEffect(() => {
    if (container.current === null) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: resolveStyle("light"),
      center: [MAP_CENTER[1], MAP_CENTER[0]],
      zoom: MAP_ZOOM,
      attributionControl: false,
    });
    mapRef.current = map;
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-left",
    );
    map.addControl(
      new maplibregl.ScaleControl({ unit: "metric" }),
      "bottom-left",
    );
    map.addControl(
      new maplibregl.AttributionControl({ customAttribution: MAP_ATTRIBUTION }),
      "bottom-right",
    );

    let labelMarkers: maplibregl.Marker[] = [];
    const clearLabels = () => {
      for (const marker of labelMarkers) marker.remove();
      labelMarkers = [];
    };
    const addLabels = (theme: Theme) => {
      fetch("/labels.geojson")
        .then((response) => response.json())
        .then((collection: GeoJSON.FeatureCollection) => {
          const MAJOR = new Set(["Matsue", "Yonago", "Izumo", "Yasugi"]);
          for (const feature of collection.features) {
            if (feature.geometry.type !== "Point") continue;
            const kind = String(feature.properties?.kind ?? "city");
            const name = String(feature.properties?.name ?? "");
            const element = document.createElement("div");
            element.className =
              `map-label map-label--${kind} map-label--${theme}` +
              (MAJOR.has(name) ? " map-label--major" : "");
            element.textContent = name;
            labelMarkers.push(
              new maplibregl.Marker({ element })
                .setLngLat(feature.geometry.coordinates as [number, number])
                .addTo(map),
            );
          }
        })
        .catch(() => {
          /* labels are optional */
        });
    };

    // Register the SDF arrow icon for moving vehicles.
    const addArrowIcon = () => {
      if (!map.hasImage("vehicle-arrow")) {
        const imageData = buildArrowImageData(17);
        map.addImage("vehicle-arrow", imageData, { sdf: true });
      }
    };

    // (Re)add the live overlay sources/layers on top of whichever basemap just
    // loaded. Guarded so it is safe to call after every style change.
    const addOverlays = () => {
      addArrowIcon();

      if (!map.getSource("geofence")) {
        map.addSource("geofence", { type: "geojson", data: EMPTY });
      }
      if (!map.getLayer("geofence-fill")) {
        map.addLayer({
          id: "geofence-fill",
          type: "fill",
          source: "geofence",
          paint: { "fill-color": "#2f6fe0", "fill-opacity": 0.06 },
        });
      }
      if (!map.getLayer("geofence-line")) {
        map.addLayer({
          id: "geofence-line",
          type: "line",
          source: "geofence",
          paint: {
            "line-color": "#2f6fe0",
            "line-width": 1.4,
            "line-opacity": 0.8,
            "line-dasharray": [3, 2],
          },
        });
      }
      if (!map.getSource("vehicles")) {
        map.addSource("vehicles", { type: "geojson", data: EMPTY });
      }
      if (!map.getLayer("vehicle-glow")) {
        map.addLayer({
          id: "vehicle-glow",
          type: "circle",
          source: "vehicles",
          filter: ["==", ["get", "selected"], true],
          paint: {
            "circle-radius": 20,
            "circle-color": ["get", "color"],
            "circle-opacity": 0.18,
            "circle-blur": 1,
          },
        });
      }
      // Stationary vehicles: classic colored dot.
      if (!map.getLayer("vehicles-stationary")) {
        map.addLayer({
          id: "vehicles-stationary",
          type: "circle",
          source: "vehicles",
          filter: ["==", ["get", "moving"], false],
          paint: {
            "circle-radius": ["case", ["get", "selected"], 8, 5.5],
            "circle-color": ["get", "color"],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": ["case", ["get", "selected"], 3, 1.5],
          },
        });
      }
      // Moving vehicles: SDF arrow rotated to heading, tinted by severity color.
      if (!map.getLayer("vehicles-moving")) {
        map.addLayer({
          id: "vehicles-moving",
          type: "symbol",
          source: "vehicles",
          filter: ["==", ["get", "moving"], true],
          layout: {
            "icon-image": "vehicle-arrow",
            "icon-size": ["case", ["get", "selected"], 1.55, 1.15],
            "icon-rotate": ["get", "course"],
            "icon-rotation-alignment": "map",
            "icon-allow-overlap": true,
            "icon-ignore-placement": true,
          },
          paint: {
            "icon-color": ["get", "color"],
            "icon-opacity": 1,
          },
        });
      }
      // Keep the legacy "vehicles" layer id alive so click/hover handlers
      // registered once still fire — they are bound to this id.
      if (!map.getLayer("vehicles")) {
        map.addLayer({
          id: "vehicles",
          type: "circle",
          source: "vehicles",
          paint: {
            "circle-radius": 0,
            "circle-opacity": 0,
          },
        });
      }
    };

    const reattach = () => {
      addOverlays();
      ready.current = true;
      const { vehicles: v, selectedId: s } = dataRef.current;
      (map.getSource("vehicles") as maplibregl.GeoJSONSource).setData(
        vehicleData(v, s),
      );
      (map.getSource("geofence") as maplibregl.GeoJSONSource).setData(
        geofenceData(v, s),
      );
      clearLabels();
      const theme = offlineTheme(basemapRef.current);
      if (theme) addLabels(theme);
    };
    reattachRef.current = reattach;

    map.on("load", reattach);

    // Clicks and hover on both visible layers route through the same handlers.
    const handleClick = (
      event: maplibregl.MapMouseEvent & {
        features?: maplibregl.MapGeoJSONFeature[];
      },
    ) => {
      const feature = event.features?.[0];
      if (feature) onSelectRef.current(String(feature.properties.id));
    };
    const setCursorPointer = () => {
      map.getCanvas().style.cursor = "pointer";
    };
    const clearCursor = () => {
      map.getCanvas().style.cursor = "";
    };

    for (const layerId of [
      "vehicles-stationary",
      "vehicles-moving",
      "vehicles",
    ]) {
      map.on("click", layerId, handleClick);
      map.on("mouseenter", layerId, setCursorPointer);
      map.on("mouseleave", layerId, clearCursor);
    }

    // If a remote light style is configured but never loads — bad/blocked key,
    // offline network — drop to the bundled offline basemap rather than render
    // blank. (When it loads normally `ready` is already set and this no-ops.)
    let fallbackTimer: ReturnType<typeof setTimeout> | undefined;
    if (typeof resolveStyle("light") === "string") {
      fallbackTimer = setTimeout(() => {
        if (ready.current) return;
        map.setStyle(offlineStyle("light"));
        map.once("idle", reattach);
      }, 8000);
    }

    // Capture refs in local variables so the cleanup closure is stable.
    const tweens = tweensRef.current;
    const glow = glowRef;

    return () => {
      if (fallbackTimer) clearTimeout(fallbackTimer);
      clearLabels();
      // Cancel any running tweens.
      for (const entry of tweens.values()) {
        cancelAnimationFrame(entry.rafId);
      }
      tweens.clear();
      // Cancel glow animation.
      if (glow.current !== null) {
        cancelAnimationFrame(glow.current.rafId);
        glow.current = null;
      }
      map.remove();
      mapRef.current = null;
      ready.current = false;
    };
  }, []);

  // Swap the basemap when the toggle changes (the initial light style is set in
  // the constructor, so skip the first run).
  const firstRun = useRef(true);
  useEffect(() => {
    basemapRef.current = basemap;
    const map = mapRef.current;
    if (map === null) return;
    if (firstRun.current) {
      firstRun.current = false;
      return;
    }
    ready.current = false;
    map.setStyle(resolveStyle(basemap));
    map.once("idle", () => reattachRef.current());
  }, [basemap]);

  useEffect(() => {
    const map = mapRef.current;
    if (map === null || !ready.current) return;

    // --- Position tween logic ---
    // For each vehicle, if its position changed, start (or replace) a tween
    // from the last known position to the new one. Skipped entirely under
    // prefers-reduced-motion: with no tweens, positions snap below.
    const reduceMotion = prefersReducedMotion();
    const now = performance.now();
    const tweens = tweensRef.current;
    const prevPos = prevPositionsRef.current;

    for (const vehicle of vehicles) {
      const newLon = vehicle.position.lon;
      const newLat = vehicle.position.lat;
      const prev = prevPos.get(vehicle.id);

      if (!reduceMotion && prev !== undefined) {
        const [oldLon, oldLat] = prev;
        // Only tween if the position actually changed.
        if (oldLon !== newLon || oldLat !== newLat) {
          // Cancel any in-flight tween for this vehicle.
          const existing = tweens.get(vehicle.id);
          if (existing !== undefined) {
            cancelAnimationFrame(existing.rafId);
          }
          // Start a new tween from the previous (display) position.
          const entry: TweenEntry = {
            fromLon: oldLon,
            fromLat: oldLat,
            toLon: newLon,
            toLat: newLat,
            startTime: now,
            rafId: 0,
          };
          const tick = () => {
            const source = map.getSource("vehicles") as
              | maplibregl.GeoJSONSource
              | undefined;
            if (!source) return;
            const frameNow = performance.now();
            const elapsed = frameNow - entry.startTime;
            if (elapsed < TWEEN_DURATION_MS) {
              // Update just this vehicle's position in the current GeoJSON.
              const { vehicles: v, selectedId: s } = dataRef.current;
              const tweenedFeatures = buildTweenedData(v, s, tweens, frameNow);
              source.setData(tweenedFeatures);
              entry.rafId = requestAnimationFrame(tick);
            } else {
              // Tween complete: write the final authoritative position.
              prevPos.set(vehicle.id, [newLon, newLat]);
              tweens.delete(vehicle.id);
              const { vehicles: v, selectedId: s } = dataRef.current;
              source.setData(buildTweenedData(v, s, tweens, frameNow));
            }
          };
          entry.rafId = requestAnimationFrame(tick);
          tweens.set(vehicle.id, entry);
        }
      }
      // Always update the known target position so the next delta is correct.
      prevPos.set(vehicle.id, [newLon, newLat]);
    }
    // Prune ids that no longer exist.
    for (const id of prevPos.keys()) {
      if (!vehicles.find((v) => v.id === id)) {
        prevPos.delete(id);
        const entry = tweens.get(id);
        if (entry) {
          cancelAnimationFrame(entry.rafId);
          tweens.delete(id);
        }
      }
    }

    // If there are no active tweens, update the source immediately.
    if (tweens.size === 0) {
      (
        map.getSource("vehicles") as maplibregl.GeoJSONSource | undefined
      )?.setData(vehicleData(vehicles, selectedId));
    }

    (
      map.getSource("geofence") as maplibregl.GeoJSONSource | undefined
    )?.setData(geofenceData(vehicles, selectedId));

    // Recenter on a newly selected vehicle (not on every position tick).
    if (selectedId !== pannedTo.current) {
      pannedTo.current = selectedId;
      const target = vehicles.find((vehicle) => vehicle.id === selectedId);
      if (target) {
        map.easeTo({
          center: [target.position.lon, target.position.lat],
          duration: 600,
        });
      }
    }

    // --- Glow animation ---
    // Start the pulse when a vehicle is selected; stop when deselected. Under
    // prefers-reduced-motion the pulse is skipped — the static glow (default
    // paint values) still marks the selection without animating.
    if (selectedId !== null && !reduceMotion) {
      if (glowRef.current === null) {
        const state: GlowState = { rafId: 0, phase: 0 };
        glowRef.current = state;
        startGlowAnimation(map, state);
      }
    } else {
      if (glowRef.current !== null) {
        cancelAnimationFrame(glowRef.current.rafId);
        glowRef.current = null;
        // Reset to default paint values.
        if (map.getLayer("vehicle-glow")) {
          map.setPaintProperty("vehicle-glow", "circle-radius", 20);
          map.setPaintProperty("vehicle-glow", "circle-opacity", 0.18);
        }
      }
    }
  }, [vehicles, selectedId]);

  return (
    <div style={{ position: "relative", height: "100%", width: "100%" }}>
      <div ref={container} style={{ height: "100%", width: "100%" }} />
      <div
        className="map-switch"
        role="group"
        aria-label={t("map.switchLabel")}
      >
        {BASEMAP_CONFIGS.map(({ id, labelKey }) => {
          const disabled = id === "aerial" && MAP_AERIAL_URL === null;
          return (
            <button
              key={id}
              type="button"
              className={`map-switch__btn${basemap === id ? " is-active" : ""}`}
              aria-pressed={basemap === id}
              disabled={disabled}
              title={disabled ? t("map.aerialDisabled") : undefined}
              onClick={() => setBasemap(id)}
            >
              {t(labelKey)}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Build a GeoJSON FeatureCollection that applies any in-flight tweens to the
 * vehicles' current positions, blending smoothly toward the target.
 */
function buildTweenedData(
  vehicles: Vehicle[],
  selectedId: string | null,
  tweens: Map<string, TweenEntry>,
  now: number,
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: vehicles.map((vehicle) => {
      const severity = highestSeverity(vehicle);
      const tween = tweens.get(vehicle.id);
      let lon = vehicle.position.lon;
      let lat = vehicle.position.lat;
      if (tween !== undefined) {
        [lon, lat] = tweenCoords(tween, now);
      }
      return {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [lon, lat],
        },
        properties: {
          id: vehicle.id,
          color: severity === null ? CALM_COLOR : SEVERITY_COLOR[severity],
          selected: vehicle.id === selectedId,
          moving: vehicle.position.speed_mps > MOVING_THRESHOLD_MPS,
          course: vehicle.position.course_deg,
        },
      };
    }),
  };
}
