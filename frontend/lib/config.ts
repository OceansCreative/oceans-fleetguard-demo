/** Runtime endpoints, configurable via NEXT_PUBLIC_* env vars. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL ?? "ws://localhost:8000";

/** Map default view: centered on the Matsue / Yasugi / Yonago area. */
export const MAP_CENTER: [number, number] = [35.45, 133.2];
export const MAP_ZOOM = 12;

// Basemap. The app ships a self-contained offline vector style built from the
// bundled GeoJSON (no key, works air-gapped), in light and dark themes. Point
// these at vector-tile styles — MapTiler, a self-hosted Protomaps/OpenMapTiles
// style, etc. — for full street detail in production. The map's style switcher
// exposes light / dark / aerial.
export const MAP_STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? null;
export const MAP_STYLE_URL_DARK =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL_DARK ?? null;
// Aerial / satellite imagery always needs a provider; the toggle is disabled
// until this points at a raster style or tile JSON (e.g. MapTiler hybrid).
export const MAP_AERIAL_URL = process.env.NEXT_PUBLIC_MAP_AERIAL_URL ?? null;

// Always-shown credit for the bundled offline layers (a remote style adds its
// own provider/OSM attribution on top).
export const MAP_ATTRIBUTION =
  process.env.NEXT_PUBLIC_MAP_ATTRIBUTION ??
  "Boundaries: 国土数値情報（国土交通省） | Rail: ekidata.jp";
