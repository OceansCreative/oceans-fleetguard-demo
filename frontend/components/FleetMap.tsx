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

const WATER = "#aed3ec";
const EMPTY: GeoJSON.FeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

// A self-contained vector style drawn from the bundled GeoJSON, used when no
// remote style is configured. No glyphs are referenced (place names are HTML
// markers), so it needs no fonts and works fully offline.
const OFFLINE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    land: { type: "geojson", data: "/basemap.geojson" },
    rail: { type: "geojson", data: "/rail.geojson" },
  },
  layers: [
    { id: "bg", type: "background", paint: { "background-color": WATER } },
    {
      id: "land",
      type: "fill",
      source: "land",
      paint: { "fill-color": "#eef2e6" },
    },
    {
      id: "land-line",
      type: "line",
      source: "land",
      paint: { "line-color": "#aebfd2", "line-width": 1 },
    },
    {
      id: "rail",
      type: "line",
      source: "rail",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: {
        "line-color": "#6a6f86",
        "line-width": 1.4,
        "line-dasharray": [3, 2],
      },
    },
    {
      id: "stations",
      type: "circle",
      source: "rail",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 2.2,
        "circle-color": "#4a5067",
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1,
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
    map.on("load", () => {
      map.addSource("geofence", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "geofence-fill",
        type: "fill",
        source: "geofence",
        paint: { "fill-color": "#3b76f0", "fill-opacity": 0.08 },
      });
      map.addLayer({
        id: "geofence-line",
        type: "line",
        source: "geofence",
        paint: {
          "line-color": "#3b76f0",
          "line-width": 1.5,
          "line-dasharray": [2, 2],
        },
      });

      map.addSource("vehicles", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "vehicles",
        type: "circle",
        source: "vehicles",
        paint: {
          "circle-radius": ["case", ["get", "selected"], 9, 6],
          "circle-color": ["get", "color"],
          "circle-stroke-color": [
            "case",
            ["get", "selected"],
            "#1f2a3a",
            "#ffffff",
          ],
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

      // Place / water labels as HTML markers — only for the offline style; a
      // remote vector style brings its own labels.
      if (MAP_STYLE_URL === null) {
        fetch("/labels.geojson")
          .then((response) => response.json())
          .then((collection: GeoJSON.FeatureCollection) => {
            for (const feature of collection.features) {
              if (feature.geometry.type !== "Point") continue;
              const kind = String(feature.properties?.kind ?? "city");
              const element = document.createElement("div");
              element.className = `map-label map-label--${kind}`;
              element.textContent = String(feature.properties?.name ?? "");
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
      }

      ready.current = true;
      const { vehicles: v, selectedId: s } = dataRef.current;
      (map.getSource("vehicles") as maplibregl.GeoJSONSource).setData(
        vehicleData(v, s),
      );
      (map.getSource("geofence") as maplibregl.GeoJSONSource).setData(
        geofenceData(v, s),
      );
    });

    return () => {
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
