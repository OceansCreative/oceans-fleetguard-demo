"use client";

/** React hook: seed the fleet over REST, then keep it live over WebSocket. */

import { useEffect, useState } from "react";

import { fetchVehicles } from "@/lib/api";
import { WS_BASE_URL } from "@/lib/config";
import { parsePositions } from "@/lib/parse";
import type { Vehicle } from "@/lib/types";

export type ConnectionState = "connecting" | "live" | "offline";

export interface FleetState {
  vehicles: Vehicle[];
  connection: ConnectionState;
}

export function useFleet(): FleetState {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");

  useEffect(() => {
    const controller = new AbortController();
    fetchVehicles(controller.signal)
      .then(setVehicles)
      .catch(() => {
        /* WebSocket will deliver the first snapshot if REST is unavailable. */
      });

    const socket = new WebSocket(`${WS_BASE_URL}/ws/positions`);
    socket.onopen = () => setConnection("live");
    socket.onclose = () => setConnection("offline");
    socket.onerror = () => setConnection("offline");
    socket.onmessage = (event: MessageEvent<string>) => {
      try {
        const next = parsePositions(JSON.parse(event.data));
        if (next !== null) {
          setVehicles(next);
        }
      } catch {
        /* Ignore malformed frames. */
      }
    };

    return () => {
      controller.abort();
      socket.close();
    };
  }, []);

  return { vehicles, connection };
}
