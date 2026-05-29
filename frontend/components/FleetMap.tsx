"use client";

import L from "leaflet";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import { MAP_CENTER, MAP_ZOOM } from "@/lib/config";
import { formatSpeedKmh, highestSeverity } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { CALM_COLOR, SEVERITY_COLOR } from "@/components/severity";

import "leaflet/dist/leaflet.css";

// Avoid Leaflet's default-icon 404s; we render CircleMarkers instead.
delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })
  ._getIconUrl;

export function FleetMap({
  vehicles,
  selectedId,
  onSelect,
}: {
  vehicles: Vehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}): React.JSX.Element {
  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={MAP_ZOOM}
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
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
              color: selected ? "#111827" : color,
              weight: selected ? 3 : 1,
              fillColor: color,
              fillOpacity: 0.9,
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
