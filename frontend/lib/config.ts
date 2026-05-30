/** Runtime endpoints, configurable via NEXT_PUBLIC_* env vars. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

/** Map default view: centered on the Matsue / Yasugi / Yonago area. */
export const MAP_CENTER: [number, number] = [35.45, 133.2];
export const MAP_ZOOM = 12;
