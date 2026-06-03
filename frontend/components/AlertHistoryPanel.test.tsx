import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageProvider } from "@/lib/i18n";
import { AlertHistoryPanel } from "./AlertHistoryPanel";
import type { AlertHistoryEntry } from "@/lib/types";

// Tell React this is a unit-test environment so act(...) is supported.
(
  globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const SAMPLE_ENTRIES: AlertHistoryEntry[] = [
  {
    vehicle_id: "v-001",
    vehicle_name: "Truck Alpha",
    alert_type: "geofence_breach",
    alert_severity: "critical",
    alert_reason: "Vehicle left the designated zone",
    lat: 35.6762,
    lon: 139.6503,
    recorded_at: new Date(Date.now() - 90_000).toISOString(), // 1.5 min ago
  },
  {
    vehicle_id: "v-002",
    vehicle_name: "Van Beta",
    alert_type: "abnormal_speed",
    alert_severity: "warning",
    alert_reason: "Speed exceeded 120 km/h",
    lat: 35.6895,
    lon: 139.6917,
    recorded_at: new Date(Date.now() - 3_600_000).toISOString(), // 1 hr ago
  },
];

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

describe("AlertHistoryPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.useRealTimers();
  });

  it("renders the section title", () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue({ ok: true, status: 200, json: async () => [] }),
    );

    render(<AlertHistoryPanel />);

    expect(container.textContent).toMatch(/alert history/i);
  });

  it("shows empty state when there are no entries", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AlertHistoryPanel />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(container.textContent).toMatch(/no alerts recorded/i);
  });

  it("renders alert history entries with vehicle name, severity badge, and reason", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => SAMPLE_ENTRIES,
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AlertHistoryPanel />);

    await act(async () => {
      await Promise.resolve();
    });

    const text = container.textContent ?? "";
    expect(text).toContain("Truck Alpha");
    expect(text).toContain("Van Beta");
    expect(text).toContain("Vehicle left the designated zone");
    expect(text).toContain("Speed exceeded 120 km/h");

    // Severity badges
    const badges = container.querySelectorAll(".badge");
    expect(badges.length).toBe(2);
    const badgeTexts = Array.from(badges).map((b) => b.textContent);
    expect(badgeTexts).toContain("critical");
    expect(badgeTexts).toContain("warning");
  });

  it("auto-refreshes by fetching again after 10 seconds", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AlertHistoryPanel />);

    await act(async () => {
      await Promise.resolve();
    });

    // StrictMode double-invokes effects in dev, so capture the baseline count
    const baselineCount = fetchMock.mock.calls.length;
    expect(baselineCount).toBeGreaterThanOrEqual(1);

    await act(async () => {
      vi.advanceTimersByTime(10_000);
      await Promise.resolve();
    });

    // At least one additional call should have been made after the interval
    expect(fetchMock.mock.calls.length).toBeGreaterThan(baselineCount);
  });

  it("renders border-left colour reflecting alert severity", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [SAMPLE_ENTRIES[0]],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<AlertHistoryPanel />);

    await act(async () => {
      await Promise.resolve();
    });

    const card = container.querySelector<HTMLElement>(".history-card");
    expect(card?.style.borderLeftColor).toBeTruthy();
  });
});
