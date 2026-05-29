/** Thin REST client for the FleetGuard backend. */

import { API_BASE_URL } from "@/lib/config";
import type { Vehicle } from "@/lib/types";

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
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
