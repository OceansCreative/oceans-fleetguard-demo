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

// ---------------------------------------------------------------------------
// Speed sparkline: a small inline SVG rendered from a rolling buffer.
// ---------------------------------------------------------------------------

/** Width × height of the sparkline SVG in pixels. */
const SPARK_W = 160;
const SPARK_H = 38;
const SPARK_PADDING = 2;

/**
 * Render a polyline sparkline from an array of speed values (m/s).
 * Handles empty and single-point cases gracefully.
 */
export function SpeedSparkline({
  samples,
}: {
  samples: number[];
}): React.JSX.Element {
  if (samples.length === 0) {
    return (
      <svg
        width={SPARK_W}
        height={SPARK_H}
        aria-hidden
        className="sparkline sparkline--empty"
        viewBox={`0 0 ${SPARK_W} ${SPARK_H}`}
      >
        <line
          x1={SPARK_PADDING}
          y1={SPARK_H / 2}
          x2={SPARK_W - SPARK_PADDING}
          y2={SPARK_H / 2}
          className="sparkline-zero"
        />
      </svg>
    );
  }

  const max = Math.max(...samples, 0.001); // avoid divide-by-zero
  const plotH = SPARK_H - SPARK_PADDING * 2;
  const plotW = SPARK_W - SPARK_PADDING * 2;

  // Map each sample to an SVG coordinate.
  const points = samples.map((val, i) => {
    const x = SPARK_PADDING + (i / Math.max(samples.length - 1, 1)) * plotW;
    const y = SPARK_PADDING + plotH - (val / max) * plotH;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  // Area fill: close the path along the bottom.
  const lastPoint =
    points[points.length - 1] ??
    `${SPARK_W - SPARK_PADDING},${SPARK_H - SPARK_PADDING}`;
  const firstPoint = points[0] ?? `${SPARK_PADDING},${SPARK_H - SPARK_PADDING}`;
  const lastX = lastPoint.split(",")[0] ?? String(SPARK_W - SPARK_PADDING);
  const firstX = firstPoint.split(",")[0] ?? String(SPARK_PADDING);
  const bottomY = String(SPARK_H - SPARK_PADDING);
  const areaPath = `M ${firstPoint} L ${points.join(" L ")} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`;

  // Latest dot position.
  const dotPoint =
    points[points.length - 1] ?? `${SPARK_W - SPARK_PADDING},${SPARK_H / 2}`;
  const dotParts = dotPoint.split(",");
  const dotX = dotParts[0];
  const dotY = dotParts[1];

  return (
    <svg
      width={SPARK_W}
      height={SPARK_H}
      aria-hidden
      className="sparkline"
      viewBox={`0 0 ${SPARK_W} ${SPARK_H}`}
    >
      <path d={areaPath} className="sparkline-area" />
      <polyline points={points.join(" ")} className="sparkline-line" />
      {dotX !== undefined && dotY !== undefined && (
        <circle cx={dotX} cy={dotY} r={2.5} className="sparkline-dot" />
      )}
    </svg>
  );
}

export function VehicleDetail({
  vehicle,
  speedSamples = [],
}: {
  vehicle: Vehicle | null;
  speedSamples?: number[];
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

      <div className="sparkline-section">
        <span className="section-label">{t("detail.speedRecent")}</span>
        <SpeedSparkline samples={speedSamples} />
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
