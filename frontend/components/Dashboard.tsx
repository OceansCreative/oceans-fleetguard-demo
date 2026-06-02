"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";

import { isAuthed, logout } from "@/lib/auth";
import { useFleet } from "@/lib/useFleet";
import { AlertsBanner } from "@/components/AlertsBanner";
import { LoginForm } from "@/components/LoginForm";
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
  // When the login gate is enabled and our session is missing/expired, a REST
  // 401 flips this on and we show the login form instead of the dashboard.
  const [needsLogin, setNeedsLogin] = useState(false);
  const onUnauthorized = useCallback(() => setNeedsLogin(true), []);
  const { vehicles, connection } = useFleet({ onUnauthorized });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    vehicles.find((vehicle) => vehicle.id === selectedId) ?? null;
  // Only offer "Sign out" when a session token is actually in use; the keyless
  // quickstart (login disabled) shows nothing extra.
  const showLogout = isAuthed();

  if (needsLogin) {
    // Remount the dashboard on success so useFleet re-seeds with the token.
    return <LoginForm onAuthed={() => window.location.reload()} />;
  }

  function handleLogout(): void {
    logout();
    setNeedsLogin(true);
  }

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
        <div className="header-right">
          <span className={`conn conn--${connection}`}>
            <span className="conn-dot" />
            {CONNECTION_LABEL[connection]}
          </span>
          {showLogout && (
            <button type="button" className="logout-btn" onClick={handleLogout}>
              Sign out
            </button>
          )}
        </div>
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
