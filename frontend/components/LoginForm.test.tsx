import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageProvider } from "@/lib/i18n";
import { LoginForm } from "./LoginForm";

// Tell React this is a unit-test environment so act(...) is supported.
(
  globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

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

function setInput(name: string, value: string): void {
  const input = container.querySelector<HTMLInputElement>(
    `input[name="${name}"]`,
  );
  if (input === null) {
    throw new Error(`missing input ${name}`);
  }
  const setter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype,
    "value",
  )?.set;
  setter?.call(input, value);
  act(() => {
    input.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

async function submit(): Promise<void> {
  const form = container.querySelector("form");
  await act(async () => {
    form?.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true }),
    );
  });
}

describe("LoginForm", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });
  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    localStorage.clear();
  });

  it("posts credentials and calls onAuthed on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        token: "jwt.value",
        expires_at: Math.floor(Date.now() / 1000) + 600,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const onAuthed = vi.fn();

    render(<LoginForm onAuthed={onAuthed} />);
    setInput("username", "admin");
    setInput("password", "hunter2");
    await submit();

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/api/auth/login");
    expect(JSON.parse(init.body as string)).toEqual({
      username: "admin",
      password: "hunter2",
    });
    expect(onAuthed).toHaveBeenCalledOnce();
    expect(localStorage.getItem("fleetguard.auth.token")).toBe("jwt.value");
  });

  it("shows an error and does not transition on bad credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 }),
    );
    const onAuthed = vi.fn();

    render(<LoginForm onAuthed={onAuthed} />);
    setInput("username", "admin");
    setInput("password", "wrong");
    await submit();

    expect(onAuthed).not.toHaveBeenCalled();
    expect(container.querySelector(".login-error")?.textContent).toMatch(
      /incorrect/i,
    );
  });
});
