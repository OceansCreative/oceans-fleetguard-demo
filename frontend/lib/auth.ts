/**
 * Opt-in user-login session handling for the browser.
 *
 * This is a SECOND, independent gate layered on top of the optional shared
 * API key. When the backend has `AUTH_SECRET` set, REST/WS calls require a
 * signed session token obtained via `POST /api/auth/login`. When it is unset,
 * login is unused and the keyless quickstart is unaffected.
 *
 * SECURITY NOTE: the token is kept in `localStorage` so it survives reloads.
 * That is convenient but readable by any script on the page, so it is exposed
 * to XSS. For a hardened deployment, prefer an httpOnly cookie set by a
 * backend-for-frontend. This MVP keeps it self-contained and dependency-free.
 */

import { API_BASE_URL } from "@/lib/config";

const TOKEN_KEY = "fleetguard.auth.token";
const EXPIRES_KEY = "fleetguard.auth.expiresAt";

interface LoginResponse {
  token: string;
  expires_at: number;
}

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The stored token, or `null` when absent or expired. */
export function getToken(): string | null {
  const store = storage();
  if (store === null) {
    return null;
  }
  const token = store.getItem(TOKEN_KEY);
  if (token === null) {
    return null;
  }
  const expiresAt = Number(store.getItem(EXPIRES_KEY) ?? "0");
  if (Number.isFinite(expiresAt) && expiresAt > 0) {
    // Treat as expired a few seconds early to avoid racing the backend clock.
    if (Date.now() / 1000 >= expiresAt - 5) {
      logout();
      return null;
    }
  }
  return token;
}

/** True when a non-expired session token is present. */
export function isAuthed(): boolean {
  return getToken() !== null;
}

/** Clear any stored session token. */
export function logout(): void {
  const store = storage();
  if (store === null) {
    return;
  }
  store.removeItem(TOKEN_KEY);
  store.removeItem(EXPIRES_KEY);
}

/**
 * Exchange credentials for a session token and persist it.
 *
 * Resolves `true` on success, `false` on a 401 (bad credentials). Other
 * failures (network, 5xx) throw so callers can surface them distinctly.
 */
export async function login(
  username: string,
  password: string,
): Promise<boolean> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (response.status === 401) {
    return false;
  }
  if (!response.ok) {
    throw new Error(`Login failed with ${response.status}`);
  }
  const body = (await response.json()) as LoginResponse;
  const store = storage();
  if (store !== null) {
    store.setItem(TOKEN_KEY, body.token);
    store.setItem(EXPIRES_KEY, String(body.expires_at));
  }
  return true;
}
