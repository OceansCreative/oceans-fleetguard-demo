import type { Vehicle } from "@/lib/types";

/** A top banner summarizing how many vehicles currently have active alerts. */
export function AlertsBanner({
  vehicles,
}: {
  vehicles: Vehicle[];
}): React.JSX.Element | null {
  const flagged = vehicles.filter((vehicle) => vehicle.alerts.length > 0);
  if (flagged.length === 0) {
    return null;
  }
  return (
    <div
      role="alert"
      style={{
        background: "#dc2626",
        color: "white",
        padding: "0.5rem 1rem",
        fontWeight: 600,
      }}
    >
      🚨 {flagged.length} vehicle{flagged.length > 1 ? "s" : ""} with active
      theft alerts: {flagged.map((v) => v.name).join(", ")}
    </div>
  );
}
