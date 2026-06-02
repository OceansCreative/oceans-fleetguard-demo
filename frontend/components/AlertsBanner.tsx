import type { Vehicle } from "@/lib/types";
import { useT } from "@/lib/i18n";

/** A top banner summarizing how many vehicles currently have active alerts. */
export function AlertsBanner({
  vehicles,
}: {
  vehicles: Vehicle[];
}): React.JSX.Element | null {
  const t = useT();
  const flagged = vehicles.filter((vehicle) => vehicle.alerts.length > 0);
  if (flagged.length === 0) {
    return null;
  }
  const noun =
    flagged.length > 1 ? t("banner.theftAlertPlural") : t("banner.theftAlert");
  return (
    <div role="alert" className="banner">
      <span className="banner-chip" aria-hidden>
        🚨
      </span>
      <span>
        <strong>{flagged.length}</strong> {noun} —{" "}
        <span className="banner-names">
          {flagged.map((v) => v.name).join(", ")}
        </span>
      </span>
    </div>
  );
}
