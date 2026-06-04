import { describe, expect, it } from "vitest";

import { appendPositionSample, type PositionHistory } from "./positionHistory";
import type { Vehicle } from "./types";

function makeVehicle(id: string, lon: number, lat: number): Vehicle {
  return {
    id,
    name: `Vehicle ${id}`,
    plate: `plate-${id}`,
    position: {
      lat,
      lon,
      speed_mps: 10,
      course_deg: 0,
      ignition_on: true,
      recorded_at: "2026-05-27T12:00:00Z",
    },
    geofence: null,
    alerts: [],
  };
}

describe("appendPositionSample", () => {
  it("appends a [lon, lat] point for each vehicle", () => {
    const prev: PositionHistory = {};
    const vehicles = [
      makeVehicle("v1", 133.05, 35.47),
      makeVehicle("v2", 133.1, 35.5),
    ];
    const next = appendPositionSample(prev, vehicles, 40);
    expect(next["v1"]).toEqual([[133.05, 35.47]]);
    expect(next["v2"]).toEqual([[133.1, 35.5]]);
  });

  it("accumulates points across multiple frames", () => {
    let history: PositionHistory = {};
    history = appendPositionSample(history, [makeVehicle("v1", 1, 1)], 40);
    history = appendPositionSample(history, [makeVehicle("v1", 2, 2)], 40);
    history = appendPositionSample(history, [makeVehicle("v1", 3, 3)], 40);
    expect(history["v1"]).toEqual([
      [1, 1],
      [2, 2],
      [3, 3],
    ]);
  });

  it("collapses a consecutive duplicate point (stationary vehicle)", () => {
    let history: PositionHistory = {};
    history = appendPositionSample(history, [makeVehicle("v1", 5, 5)], 40);
    history = appendPositionSample(history, [makeVehicle("v1", 5, 5)], 40);
    history = appendPositionSample(history, [makeVehicle("v1", 5, 5)], 40);
    expect(history["v1"]).toEqual([[5, 5]]);
  });

  it("caps the buffer at `cap` points, discarding the oldest", () => {
    let history: PositionHistory = {};
    for (let i = 0; i < 45; i++) {
      history = appendPositionSample(history, [makeVehicle("v1", i, i)], 40);
    }
    const buf = history["v1"];
    expect(buf).toHaveLength(40);
    expect(buf?.[0]).toEqual([5, 5]);
    expect(buf?.[39]).toEqual([44, 44]);
  });

  it("prunes ids that are no longer in the vehicles list", () => {
    let history: PositionHistory = {
      v1: [[1, 1]],
      v2: [[2, 2]],
    };
    history = appendPositionSample(history, [makeVehicle("v1", 3, 3)], 40);
    expect(Object.keys(history)).toEqual(["v1"]);
    expect(history["v1"]).toEqual([
      [1, 1],
      [3, 3],
    ]);
  });

  it("does not mutate the input history object", () => {
    const prev: PositionHistory = { v1: [[1, 1]] };
    const original = prev["v1"];
    appendPositionSample(prev, [makeVehicle("v1", 2, 2)], 40);
    expect(prev["v1"]).toBe(original); // same reference — not mutated
  });

  it("handles an empty vehicles list (clears the history)", () => {
    const prev: PositionHistory = { v1: [[1, 1]] };
    const next = appendPositionSample(prev, [], 40);
    expect(Object.keys(next)).toHaveLength(0);
  });
});
