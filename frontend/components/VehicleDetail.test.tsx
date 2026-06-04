import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { LanguageProvider } from "@/lib/i18n";
import { SpeedSparkline, VehicleDetail } from "./VehicleDetail";
import type { Vehicle } from "@/lib/types";

let container: HTMLDivElement;
let root: Root;

function render(node: React.ReactNode): void {
  act(() => {
    root.render(
      <StrictMode>
        <LanguageProvider>{node}</LanguageProvider>
      </StrictMode>,
    );
  });
}

const SAMPLE_VEHICLE: Vehicle = {
  id: "v-001",
  name: "Van Alpha",
  plate: "ABC-123",
  position: {
    lat: 35.47,
    lon: 133.05,
    speed_mps: 12.5,
    course_deg: 45,
    ignition_on: true,
    recorded_at: "2026-05-27T12:00:00Z",
  },
  geofence: null,
  alerts: [],
};

describe("SpeedSparkline", () => {
  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("renders an SVG with a zero-baseline line for empty samples", () => {
    render(<SpeedSparkline samples={[]} />);
    const svg = container.querySelector("svg.sparkline");
    expect(svg).not.toBeNull();
    // Empty state uses a dashed zero line instead of a polyline
    const zeroline = container.querySelector("line.sparkline-zero");
    expect(zeroline).not.toBeNull();
    const polyline = container.querySelector("polyline.sparkline-line");
    expect(polyline).toBeNull();
  });

  it("renders a polyline for a single sample without crashing", () => {
    render(<SpeedSparkline samples={[10]} />);
    const polyline = container.querySelector("polyline.sparkline-line");
    expect(polyline).not.toBeNull();
    // The latest-value dot should also appear
    const dot = container.querySelector("circle.sparkline-dot");
    expect(dot).not.toBeNull();
  });

  it("renders a polyline with correct number of coordinate pairs for multi-sample data", () => {
    const samples = [5, 10, 8, 15, 12];
    render(<SpeedSparkline samples={samples} />);
    const polyline = container.querySelector("polyline.sparkline-line");
    expect(polyline).not.toBeNull();
    const pointsAttr = polyline?.getAttribute("points") ?? "";
    // Each sample produces one "x,y" pair separated by spaces.
    const pairs = pointsAttr.trim().split(/\s+/);
    expect(pairs).toHaveLength(samples.length);
  });

  it("renders an area fill path alongside the polyline", () => {
    render(<SpeedSparkline samples={[4, 8, 6]} />);
    const area = container.querySelector("path.sparkline-area");
    expect(area).not.toBeNull();
    // The path's d attribute should be non-empty.
    expect(area?.getAttribute("d")).not.toBe("");
  });
});

describe("VehicleDetail", () => {
  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("renders the empty state when vehicle is null", () => {
    render(<VehicleDetail vehicle={null} />);
    expect(container.textContent).toMatch(/select a vehicle/i);
  });

  it("renders vehicle name and plate", () => {
    render(<VehicleDetail vehicle={SAMPLE_VEHICLE} />);
    expect(container.textContent).toContain("Van Alpha");
    expect(container.textContent).toContain("ABC-123");
  });

  it("renders the sparkline section label", () => {
    render(<VehicleDetail vehicle={SAMPLE_VEHICLE} speedSamples={[5, 10]} />);
    // The localized label for "detail.speedRecent" in English is "Speed (recent)"
    expect(container.textContent).toMatch(/speed \(recent\)/i);
  });

  it("renders a sparkline SVG when speedSamples are provided", () => {
    render(
      <VehicleDetail vehicle={SAMPLE_VEHICLE} speedSamples={[5, 10, 8]} />,
    );
    const svg = container.querySelector("svg.sparkline");
    expect(svg).not.toBeNull();
  });

  it("renders an empty sparkline when speedSamples is not provided", () => {
    render(<VehicleDetail vehicle={SAMPLE_VEHICLE} />);
    const svg = container.querySelector("svg.sparkline");
    expect(svg).not.toBeNull();
    // Default empty state: dashed zero line
    const zeroline = container.querySelector("line.sparkline-zero");
    expect(zeroline).not.toBeNull();
  });
});
