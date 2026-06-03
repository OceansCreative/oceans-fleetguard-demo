"use client";

import { useEffect, useRef, useState } from "react";

import { fetchAlertHistory } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { AlertHistoryEntry } from "@/lib/types";
import { AlertBadge } from "@/components/AlertBadge";
import { SEVERITY_COLOR } from "@/components/severity";

const REFRESH_INTERVAL_MS = 10_000;
const DEFAULT_LIMIT = 20;

/** Format a recorded_at ISO string as a relative "X ago" label. */
function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr}h`;
}

export function AlertHistoryPanel(): React.JSX.Element {
  const t = useT();
  const [entries, setEntries] = useState<AlertHistoryEntry[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function load(): void {
    fetchAlertHistory(DEFAULT_LIMIT)
      .then(setEntries)
      .catch(() => {
        // silently ignore fetch errors (network, auth) to keep panel non-disruptive
      });
  }

  useEffect(() => {
    load();
    intervalRef.current = setInterval(load, REFRESH_INTERVAL_MS);
    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return (
    <section className="history-panel">
      <span className="section-label">{t("history.title")}</span>
      {entries.length === 0 ? (
        <p className="detail-ok">✓ {t("history.empty")}</p>
      ) : (
        <ul className="alert-list">
          {entries.map((entry, idx) => (
            <li
              key={`${entry.vehicle_id}-${entry.recorded_at}-${idx}`}
              className="alert-card history-card"
              style={{
                borderLeftColor: SEVERITY_COLOR[entry.alert_severity],
              }}
            >
              <div className="history-card-top">
                <AlertBadge severity={entry.alert_severity}>
                  {entry.alert_severity}
                </AlertBadge>
                <span className="history-vehicle">{entry.vehicle_name}</span>
                <span className="history-time">
                  {relativeTime(entry.recorded_at)} {t("history.ago")}
                </span>
              </div>
              <span className="alert-reason">{entry.alert_reason}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
