import { StrictMode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LanguageProvider } from "@/lib/i18n";
import { AlertToasts, type ActiveToast } from "./AlertToasts";

(
  globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

const TOASTS: ActiveToast[] = [
  {
    id: "t1",
    vehicleId: "v1",
    vehicleName: "Van 03",
    reason: "moving at 12.0 m/s with ignition off",
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

describe("AlertToasts", () => {
  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  it("renders nothing when there are no toasts", () => {
    render(
      <AlertToasts toasts={[]} onLocate={() => {}} onDismiss={() => {}} />,
    );
    expect(container.querySelector(".toast-stack")).toBeNull();
  });

  it("renders the vehicle name and reason", () => {
    render(
      <AlertToasts toasts={TOASTS} onLocate={() => {}} onDismiss={() => {}} />,
    );
    expect(container.textContent).toContain("Van 03");
    expect(container.textContent).toContain("ignition off");
  });

  it("calls onLocate with the vehicle id when Locate is clicked", () => {
    const onLocate = vi.fn();
    render(
      <AlertToasts toasts={TOASTS} onLocate={onLocate} onDismiss={() => {}} />,
    );
    const locate = container.querySelector(
      ".toast-btn--primary",
    ) as HTMLButtonElement;
    act(() => locate.click());
    expect(onLocate).toHaveBeenCalledWith("v1");
  });

  it("calls onDismiss with the toast id when Dismiss is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <AlertToasts toasts={TOASTS} onLocate={() => {}} onDismiss={onDismiss} />,
    );
    const buttons = container.querySelectorAll(".toast-btn");
    const dismiss = buttons[buttons.length - 1] as HTMLButtonElement;
    act(() => dismiss.click());
    expect(onDismiss).toHaveBeenCalledWith("t1");
  });
});
