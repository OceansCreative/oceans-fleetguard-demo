const MS_TO_KMH = 3.6;
const EM_DASH = "—";

/**
 * Format a speed given in meters per second as a rounded "N km/h" string.
 *
 * Returns an em dash for missing or invalid (negative / non-finite) input so
 * the UI never renders "NaN km/h".
 */
export function formatSpeedKmh(metersPerSecond: number): string {
  if (!Number.isFinite(metersPerSecond) || metersPerSecond < 0) {
    return EM_DASH;
  }
  return `${Math.round(metersPerSecond * MS_TO_KMH)} km/h`;
}
