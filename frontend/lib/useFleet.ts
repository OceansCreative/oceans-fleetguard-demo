"use client";

/** React hook: seed the fleet over REST, then keep it live over WebSocket. */

import { useEffect, useState } from "react";

import { fetchVehicles } from "@/lib/api";
import { WS_BASE_URL } from "@/lib/config";
import { connectLive, type SocketStatus } from "@/lib/liveSocket";
import { parsePositions } from "@/lib/parse";
import type { Vehicle } from "@/lib/types";

export type ConnectionState = SocketStatus;

export interface FleetState {
  vehicles: Vehicle[];
  connection: ConnectionState;
}

export function useFleet(): FleetState {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");

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
      .catch(() => {
        /* WebSocket will deliver the first snapshot if REST is unavailable. */
      });

    const live = connectLive({
      url: `${WS_BASE_URL}/ws/positions`,
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
