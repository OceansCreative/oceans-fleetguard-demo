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
    loading: () => <div style={{ padding: "1rem" }}>Loading map…</div>,
  },
);

const CONNECTION_LABEL = {
  connecting: "● connecting",
  live: "● live",
  reconnecting: "● reconnecting…",
} as const;

const CONNECTION_COLOR = {
  connecting: "#9ca3af",
  live: "#16a34a",
  reconnecting: "#d97706",
} as const;

export function Dashboard(): React.JSX.Element {
  const { vehicles, connection } = useFleet();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    vehicles.find((vehicle) => vehicle.id === selectedId) ?? null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0.6rem 1rem",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        <strong>🛰️ FleetGuard</strong>
        <span style={{ color: CONNECTION_COLOR[connection] }}>
          {CONNECTION_LABEL[connection]}
        </span>
      </header>

      <AlertsBanner vehicles={vehicles} />

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <aside
          style={{
            width: 280,
            borderRight: "1px solid #e5e7eb",
            overflowY: "auto",
          }}
        >
          <VehicleList
            vehicles={vehicles}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>

        <main style={{ flex: 1, minWidth: 0 }}>
          <FleetMap
            vehicles={vehicles}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </main>

        <aside
          style={{
            width: 320,
            borderLeft: "1px solid #e5e7eb",
            padding: "1rem",
            overflowY: "auto",
          }}
        >
          <VehicleDetail vehicle={selected} />
        </aside>
      </div>
    </div>
  );
}
