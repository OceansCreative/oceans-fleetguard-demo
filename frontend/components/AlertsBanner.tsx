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
    <div role="alert" className="banner">
      <span className="banner-chip" aria-hidden>
        🚨
      </span>
      <span>
        <strong>
          {flagged.length} vehicle{flagged.length > 1 ? "s" : ""}
        </strong>{" "}
        with active theft alerts —{" "}
        <span className="banner-names">
          {flagged.map((v) => v.name).join(", ")}
        </span>
      </span>
    </div>
  );
}
