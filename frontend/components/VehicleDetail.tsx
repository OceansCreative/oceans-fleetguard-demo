import { formatDistanceKm, formatSpeedKmh } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { AlertBadge } from "@/components/AlertBadge";
import { SEVERITY_COLOR } from "@/components/severity";

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
  if (vehicle === null) {
    return (
      <div className="detail-empty">
        <span className="detail-empty-mark" aria-hidden>
          🛰
        </span>
        <span>Select a vehicle to see its details.</span>
      </div>
    );
  }
  const { position } = vehicle;
  const idle = !position.ignition_on;
  const dotColor = vehicle.alerts.length > 0 ? "#fb5566" : "#34d399";
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
        <Row label="Plate" value={vehicle.plate} />
        <Row label="Speed" value={formatSpeedKmh(position.speed_mps)} />
        <Row label="Heading" value={`${Math.round(position.course_deg)}°`} />
        <Row label="Ignition" value={idle ? "off" : "on"} />
        <Row
          label="Position"
          value={`${position.lat.toFixed(4)}, ${position.lon.toFixed(4)}`}
        />
        <Row
          label="Last update"
          value={new Date(position.recorded_at).toLocaleTimeString()}
        />
        {vehicle.geofence !== null && (
          <Row
            label="Geofence"
            value={`${formatDistanceKm(vehicle.geofence.radius_m)} radius`}
          />
        )}
      </div>

      <span className="section-label">Alerts</span>
      {vehicle.alerts.length === 0 ? (
        <p className="detail-ok">✓ No active alerts</p>
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
