import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildHeaders, fetchVehicles, UnauthorizedError } from "./api";

const TOKEN_KEY = "fleetguard.auth.token";
const EXPIRES_KEY = "fleetguard.auth.expiresAt";

function storeValidToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(
    EXPIRES_KEY,
    String(Math.floor(Date.now() / 1000) + 600),
  );
}

describe("api auth headers", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    localStorage.clear();
  });

  it("omits the bearer header when no token is stored", () => {
    expect(buildHeaders()["Authorization"]).toBeUndefined();
  });

  it("attaches the bearer header when a token is stored", () => {
    storeValidToken("jwt.token.here");
    expect(buildHeaders()["Authorization"]).toBe("Bearer jwt.token.here");
  });

  it("sends the bearer header on a REST request", async () => {
    storeValidToken("jwt.token.here");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [],
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchVehicles();

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer jwt.token.here");
  });

  it("raises UnauthorizedError on a 401 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 }),
    );
    await expect(fetchVehicles()).rejects.toBeInstanceOf(UnauthorizedError);
  });
});
