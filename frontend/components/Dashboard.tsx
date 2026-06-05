"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  criticalVehicleIds,
  newCriticalAlerts,
} from "@/lib/alertNotifications";
import { isAuthed, logout } from "@/lib/auth";
import { useFleet } from "@/lib/useFleet";
import { useLang, useT } from "@/lib/i18n";
import { AlertHistoryPanel } from "@/components/AlertHistoryPanel";
import { AlertsBanner } from "@/components/AlertsBanner";
import { AlertToasts, type ActiveToast } from "@/components/AlertToasts";
import { LoginForm } from "@/components/LoginForm";
import { VehicleDetail } from "@/components/VehicleDetail";
import { VehicleList } from "@/components/VehicleList";

/** How long a critical-alert toast stays on screen before auto-dismissing. */
const TOAST_TTL_MS = 8000;

// MapLibre touches `window`, so the map must be client-only (no SSR).
const FleetMap = dynamic(
  () => import("@/components/FleetMap").then((m) => m.FleetMap),
  {
    ssr: false,
    loading: () => <div className="map-loading">Loading map…</div>,
  },
);

export function Dashboard(): React.JSX.Element {
  // When the login gate is enabled and our session is missing/expired, a REST
  // 401 flips this on and we show the login form instead of the dashboard.
  const [needsLogin, setNeedsLogin] = useState(false);
  const onUnauthorized = useCallback(() => setNeedsLogin(true), []);
  const { vehicles, connection, speedHistory, positionHistory } = useFleet({
    onUnauthorized,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    vehicles.find((vehicle) => vehicle.id === selectedId) ?? null;
  const t = useT();
  const { lang, setLang } = useLang();
  // Only offer "Sign out" when a session token is actually in use; the keyless
  // quickstart (login disabled) shows nothing extra.
  const showLogout = isAuthed();

  // Active-notification toasts for vehicles that *just* turned critical, so a
  // theft alert grabs attention instead of only updating the passive banner.
  const [toasts, setToasts] = useState<ActiveToast[]>([]);
  const prevCriticalRef = useRef<Set<string>>(new Set());
  const toastSeqRef = useRef(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    const fresh = newCriticalAlerts(prevCriticalRef.current, vehicles);
    prevCriticalRef.current = criticalVehicleIds(vehicles);
    if (fresh.length === 0) return;
    const added: ActiveToast[] = fresh.map((alert) => ({
      id: `toast-${(toastSeqRef.current += 1)}`,
      ...alert,
    }));
    setToasts((current) => [...current, ...added]);
    for (const toast of added) {
      const timer = setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== toast.id));
      }, TOAST_TTL_MS);
      timersRef.current.push(timer);
    }
  }, [vehicles]);

  // Clear any pending auto-dismiss timers on unmount.
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      for (const timer of timers) clearTimeout(timer);
    };
  }, []);

  const dismissToast = useCallback((toastId: string) => {
    setToasts((current) => current.filter((item) => item.id !== toastId));
  }, []);

  const locateVehicle = useCallback((vehicleId: string) => {
    setSelectedId(vehicleId);
    setToasts((current) =>
      current.filter((item) => item.vehicleId !== vehicleId),
    );
  }, []);

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
            <span className="brand-name">{t("app.title")}</span>
            <span className="brand-sub">{t("app.sub")}</span>
          </span>
        </div>
        <div className="header-right">
          <span className={`conn conn--${connection}`}>
            <span className="conn-dot" />
            {t(`status.${connection}` as Parameters<typeof t>[0])}
          </span>
          <button
            type="button"
            className="lang-toggle"
            onClick={() => setLang(lang === "en" ? "ja" : "en")}
            aria-label="Switch language"
          >
            {t("lang.toggle")}
          </button>
          {showLogout && (
            <button type="button" className="logout-btn" onClick={handleLogout}>
              {t("auth.signOut")}
            </button>
          )}
        </div>
      </header>

      <AlertsBanner vehicles={vehicles} />

      <div className="body">
        <aside className="col-list scroll">
          <div className="col-head">
            <span className="col-title">{t("fleet.title")}</span>
            <span className="col-count">
              {vehicles.length} {t("fleet.vehicles")}
            </span>
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
            trail={
              selected !== null ? (positionHistory[selected.id] ?? []) : []
            }
          />
        </main>

        <aside className="col-detail scroll">
          <VehicleDetail
            vehicle={selected}
            speedSamples={
              selected !== null ? (speedHistory[selected.id] ?? []) : []
            }
          />
          <div className="col-detail-divider" />
          <AlertHistoryPanel />
        </aside>
      </div>

      <AlertToasts
        toasts={toasts}
        onLocate={locateVehicle}
        onDismiss={dismissToast}
      />
    </div>
  );
}
