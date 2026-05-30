"use client";

import L from "leaflet";
import type { GeoJsonObject } from "geojson";
import { useEffect, useState } from "react";
import {
  Circle,
  CircleMarker,
  GeoJSON,
  MapContainer,
  Pane,
  Popup,
  TileLayer,
} from "react-leaflet";

import { MAP_CENTER, MAP_ZOOM } from "@/lib/config";
import { formatSpeedKmh, highestSeverity } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { CALM_COLOR, SEVERITY_COLOR } from "@/components/severity";

import "leaflet/dist/leaflet.css";

// Avoid Leaflet's default-icon 404s; we render CircleMarkers instead.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })
  ._getIconUrl;

const LAND_STYLE = {
  color: "#bccdde",
  weight: 1,
  fillColor: "#edf1e8",
  fillOpacity: 1,
};
const RAIL_STYLE = {
  color: "#6a6f86",
  weight: 1.6,
  opacity: 0.85,
  dashArray: "5 3",
};
const stationDot = (_feature: unknown, latlng: L.LatLng): L.CircleMarker =>
  L.circleMarker(latlng, {
    pane: "basemap",
    radius: 2.2,
    weight: 1,
    color: "#ffffff",
    fillColor: "#4a5067",
    fillOpacity: 1,
  });

export function FleetMap({
  vehicles,
  selectedId,
  onSelect,
}: {
  vehicles: Vehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}): React.JSX.Element {
  // A small, bundled vector basemap of the demo area (Matsue / Yonago, incl.
  // Lake Shinji & Nakaumi). It sits in a pane *below* the OSM tiles, so a live
  // network shows full street tiles while an offline/locked-down one still
  // renders recognizable coastline and water instead of a blank rectangle.
  const [land, setLand] = useState<GeoJsonObject | null>(null);
  const [rail, setRail] = useState<GeoJsonObject | null>(null);
  useEffect(() => {
    let active = true;
    const load = (path: string, set: (d: GeoJsonObject) => void) =>
      fetch(path)
        .then((response) => response.json())
        .then((data: GeoJsonObject) => {
          if (active) set(data);
        })
        .catch(() => {
          /* A missing layer is fine; the map still works without it. */
        });
    load("/basemap.geojson", setLand);
    load("/rail.geojson", setRail); // railway lines + stations (ekidata.jp)
    return () => {
      active = false;
    };
  }, []);

  const selectedGeofence =
    vehicles.find((vehicle) => vehicle.id === selectedId)?.geofence ?? null;
  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={MAP_ZOOM}
      style={{ height: "100%", width: "100%" }}
    >
      <Pane name="basemap" style={{ zIndex: 150 }}>
        {land !== null && (
          <GeoJSON data={land} interactive={false} style={() => LAND_STYLE} />
        )}
        {rail !== null && (
          <GeoJSON
            data={rail}
            interactive={false}
            style={() => RAIL_STYLE}
            pointToLayer={stationDot}
          />
        )}
      </Pane>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | Boundaries: 国土数値情報（国土交通省） | Rail: ekidata.jp'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {selectedGeofence !== null && (
        // The allowed area the geofence rule checks the selected vehicle against.
        <Circle
          center={[selectedGeofence.lat, selectedGeofence.lon]}
          radius={selectedGeofence.radius_m}
          pathOptions={{
            color: "#3b76f0",
            weight: 1.5,
            dashArray: "6 6",
            fillColor: "#3b76f0",
            fillOpacity: 0.08,
          }}
        />
      )}
      {vehicles.map((vehicle) => {
        const severity = highestSeverity(vehicle);
        const color = severity === null ? CALM_COLOR : SEVERITY_COLOR[severity];
        const selected = vehicle.id === selectedId;
        return (
          <CircleMarker
            key={vehicle.id}
            center={[vehicle.position.lat, vehicle.position.lon]}
            radius={selected ? 11 : 8}
            pathOptions={{
              color: selected ? "#1f2a3a" : "#ffffff",
              weight: selected ? 3 : 1.5,
              fillColor: color,
              fillOpacity: 0.95,
            }}
            eventHandlers={{ click: () => onSelect(vehicle.id) }}
          >
            <Popup>
              <strong>{vehicle.name}</strong>
              <br />
              {formatSpeedKmh(vehicle.position.speed_mps)}
              {vehicle.alerts.length > 0 && (
                <>
                  <br />
                  🚨 {vehicle.alerts.length} alert
                  {vehicle.alerts.length > 1 ? "s" : ""}
                </>
              )}
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
