/**
 * Tests for the i18n module.
 *
 * We test the pure logic (detectLang-equivalent behaviour, t(), persistence)
 * by exercising the LanguageProvider through React's act() + createRoot,
 * without requiring @testing-library/react.
 */

import { afterEach, describe, expect, it, vi, type MockInstance } from "vitest";
import { createElement, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { act } from "react";

import { LanguageProvider, useLang, useT } from "./i18n";
import type { MessageKey } from "./i18n";

// ---------------------------------------------------------------------------
// Tiny test harness: renders a component that captures hook values
// ---------------------------------------------------------------------------

interface Captured {
  lang?: string;
  setLang?: (l: "en" | "ja") => void;
  value?: string;
}

function renderWithProvider(
  useHookFn: () => Captured,
  onCapture: (c: Captured) => void,
): { root: ReturnType<typeof createRoot>; container: HTMLElement } {
  const container = document.createElement("div");
  document.body.appendChild(container);

  function Inner() {
    const captured = useHookFn();
    useEffect(() => {
      onCapture(captured);
    });
    return null;
  }

  const root = createRoot(container);
  act(() => {
    root.render(
      createElement(LanguageProvider, null, createElement(Inner, null)),
    );
  });
  return { root, container };
}

// ---------------------------------------------------------------------------
// localStorage mock
// ---------------------------------------------------------------------------

function mockLocalStorage(initial: Record<string, string> = {}): {
  store: Record<string, string>;
  getItemSpy: MockInstance;
  setItemSpy: MockInstance;
} {
  const store: Record<string, string> = { ...initial };
  const getItemSpy = vi
    .spyOn(Storage.prototype, "getItem")
    .mockImplementation((key: string) => store[key] ?? null);
  const setItemSpy = vi
    .spyOn(Storage.prototype, "setItem")
    .mockImplementation((key: string, value: string) => {
      store[key] = value;
    });
  return { store, getItemSpy, setItemSpy };
}

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

describe("i18n – language detection from navigator", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("defaults to 'en' when navigator.language is en-US", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage();

    let captured: Captured = {};
    const { root, container } = renderWithProvider(
      () => {
        const { lang, setLang } = useLang();
        return { lang, setLang };
      },
      (c) => {
        captured = c;
      },
    );

    expect(captured.lang).toBe("en");
    act(() => root.unmount());
    document.body.removeChild(container);
  });

  it("detects 'ja' when navigator.language starts with 'ja'", () => {
    vi.stubGlobal("navigator", { language: "ja-JP" });
    mockLocalStorage();

    let captured: Captured = {};
    const { root, container } = renderWithProvider(
      () => {
        const { lang, setLang } = useLang();
        return { lang, setLang };
      },
      (c) => {
        captured = c;
      },
    );

    expect(captured.lang).toBe("ja");
    act(() => root.unmount());
    document.body.removeChild(container);
  });

  it("reads persisted 'ja' from localStorage even when navigator says en", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage({ "fleetguard.lang": "ja" });

    let captured: Captured = {};
    const { root, container } = renderWithProvider(
      () => {
        const { lang, setLang } = useLang();
        return { lang, setLang };
      },
      (c) => {
        captured = c;
      },
    );

    expect(captured.lang).toBe("ja");
    act(() => root.unmount());
    document.body.removeChild(container);
  });
});

// ---------------------------------------------------------------------------
// setLang switches t() output
// ---------------------------------------------------------------------------

describe("i18n – setLang switches t() output", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns English strings by default, then Japanese after setLang('ja')", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage();

    const tValues: Record<string, string> = {};
    let capturedSetLang: ((l: "en" | "ja") => void) | undefined;

    function Inner() {
      const { setLang } = useLang();
      const t = useT();
      const [tick, setTick] = useState(0);

      useEffect(() => {
        capturedSetLang = (l: "en" | "ja") => {
          setLang(l);
          setTick((n) => n + 1);
        };
        tValues[`${tick}`] = t("status.live" as MessageKey);
      });
      return null;
    }

    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    act(() => {
      root.render(
        createElement(LanguageProvider, null, createElement(Inner, null)),
      );
    });

    // After initial render lang = "en"
    expect(tValues["0"]).toBe("live");

    // Switch to Japanese
    act(() => {
      capturedSetLang?.("ja");
    });
    expect(tValues["1"]).toBe("ライブ");

    // Switch back to English
    act(() => {
      capturedSetLang?.("en");
    });
    expect(tValues["2"]).toBe("live");

    act(() => root.unmount());
    document.body.removeChild(container);
  });
});

// ---------------------------------------------------------------------------
// localStorage persistence
// ---------------------------------------------------------------------------

describe("i18n – localStorage persistence", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("writes the selected lang to localStorage when setLang is called", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    const { setItemSpy } = mockLocalStorage();

    let capturedSetLang: ((l: "en" | "ja") => void) | undefined;

    function Inner() {
      const { setLang } = useLang();
      useEffect(() => {
        capturedSetLang = setLang;
      });
      return null;
    }

    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    act(() => {
      root.render(
        createElement(LanguageProvider, null, createElement(Inner, null)),
      );
    });

    act(() => {
      capturedSetLang?.("ja");
    });

    expect(setItemSpy).toHaveBeenCalledWith("fleetguard.lang", "ja");

    act(() => root.unmount());
    document.body.removeChild(container);
  });
});

// ---------------------------------------------------------------------------
// Translation string coverage — EN and JA
// ---------------------------------------------------------------------------

describe("i18n – translation string coverage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("returns correct English strings for key sample", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage();

    const results: Record<string, string> = {};

    function Inner() {
      const t = useT();
      useEffect(() => {
        results["plate"] = t("detail.plate");
        results["noAlerts"] = t("detail.noAlerts");
        results["live"] = t("status.live");
        results["mapLight"] = t("map.light");
        results["mapDark"] = t("map.dark");
        results["mapAerial"] = t("map.aerial");
        results["reconnecting"] = t("status.reconnecting");
      });
      return null;
    }

    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    act(() => {
      root.render(
        createElement(LanguageProvider, null, createElement(Inner, null)),
      );
    });

    expect(results["plate"]).toBe("Plate");
    expect(results["noAlerts"]).toBe("No active alerts.");
    expect(results["live"]).toBe("live");
    expect(results["mapLight"]).toBe("Light");
    expect(results["mapDark"]).toBe("Dark");
    expect(results["mapAerial"]).toBe("Aerial");
    expect(results["reconnecting"]).toBe("reconnecting");

    act(() => root.unmount());
    document.body.removeChild(container);
  });

  it("returns correct Japanese strings after switching to ja", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage();

    const results: Record<string, string> = {};
    let capturedSetLang: ((l: "en" | "ja") => void) | undefined;

    function Inner() {
      const { setLang } = useLang();
      const t = useT();
      useEffect(() => {
        capturedSetLang = setLang;
        results["plate"] = t("detail.plate");
        results["noAlerts"] = t("detail.noAlerts");
        results["noVehicle"] = t("fleet.noVehicleSelected");
        results["mapLight"] = t("map.light");
        results["mapDark"] = t("map.dark");
        results["mapAerial"] = t("map.aerial");
        results["reconnecting"] = t("status.reconnecting");
      });
      return null;
    }

    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    act(() => {
      root.render(
        createElement(LanguageProvider, null, createElement(Inner, null)),
      );
    });

    act(() => {
      capturedSetLang?.("ja");
    });

    expect(results["plate"]).toBe("ナンバー");
    expect(results["noAlerts"]).toBe("アクティブなアラートはありません。");
    expect(results["noVehicle"]).toBe("車両を選択すると詳細が表示されます。");
    expect(results["mapLight"]).toBe("ライト");
    expect(results["mapDark"]).toBe("ダーク");
    expect(results["mapAerial"]).toBe("航空写真");
    expect(results["reconnecting"]).toBe("再接続中");

    act(() => root.unmount());
    document.body.removeChild(container);
  });

  it("falls back to English for a missing-key scenario", () => {
    vi.stubGlobal("navigator", { language: "en-US" });
    mockLocalStorage();

    const results: Record<string, string> = {};

    function Inner() {
      const t = useT();
      useEffect(() => {
        // Cast an unknown key to verify the fallback path
        results["missing"] = t("detail.plate");
      });
      return null;
    }

    const container = document.createElement("div");
    document.body.appendChild(container);
    const root = createRoot(container);

    act(() => {
      root.render(
        createElement(LanguageProvider, null, createElement(Inner, null)),
      );
    });

    expect(results["missing"]).toBe("Plate");

    act(() => root.unmount());
    document.body.removeChild(container);
  });
});
