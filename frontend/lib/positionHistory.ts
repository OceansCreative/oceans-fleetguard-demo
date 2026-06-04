/**
 * Pure helper for maintaining a client-side rolling position-history buffer,
 * used to draw a breadcrumb trail for the selected vehicle on the map.
 * Extracted from the hook so it can be unit-tested without React.
 */

import type { Vehicle } from "@/lib/types";

/** Maps vehicle id → array of recent [lon, lat] points (oldest first). */
export type PositionHistory = Record<string, [number, number][]>;

/**
 * Append the current [lon, lat] of each vehicle in `vehicles` to `history`,
 * capping each vehicle's buffer at `cap` points. Consecutive duplicate points
 * (a stationary vehicle) are collapsed so the trail does not accumulate a pile
 * of identical coordinates. Vehicle ids no longer present are pruned so memory
 * stays bounded.
 *
 * Returns a new PositionHistory object (does not mutate the input).
 */
export function appendPositionSample(
  history: PositionHistory,
  vehicles: Vehicle[],
  cap: number,
): PositionHistory {
  const next: PositionHistory = {};

  for (const vehicle of vehicles) {
    const point: [number, number] = [
      vehicle.position.lon,
      vehicle.position.lat,
    ];
    const prev = history[vehicle.id] ?? [];
    const last = prev[prev.length - 1];
    // Skip points identical to the previous one (stationary vehicle).
    const appended =
      last !== undefined && last[0] === point[0] && last[1] === point[1]
        ? prev
        : [...prev, point];
    next[vehicle.id] = appended.length > cap ? appended.slice(-cap) : appended;
  }

  // Vehicle ids absent from `vehicles` are simply not copied → pruned.
  return next;
}
