/** Pure parser for the `/ws/positions` WebSocket payload. */

import type { PositionsMessage, Vehicle } from "@/lib/types";

/** Extract the vehicles array from a WebSocket frame, or `null` if malformed. */
export function parsePositions(data: unknown): Vehicle[] | null {
  if (typeof data !== "object" || data === null) {
    return null;
  }
  const message = data as Partial<PositionsMessage>;
  return Array.isArray(message.vehicles) ? message.vehicles : null;
}
