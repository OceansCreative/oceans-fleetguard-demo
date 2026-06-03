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

    // (Re)add the live overlay sources/layers on top of whichever basemap just
    // loaded. Guarded so it is safe to call after every style change.
    const addOverlays = () => {
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
      if (!map.getLayer("vehicles")) {
        map.addLayer({
          id: "vehicles",
          type: "circle",
          source: "vehicles",
          paint: {
            "circle-radius": ["case", ["get", "selected"], 8, 5.5],
            "circle-color": ["get", "color"],
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": ["case", ["get", "selected"], 3, 1.5],
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

    // Interaction handlers bind by layer id and survive style swaps, so add
    // them once.
    map.on("click", "vehicles", (event) => {
      const feature = event.features?.[0];
      if (feature) onSelectRef.current(String(feature.properties.id));
    });
    map.on("mouseenter", "vehicles", () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "vehicles", () => {
      map.getCanvas().style.cursor = "";
    });

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

    return () => {
      if (fallbackTimer) clearTimeout(fallbackTimer);
      clearLabels();
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
    (
      map.getSource("vehicles") as maplibregl.GeoJSONSource | undefined
    )?.setData(vehicleData(vehicles, selectedId));
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
