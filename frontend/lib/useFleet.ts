"use client";

/** React hook: seed the fleet over REST, then keep it live over WebSocket. */

import { useEffect, useRef, useState } from "react";

import { fetchVehicles, UnauthorizedError } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { API_KEY, WS_BASE_URL } from "@/lib/config";
import { connectLive, type SocketStatus } from "@/lib/liveSocket";
import { parsePositions } from "@/lib/parse";
import type { Vehicle } from "@/lib/types";

export type ConnectionState = SocketStatus;

export interface FleetState {
  vehicles: Vehicle[];
  connection: ConnectionState;
}

export interface UseFleetOptions {
  /** Called when a REST seed is rejected with 401 (session missing/expired). */
  onUnauthorized?: () => void;
}

/** Build the `/ws/positions` URL, attaching the optional key and token gates. */
export function buildWsUrl(): string {
  const params = new URLSearchParams();
  if (API_KEY) {
    params.set("key", API_KEY);
  }
  const token = getToken();
  if (token !== null) {
    params.set("token", token);
  }
  const query = params.toString();
  return `${WS_BASE_URL}/ws/positions${query ? `?${query}` : ""}`;
}

export function useFleet(options: UseFleetOptions = {}): FleetState {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  // Keep the latest callback in a ref so the connect effect stays mount-once.
  const onUnauthorizedRef = useRef(options.onUnauthorized);
  onUnauthorizedRef.current = options.onUnauthorized;

  useEffect(() => {
    const controller = new AbortController();
    // The socket sends a snapshot on connect, which can beat the REST seed.
    // Once a live frame has landed, drop the (now staler) REST response so it
    // can't flash older positions over the live ones.
    let liveReceived = false;

    fetchVehicles(controller.signal)
      .then((seed) => {
        if (!liveReceived) {
          setVehicles(seed);
        }
      })
      .catch((error: unknown) => {
        if (error instanceof UnauthorizedError) {
          onUnauthorizedRef.current?.();
        }
        /* Otherwise the WebSocket delivers the first snapshot if REST fails. */
      });

    const wsUrl = buildWsUrl();
    const live = connectLive({
      url: wsUrl,
      onStatus: setConnection,
      onMessage: (data) => {
        try {
          const next = parsePositions(JSON.parse(data as string));
          if (next !== null) {
            liveReceived = true;
            setVehicles(next);
          }
        } catch {
          /* Ignore malformed frames. */
        }
      },
    });

    return () => {
      controller.abort();
      live.close();
    };
  }, []);

  return { vehicles, connection };
}
