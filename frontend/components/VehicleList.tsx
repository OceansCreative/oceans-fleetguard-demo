import { highestSeverity, sortByUrgency, formatSpeedKmh } from "@/lib/format";
import type { Vehicle } from "@/lib/types";
import { CALM_COLOR, SEVERITY_COLOR } from "@/components/severity";

export function VehicleList({
  vehicles,
  selectedId,
  onSelect,
}: {
  vehicles: Vehicle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}): React.JSX.Element {
  const ordered = sortByUrgency(vehicles);
  return (
    <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
      {ordered.map((vehicle) => {
        const severity = highestSeverity(vehicle);
        const dot = severity === null ? CALM_COLOR : SEVERITY_COLOR[severity];
        const selected = vehicle.id === selectedId;
        return (
          <li key={vehicle.id}>
            <button
              type="button"
              onClick={() => onSelect(vehicle.id)}
              aria-pressed={selected}
              style={{
                width: "100%",
                textAlign: "left",
                border: "none",
                borderLeft: `4px solid ${dot}`,
                background: selected ? "#eef2ff" : "transparent",
                padding: "0.6rem 0.8rem",
                cursor: "pointer",
                display: "flex",
                justifyContent: "space-between",
                gap: "0.5rem",
              }}
            >
              <span>
                <strong>{vehicle.name}</strong>
                <br />
                <small style={{ color: "#6b7280" }}>
                  {formatSpeedKmh(vehicle.position.speed_mps)}
                  {vehicle.position.ignition_on ? "" : " · ignition off"}
                </small>
              </span>
              {vehicle.alerts.length > 0 && (
                <span aria-label={`${vehicle.alerts.length} alerts`}>
                  🚨 {vehicle.alerts.length}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
