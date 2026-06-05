"use client";

import { useT } from "@/lib/i18n";

/** A single active toast: a newly-fired critical alert plus a unique id. */
export interface ActiveToast {
  id: string;
  vehicleId: string;
  vehicleName: string;
  reason: string;
}

/**
 * A fixed-position stack of CRITICAL-alert toasts. Purely presentational — the
 * queue and auto-dismiss timers live in the parent, so this renders cleanly and
 * is easy to test. "Locate" selects the vehicle (the map pans to it); "Dismiss"
 * drops the toast.
 */
export function AlertToasts({
  toasts,
  onLocate,
  onDismiss,
}: {
  toasts: ActiveToast[];
  onLocate: (vehicleId: string) => void;
  onDismiss: (toastId: string) => void;
}): React.JSX.Element | null {
  const t = useT();
  if (toasts.length === 0) {
    return null;
  }
  return (
    <div
      className="toast-stack"
      role="region"
      aria-label={t("alert.criticalTitle")}
    >
      {toasts.map((toast) => (
        <div key={toast.id} role="alert" className="toast toast--critical">
          <span className="toast-icon" aria-hidden>
            🚨
          </span>
          <div className="toast-body">
            <div className="toast-title">
              {t("alert.criticalTitle")} — {toast.vehicleName}
            </div>
            <div className="toast-reason">{toast.reason}</div>
            <div className="toast-actions">
              <button
                type="button"
                className="toast-btn toast-btn--primary"
                onClick={() => onLocate(toast.vehicleId)}
              >
                {t("alert.locate")}
              </button>
              <button
                type="button"
                className="toast-btn"
                onClick={() => onDismiss(toast.id)}
              >
                {t("alert.dismiss")}
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
