/**
 * Pure helpers for detecting vehicles that have *just* entered a CRITICAL
 * (theft) alert state, so the dashboard can raise an active notification rather
 * than relying on the operator noticing the passive banner. Extracted from the
 * component so the transition logic can be unit-tested without React.
 */

import type { Vehicle } from "@/lib/types";

/** A newly-fired critical alert, ready to surface as a toast. */
export interface CriticalAlert {
  vehicleId: string;
  vehicleName: string;
  reason: string;
}

/** The set of vehicle ids that currently carry at least one critical alert. */
export function criticalVehicleIds(vehicles: Vehicle[]): Set<string> {
  const ids = new Set<string>();
  for (const vehicle of vehicles) {
    if (vehicle.alerts.some((alert) => alert.severity === "critical")) {
      ids.add(vehicle.id);
    }
  }
  return ids;
}

/**
 * Vehicles that are critical now but were not in `prevIds` — i.e. the alert
 * just fired. Returns one entry per newly-critical vehicle, using its first
 * critical alert's reason. A vehicle that stays critical across frames is not
 * reported again; one that recovers and re-offends is reported afresh.
 */
export function newCriticalAlerts(
  prevIds: Set<string>,
  vehicles: Vehicle[],
): CriticalAlert[] {
  const fresh: CriticalAlert[] = [];
  for (const vehicle of vehicles) {
    const critical = vehicle.alerts.find(
      (alert) => alert.severity === "critical",
    );
    if (critical !== undefined && !prevIds.has(vehicle.id)) {
      fresh.push({
        vehicleId: vehicle.id,
        vehicleName: vehicle.name,
        reason: critical.reason,
      });
    }
  }
  return fresh;
}
