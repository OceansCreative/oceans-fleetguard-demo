/** Runtime endpoints, configurable via NEXT_PUBLIC_* env vars. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

/** Map default view: centered on the Matsue / Yasugi / Yonago area. */
export const MAP_CENTER: [number, number] = [35.45, 133.2];
export const MAP_ZOOM = 12;

// Map tiles. Defaults to OpenStreetMap (no key). Point NEXT_PUBLIC_TILE_URL at a
// commercial provider (Mapbox, MapTiler, …) to swap basemaps without code
// changes; include the API key in the URL template and set a matching
// NEXT_PUBLIC_TILE_ATTRIBUTION. The bundled-data credits are always appended.
const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const BUNDLED_CREDITS =
  "Boundaries: 国土数値情報（国土交通省） | Rail: ekidata.jp";

export const TILE_URL = process.env.NEXT_PUBLIC_TILE_URL ?? OSM_TILE_URL;
export const TILE_ATTRIBUTION = `${
  process.env.NEXT_PUBLIC_TILE_ATTRIBUTION ?? OSM_ATTRIBUTION
} | ${BUNDLED_CREDITS}`;
