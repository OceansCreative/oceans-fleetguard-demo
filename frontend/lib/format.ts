/** Presentation helpers — pure functions, unit-tested in isolation. */

import type { AlertSeverity, Vehicle } from "@/lib/types";

const MS_TO_KMH = 3.6;
const EM_DASH = "—";

const SEVERITY_RANK: Record<AlertSeverity, number> = {
  critical: 3,
  warning: 2,
  info: 1,
};

/**
 * Format a speed given in meters per second as a rounded "N km/h" string.
 * Returns an em dash for missing or invalid (negative / non-finite) input.
 */
export function formatSpeedKmh(metersPerSecond: number): string {
  if (!Number.isFinite(metersPerSecond) || metersPerSecond < 0) {
    return EM_DASH;
  }
  return `${Math.round(metersPerSecond * MS_TO_KMH)} km/h`;
}

/** Format a distance given in meters as a "N.N km" string. */
export function formatDistanceKm(meters: number): string {
  if (!Number.isFinite(meters) || meters < 0) {
    return EM_DASH;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

/**
 * The most urgent severity among a vehicle's alerts, or `null` when it has
 * none. Used to drive marker color and list sorting.
 */
export function highestSeverity(vehicle: Vehicle): AlertSeverity | null {
  let best: AlertSeverity | null = null;
  for (const alert of vehicle.alerts) {
    if (best === null || SEVERITY_RANK[alert.severity] > SEVERITY_RANK[best]) {
      best = alert.severity;
    }
  }
  return best;
}

/**
 * Sort vehicles so the most urgent (most severe alert) come first; vehicles
 * with equal severity keep a stable, name-based order. Does not mutate input.
 */
export function sortByUrgency(vehicles: readonly Vehicle[]): Vehicle[] {
  return [...vehicles].sort((a, b) => {
    const sa = highestSeverity(a);
    const sb = highestSeverity(b);
    const ra = sa === null ? 0 : SEVERITY_RANK[sa];
    const rb = sb === null ? 0 : SEVERITY_RANK[sb];
    if (ra !== rb) {
      return rb - ra;
    }
    return a.name.localeCompare(b.name);
  });
}
