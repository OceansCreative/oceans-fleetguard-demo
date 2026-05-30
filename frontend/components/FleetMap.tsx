"use client";

import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

import {
  MAP_ATTRIBUTION,
  MAP_CENTER,
  MAP_STYLE_URL,
  MAP_ZOOM,
} from "@/lib/config";
import { highestSeverity } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { CALM_COLOR, SEVERITY_COLOR } from "@/components/severity";

import "maplibre-gl/dist/maplibre-gl.css";

const SEA = "#a7cde4";
const EMPTY: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

// A self-contained vector style drawn from the bundled GeoJSON, used when no
// remote style is configured. No glyphs are referenced (place names are HTML
// markers), so it needs no fonts and works fully offline. Styling leans on
// cartographic conventions — soft sea, a haloed coastline, railway hatching —
// so the limited offline data still reads as a deliberately designed map.
const OFFLINE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    land: { type: "geojson", data: "/basemap.geojson" },
    rail: { type: "geojson", data: "/rail.geojson" },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": SEA } },
    {
      id: "land",
      type: "fill",
      source: "land",
      paint: { "fill-color": "#f4f1ea" },
    },
    // Coastline: a soft white halo under a crisp blue-grey edge.
    {
      id: "coast-halo",
      type: "line",
      source: "land",
      paint: { "line-color": "#ffffff", "line-width": 3.5, "line-blur": 1.5 },
    },
    {
      id: "coast",
      type: "line",
      source: "land",
      paint: { "line-color": "#8aa6bb", "line-width": 1.1 },
    },
    // Railway: a pale bed with a dashed line on top (classic hatched look).
    {
      id: "rail-bed",
      type: "line",
      source: "rail",
      filter: ["==", ["get", "kind"], "rail"],
      layout: { "line-cap": "round" },
      paint: { "line-color": "#c2c5d4", "line-width": 3 },
    },
    {
      id: "rail-line",
      type: "line",
      source: "rail",
      filter: ["==", ["get", "kind"], "rail"],
      paint: {
        "line-color": "#5c627a",
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
        "circle-color": "#ffffff",
        "circle-stroke-color": "#5c627a",
        "circle-stroke-width": 1.1,
      },
    },
  ],
};

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
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const ready = useRef(false);
  // Keep the latest props reachable from the (stable) map callbacks.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const dataRef = useRef({ vehicles, selectedId });
  dataRef.current = { vehicles, selectedId };
  const pannedTo = useRef<string | null>(null);

  useEffect(() => {
    if (container.current === null) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: MAP_STYLE_URL ?? OFFLINE_STYLE,
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

    const markers: maplibregl.Marker[] = [];
    let activated = false;
    // Whether the *active* style is the bundled offline one (true from the
    // start when no remote style is configured, or after a fallback).
    let offlineMode = MAP_STYLE_URL === null;

    const addLabels = () => {
      fetch("/labels.geojson")
        .then((response) => response.json())
        .then((collection: GeoJSON.FeatureCollection) => {
          const MAJOR = new Set(["Matsue", "Yonago", "Izumo", "Yasugi"]);
          for (const feature of collection.features) {
            if (feature.geometry.type !== "Point") continue;
            const kind = String(feature.properties?.kind ?? "city");
            const name = String(feature.properties?.name ?? "");
            const element = document.createElement("div");
            element.className = `map-label map-label--${kind}${
              MAJOR.has(name) ? " map-label--major" : ""
            }`;
            element.textContent = name;
            markers.push(
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

    // Add the live overlays (geofence + vehicles) on top of whichever basemap
    // finished loading. Idempotent — guarded so a fallback can't double-add.
    const activate = () => {
      if (activated) return;
      activated = true;

      map.addSource("geofence", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "geofence-fill",
        type: "fill",
        source: "geofence",
        paint: { "fill-color": "#2f6fe0", "fill-opacity": 0.06 },
      });
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

      map.addSource("vehicles", { type: "geojson", data: EMPTY });
      // Soft glow under the selected vehicle.
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

      // Bundled place / water labels only when the offline basemap is active;
      // a remote vector style brings its own labels.
      if (offlineMode) addLabels();

      ready.current = true;
      const { vehicles: v, selectedId: s } = dataRef.current;
      (map.getSource("vehicles") as maplibregl.GeoJSONSource).setData(
        vehicleData(v, s),
      );
      (map.getSource("geofence") as maplibregl.GeoJSONSource).setData(
        geofenceData(v, s),
      );
    };

    map.on("load", activate);

    // If a remote style is configured but never loads — bad/blocked key,
    // offline network — drop to the bundled offline basemap rather than show a
    // blank map. (When the remote style loads normally, `activated` is already
    // true and this is a no-op.)
    let fallbackTimer: ReturnType<typeof setTimeout> | undefined;
    if (MAP_STYLE_URL !== null) {
      fallbackTimer = setTimeout(() => {
        if (activated) return;
        offlineMode = true;
        map.setStyle(OFFLINE_STYLE);
        map.once("idle", activate);
      }, 8000);
    }

    return () => {
      if (fallbackTimer) clearTimeout(fallbackTimer);
      for (const marker of markers) marker.remove();
      map.remove();
      mapRef.current = null;
      ready.current = false;
    };
  }, []);

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

  return <div ref={container} style={{ height: "100%", width: "100%" }} />;
}
