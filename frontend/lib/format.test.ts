import { describe, expect, it } from "vitest";

import { formatSpeedKmh, highestSeverity, sortByUrgency } from "./format";
import type { Vehicle } from "./types";

function vehicle(
  id: string,
  name: string,
  severities: Vehicle["alerts"][number]["severity"][],
): Vehicle {
  return {
    id,
    name,
    plate: `plate-${id}`,
    position: {
      lat: 35.47,
      lon: 133.05,
      speed_mps: 10,
      course_deg: 0,
      ignition_on: true,
      recorded_at: "2026-05-27T12:00:00Z",
    },
    alerts: severities.map((severity) => ({
      type: "abnormal_speed",
      severity,
      reason: "test",
    })),
  };
}

describe("formatSpeedKmh", () => {
  it("converts m/s to rounded km/h", () => {
    expect(formatSpeedKmh(10)).toBe("36 km/h");
    expect(formatSpeedKmh(16.7)).toBe("60 km/h");
  });

  it("treats zero as a valid stationary speed", () => {
    expect(formatSpeedKmh(0)).toBe("0 km/h");
  });

  it("returns an em dash for negative or non-finite input", () => {
    expect(formatSpeedKmh(-1)).toBe("—");
    expect(formatSpeedKmh(Number.NaN)).toBe("—");
    expect(formatSpeedKmh(Number.POSITIVE_INFINITY)).toBe("—");
  });
});

describe("highestSeverity", () => {
  it("returns null when there are no alerts", () => {
    expect(highestSeverity(vehicle("1", "A", []))).toBeNull();
  });

  it("picks the most urgent severity", () => {
    expect(
      highestSeverity(vehicle("1", "A", ["info", "critical", "warning"])),
    ).toBe("critical");
    expect(highestSeverity(vehicle("1", "A", ["info", "warning"]))).toBe(
      "warning",
    );
  });
});

describe("sortByUrgency", () => {
  it("orders critical before warning before none, then by name", () => {
    const calm = vehicle("1", "Bravo", []);
    const warn = vehicle("2", "Charlie", ["warning"]);
    const crit = vehicle("3", "Alpha", ["critical"]);
    const result = sortByUrgency([calm, warn, crit]).map((v) => v.id);
    expect(result).toEqual(["3", "2", "1"]);
  });

  it("breaks ties by name and does not mutate the input", () => {
    const input = [vehicle("1", "Zulu", []), vehicle("2", "Alpha", [])];
    const result = sortByUrgency(input);
    expect(result.map((v) => v.name)).toEqual(["Alpha", "Zulu"]);
    expect(input.map((v) => v.name)).toEqual(["Zulu", "Alpha"]);
  });
});
