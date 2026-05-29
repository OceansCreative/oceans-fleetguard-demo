import { formatDistanceKm, formatSpeedKmh } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { AlertBadge } from "@/components/AlertBadge";

function Row({
  label,
  value,
}: {
  label: string;
  value: string;
}): React.JSX.Element {
  return (
    <div
      style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}
    >
      <span style={{ color: "#6b7280" }}>{label}</span>
      <span>{value}</span>
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
      <p style={{ color: "#6b7280" }}>Select a vehicle to see its details.</p>
    );
  }
  const { position } = vehicle;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      <h2 style={{ margin: 0 }}>{vehicle.name}</h2>
      <Row label="Plate" value={vehicle.plate} />
      <Row label="Speed" value={formatSpeedKmh(position.speed_mps)} />
      <Row label="Heading" value={`${Math.round(position.course_deg)}°`} />
      <Row label="Ignition" value={position.ignition_on ? "on" : "off"} />
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

      <h3 style={{ margin: "0.4rem 0 0" }}>Alerts</h3>
      {vehicle.alerts.length === 0 ? (
        <p style={{ color: "#16a34a", margin: 0 }}>No active alerts.</p>
      ) : (
        <ul style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
          {vehicle.alerts.map((alert) => (
            <li
              key={alert.type}
              style={{
                display: "flex",
                gap: "0.5rem",
                alignItems: "center",
                marginBottom: "0.3rem",
              }}
            >
              <AlertBadge severity={alert.severity}>
                {alert.severity}
              </AlertBadge>
              <span>{alert.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
