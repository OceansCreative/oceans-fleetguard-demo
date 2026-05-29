import { describe, expect, it } from "vitest";

import { formatSpeedKmh } from "./format";

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
