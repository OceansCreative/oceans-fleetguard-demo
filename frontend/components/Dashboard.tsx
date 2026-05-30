"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { useFleet } from "@/lib/useFleet";
import { AlertsBanner } from "@/components/AlertsBanner";
import { VehicleDetail } from "@/components/VehicleDetail";
import { VehicleList } from "@/components/VehicleList";

// Leaflet touches `window`, so the map must be client-only (no SSR).
const FleetMap = dynamic(
  () => import("@/components/FleetMap").then((m) => m.FleetMap),
  {
    ssr: false,
    loading: () => <div className="map-loading">Loading map…</div>,
  },
);

const CONNECTION_LABEL = {
  connecting: "connecting",
  live: "live",
  reconnecting: "reconnecting",
} as const;

export function Dashboard(): React.JSX.Element {
  const { vehicles, connection } = useFleet();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    vehicles.find((vehicle) => vehicle.id === selectedId) ?? null;

  return (
    <div className="shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            🛰
          </span>
          <span className="brand-text">
            <span className="brand-name">FleetGuard</span>
            <span className="brand-sub">Fleet Operations</span>
          </span>
        </div>
        <span className={`conn conn--${connection}`}>
          <span className="conn-dot" />
          {CONNECTION_LABEL[connection]}
        </span>
      </header>

      <AlertsBanner vehicles={vehicles} />

      <div className="body">
        <aside className="col-list scroll">
          <div className="col-head">
            <span className="col-title">Fleet</span>
            <span className="col-count">{vehicles.length} vehicles</span>
          </div>
          <VehicleList
            vehicles={vehicles}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>

        <main className="col-map">
          <FleetMap
            vehicles={vehicles}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </main>

        <aside className="col-detail scroll">
          <VehicleDetail vehicle={selected} />
        </aside>
      </div>
    </div>
  );
}
