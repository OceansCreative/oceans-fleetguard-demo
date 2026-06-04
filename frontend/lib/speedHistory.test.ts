import { describe, expect, it } from "vitest";

import { appendSpeedSample, type SpeedHistory } from "./speedHistory";
import type { Vehicle } from "./types";

function makeVehicle(id: string, speed: number): Vehicle {
  return {
    id,
    name: `Vehicle ${id}`,
    plate: `plate-${id}`,
    position: {
      lat: 35.47,
      lon: 133.05,
      speed_mps: speed,
      course_deg: 0,
      ignition_on: true,
      recorded_at: "2026-05-27T12:00:00Z",
    },
    geofence: null,
    alerts: [],
  };
}

describe("appendSpeedSample", () => {
  it("appends a speed sample for each vehicle", () => {
    const prev: SpeedHistory = {};
    const vehicles = [makeVehicle("v1", 10), makeVehicle("v2", 5)];
    const next = appendSpeedSample(prev, vehicles, 30);
    expect(next["v1"]).toEqual([10]);
    expect(next["v2"]).toEqual([5]);
  });

  it("accumulates samples across multiple calls", () => {
    let history: SpeedHistory = {};
    const vehicles = [makeVehicle("v1", 10)];
    history = appendSpeedSample(history, vehicles, 30);
    history = appendSpeedSample(history, [makeVehicle("v1", 20)], 30);
    history = appendSpeedSample(history, [makeVehicle("v1", 30)], 30);
    expect(history["v1"]).toEqual([10, 20, 30]);
  });

  it("caps the buffer at `cap` samples, discarding the oldest", () => {
    let history: SpeedHistory = {};
    for (let i = 0; i < 35; i++) {
      history = appendSpeedSample(history, [makeVehicle("v1", i)], 30);
    }
    const buf = history["v1"];
    expect(buf).toHaveLength(30);
    // The oldest samples (0–4) should have been dropped.
    expect(buf?.[0]).toBe(5);
    expect(buf?.[29]).toBe(34);
  });

  it("prunes ids that are no longer in the vehicles list", () => {
    let history: SpeedHistory = {
      v1: [10, 20],
      v2: [5, 6],
    };
    // Only v1 remains in the next frame.
    history = appendSpeedSample(history, [makeVehicle("v1", 30)], 30);
    expect(Object.keys(history)).toEqual(["v1"]);
    expect(history["v1"]).toEqual([10, 20, 30]);
  });

  it("does not mutate the input history object", () => {
    const prev: SpeedHistory = { v1: [1, 2, 3] };
    const original = prev["v1"];
    appendSpeedSample(prev, [makeVehicle("v1", 4)], 30);
    expect(prev["v1"]).toBe(original); // same reference — not mutated
  });

  it("handles an empty vehicles list (clears the history)", () => {
    const prev: SpeedHistory = { v1: [10, 20] };
    const next = appendSpeedSample(prev, [], 30);
    expect(Object.keys(next)).toHaveLength(0);
  });
});
