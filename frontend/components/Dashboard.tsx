"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

import { useFleet } from "@/lib/useFleet";
import { useLang, useT } from "@/lib/i18n";
import { AlertsBanner } from "@/components/AlertsBanner";
import { VehicleDetail } from "@/components/VehicleDetail";
import { VehicleList } from "@/components/VehicleList";

// MapLibre touches `window`, so the map must be client-only (no SSR).
const FleetMap = dynamic(
  () => import("@/components/FleetMap").then((m) => m.FleetMap),
  {
    ssr: false,
    loading: () => <div className="map-loading">Loading map…</div>,
  },
);

export function Dashboard(): React.JSX.Element {
  const { vehicles, connection } = useFleet();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected =
    vehicles.find((vehicle) => vehicle.id === selectedId) ?? null;
  const t = useT();
  const { lang, setLang } = useLang();

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
          />
        </main>

        <aside className="col-detail scroll">
          <VehicleDetail vehicle={selected} />
        </aside>
      </div>
    </div>
  );
}
