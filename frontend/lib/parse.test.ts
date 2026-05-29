import { describe, expect, it } from "vitest";

import { parsePositions } from "./parse";
import type { Vehicle } from "./types";

const sample: Vehicle = {
  id: "v-001",
  name: "Van 01",
  plate: "p",
  position: {
    lat: 35.47,
    lon: 133.05,
    speed_mps: 10,
    course_deg: 0,
    ignition_on: true,
    recorded_at: "2026-05-27T12:00:00Z",
  },
  geofence: null,
  alerts: [],
};

describe("parsePositions", () => {
  it("extracts the vehicles array from a valid message", () => {
    expect(parsePositions({ vehicles: [sample] })).toEqual([sample]);
  });

  it("returns an empty array for an empty fleet", () => {
    expect(parsePositions({ vehicles: [] })).toEqual([]);
  });

  it("returns null for malformed payloads", () => {
    expect(parsePositions(null)).toBeNull();
    expect(parsePositions(42)).toBeNull();
    expect(parsePositions({})).toBeNull();
    expect(parsePositions({ vehicles: "nope" })).toBeNull();
  });
});
