/**
 * Pure helper for maintaining a client-side rolling speed-history buffer.
 * Extracted from the hook so it can be unit-tested without React.
 */

import type { Vehicle } from "@/lib/types";

/** Maps vehicle id → array of recent speed_mps readings (oldest first). */
export type SpeedHistory = Record<string, number[]>;

/**
 * Append the current speed_mps of each vehicle in `vehicles` to `history`,
 * capping each vehicle's buffer at `cap` samples.  Vehicle ids that are no
 * longer present in the incoming fleet are pruned so memory stays bounded.
 *
 * Returns a new SpeedHistory object (does not mutate the input).
 */
export function appendSpeedSample(
  history: SpeedHistory,
  vehicles: Vehicle[],
  cap: number,
): SpeedHistory {
  const next: SpeedHistory = {};

  for (const vehicle of vehicles) {
    const prev = history[vehicle.id] ?? [];
    const appended = [...prev, vehicle.position.speed_mps];
    next[vehicle.id] = appended.length > cap ? appended.slice(-cap) : appended;
  }

  // Vehicle ids absent from `vehicles` are simply not copied → pruned.
  return next;
}
