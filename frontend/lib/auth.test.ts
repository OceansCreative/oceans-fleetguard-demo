import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getToken, isAuthed, login, logout } from "./auth";

const TOKEN_KEY = "fleetguard.auth.token";
const EXPIRES_KEY = "fleetguard.auth.expiresAt";

function farFuture(): number {
  return Math.floor(Date.now() / 1000) + 3600;
}

describe("auth token storage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    // Default benign fetch; individual tests override it as needed. logout()
    // fires a best-effort backend call, so a stub keeps tests offline.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      }),
    );
  });
  afterEach(() => {
    localStorage.clear();
  });

  it("reports no token when storage is empty", () => {
    expect(getToken()).toBeNull();
    expect(isAuthed()).toBe(false);
  });

  it("login stores the token and expiry, isAuthed becomes true", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ token: "jwt.abc.def", expires_at: farFuture() }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const ok = await login("admin", "hunter2");

    expect(ok).toBe(true);
    expect(localStorage.getItem(TOKEN_KEY)).toBe("jwt.abc.def");
    expect(getToken()).toBe("jwt.abc.def");
    expect(isAuthed()).toBe(true);
    // It POSTed JSON credentials to the login endpoint, including cookies so
    // the backend's httpOnly session cookie is accepted.
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({
      username: "admin",
      password: "hunter2",
    });
  });

  it("login returns false and stores nothing on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 }),
    );
    const ok = await login("admin", "wrong");
    expect(ok).toBe(false);
    expect(getToken()).toBeNull();
  });

  it("login throws on a server error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500 }),
    );
    await expect(login("admin", "x")).rejects.toThrow();
  });

  it("logout clears the stored token and asks the backend to drop the cookie", () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem(TOKEN_KEY, "jwt");
    localStorage.setItem(EXPIRES_KEY, String(farFuture()));
    expect(isAuthed()).toBe(true);

    logout();

    expect(getToken()).toBeNull();
    expect(isAuthed()).toBe(false);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/auth/logout");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
  });

  it("treats an expired token as absent and clears it", () => {
    localStorage.setItem(TOKEN_KEY, "jwt");
    localStorage.setItem(
      EXPIRES_KEY,
      String(Math.floor(Date.now() / 1000) - 10),
    );
    expect(getToken()).toBeNull();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });
});
