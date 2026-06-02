import { formatDistanceKm, formatSpeedKmh } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { AlertBadge } from "@/components/AlertBadge";
import { SEVERITY_COLOR } from "@/components/severity";
import { useT } from "@/lib/i18n";

function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div className="drow">
      <span className="drow-label">{label}</span>
      <span className="drow-value">{value}</span>
    </div>
  );
}

export function VehicleDetail({
  vehicle,
}: {
  vehicle: Vehicle | null;
}): React.JSX.Element {
  const t = useT();
  if (vehicle === null) {
    return (
      <div className="detail-empty">
        <span className="detail-empty-mark" aria-hidden>
          🛰
        </span>
        <span>{t("fleet.noVehicleSelected")}</span>
      </div>
    );
  }
  const { position } = vehicle;
  const idle = !position.ignition_on;
  const dotColor = vehicle.alerts.length > 0 ? "#ef4d54" : "#22c55e";
  return (
    <div className="detail">
      <div className="detail-title">
        <span
          className="vrow-dot"
          style={{ background: dotColor }}
          aria-hidden
        />
        <h2>{vehicle.name}</h2>
      </div>

      <div className="detail-rows">
        <Row label={t("detail.plate")} value={vehicle.plate} />
        <Row
          label={t("detail.speed")}
          value={formatSpeedKmh(position.speed_mps)}
        />
        <Row
          label={t("detail.heading")}
          value={`${Math.round(position.course_deg)}°`}
        />
        <Row
          label={t("detail.ignition")}
          value={idle ? t("detail.ignitionOff") : t("detail.ignitionOn")}
        />
        <Row
          label={t("detail.position")}
          value={`${position.lat.toFixed(4)}, ${position.lon.toFixed(4)}`}
        />
        <Row
          label={t("detail.lastUpdate")}
          value={new Date(position.recorded_at).toLocaleTimeString()}
        />
        {vehicle.geofence !== null && (
          <Row
            label={t("detail.geofence")}
            value={`${formatDistanceKm(vehicle.geofence.radius_m)} ${t("detail.geofenceRadius")}`}
          />
        )}
      </div>

      <span className="section-label">{t("detail.alerts")}</span>
      {vehicle.alerts.length === 0 ? (
        <p className="detail-ok">✓ {t("detail.noAlerts")}</p>
      ) : (
        <ul className="alert-list">
          {vehicle.alerts.map((alert) => (
            <li
              key={alert.type}
              className="alert-card"
              style={{ borderLeftColor: SEVERITY_COLOR[alert.severity] }}
            >
              <AlertBadge severity={alert.severity}>
                {alert.severity}
              </AlertBadge>
              <span className="alert-reason">{alert.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
