import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAlertHistory, UnauthorizedError } from "./api";
import type { AlertHistoryEntry } from "./types";

const SAMPLE_ENTRY: AlertHistoryEntry = {
  vehicle_id: "v-001",
  vehicle_name: "Truck Alpha",
  alert_type: "geofence_breach",
  alert_severity: "critical",
  alert_reason: "Vehicle left the designated zone",
  lat: 35.6762,
  lon: 139.6503,
  recorded_at: "2024-01-15T10:30:00Z",
};

describe("fetchAlertHistory", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    localStorage.clear();
  });

  it("calls GET /api/alerts/history without limit param when limit is omitted", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [SAMPLE_ENTRY],
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchAlertHistory();

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toMatch(/\/api\/alerts\/history$/);
    expect(url).not.toContain("limit=");
  });

  it("appends ?limit=N when a limit is provided", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchAlertHistory(5);

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("?limit=5");
  });

  it("attaches buildHeaders on the request", async () => {
    localStorage.setItem("fleetguard.auth.token", "tok123");
    localStorage.setItem(
      "fleetguard.auth.expiresAt",
      String(Math.floor(Date.now() / 1000) + 600),
    );
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchAlertHistory();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer tok123");
  });

  it("parses and returns alert history entries", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [SAMPLE_ENTRY],
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchAlertHistory();

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual(SAMPLE_ENTRY);
    expect(result[0]?.vehicle_id).toBe("v-001");
    expect(result[0]?.vehicle_name).toBe("Truck Alpha");
    expect(result[0]?.alert_severity).toBe("critical");
  });

  it("raises UnauthorizedError on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 }),
    );

    await expect(fetchAlertHistory()).rejects.toBeInstanceOf(UnauthorizedError);
  });
});
