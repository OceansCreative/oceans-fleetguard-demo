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
    <ul className="vlist">
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
              className={`vrow${selected ? " vrow--selected" : ""}`}
            >
              <span
                className="vrow-dot"
                style={{ background: dot }}
                aria-hidden
              />
              <span className="vrow-main">
                <span className="vrow-name">{vehicle.name}</span>
                <span className="vrow-meta">
                  {formatSpeedKmh(vehicle.position.speed_mps)}
                  {!vehicle.position.ignition_on && (
                    <span className="chip-off">ign off</span>
                  )}
                </span>
              </span>
              {vehicle.alerts.length > 0 && (
                <span
                  className="vrow-alerts"
                  aria-label={`${vehicle.alerts.length} alerts`}
                >
                  ⚠ {vehicle.alerts.length}
                </span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}
