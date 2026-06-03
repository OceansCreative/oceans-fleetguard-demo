/** Thin REST client for the FleetGuard backend. */

import { getToken } from "@/lib/auth";
import { API_BASE_URL, API_KEY } from "@/lib/config";
import type { AlertHistoryEntry, Vehicle } from "@/lib/types";

/** Raised when a request is rejected by an auth gate (HTTP 401). */
export class UnauthorizedError extends Error {
  constructor(path: string) {
    super(`Request to ${path} was unauthorized`);
    this.name = "UnauthorizedError";
  }
}

/**
 * Build request headers, attaching the optional shared API key (`X-API-Key`)
 * and the optional user session token (`Authorization: Bearer`). The two gates
 * are independent: each header is added only when its value is present.
 */
export function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  const token = getToken();
  if (token !== null) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const headers = buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, { signal, headers });
  if (response.status === 401) {
    throw new UnauthorizedError(path);
  }
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchVehicles(signal?: AbortSignal): Promise<Vehicle[]> {
  return getJson<Vehicle[]>("/api/vehicles", signal);
}

export function fetchVehicle(
  id: string,
  signal?: AbortSignal,
): Promise<Vehicle> {
  return getJson<Vehicle>(`/api/vehicles/${id}`, signal);
}

export function fetchAlertHistory(
  limit?: number,
  signal?: AbortSignal,
): Promise<AlertHistoryEntry[]> {
  const path =
    limit !== undefined
      ? `/api/alerts/history?limit=${limit}`
      : "/api/alerts/history";
  return getJson<AlertHistoryEntry[]>(path, signal);
}
