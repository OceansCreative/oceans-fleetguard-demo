"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { ReactNode } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Lang = "en" | "ja";

export type MessageKey =
  | "app.title"
  | "app.sub"
  | "status.connecting"
  | "status.live"
  | "status.reconnecting"
  | "status.offline"
  | "fleet.title"
  | "fleet.vehicles"
  | "fleet.loadingMap"
  | "fleet.noVehicleSelected"
  | "fleet.ignitionOff"
  | "fleet.alerts"
  | "fleet.alertsCount"
  | "detail.plate"
  | "detail.speed"
  | "detail.heading"
  | "detail.ignition"
  | "detail.position"
  | "detail.lastUpdate"
  | "detail.geofence"
  | "detail.geofenceRadius"
  | "detail.alerts"
  | "detail.noAlerts"
  | "detail.ignitionOn"
  | "detail.ignitionOff"
  | "banner.theftAlert"
  | "banner.theftAlertPlural"
  | "banner.withActiveTheftAlerts"
  | "map.light"
  | "map.dark"
  | "map.aerial"
  | "map.aerialDisabled"
  | "map.switchLabel"
  | "list.ignOff"
  | "list.alerts"
  | "lang.toggle"
  | "auth.signOut"
  | "auth.signIn"
  | "auth.signingIn"
  | "auth.signInToContinue"
  | "auth.username"
  | "auth.password"
  | "auth.invalidCredentials"
  | "auth.serverUnreachable"
  | "history.title"
  | "history.empty"
  | "history.ago";

// ---------------------------------------------------------------------------
// Message dictionary
// ---------------------------------------------------------------------------

const messages: Record<Lang, Record<MessageKey, string>> = {
  en: {
    "app.title": "FleetGuard",
    "app.sub": "Fleet Operations",
    "status.connecting": "connecting",
    "status.live": "live",
    "status.reconnecting": "reconnecting",
    "status.offline": "offline",
    "fleet.title": "Fleet",
    "fleet.vehicles": "vehicles",
    "fleet.loadingMap": "Loading map…",
    "fleet.noVehicleSelected": "Select a vehicle to see its details.",
    "fleet.ignitionOff": "ignition off",
    "fleet.alerts": "alerts",
    "fleet.alertsCount": "alerts",
    "detail.plate": "Plate",
    "detail.speed": "Speed",
    "detail.heading": "Heading",
    "detail.ignition": "Ignition",
    "detail.position": "Position",
    "detail.lastUpdate": "Last update",
    "detail.geofence": "Geofence",
    "detail.geofenceRadius": "radius",
    "detail.alerts": "Alerts",
    "detail.noAlerts": "No active alerts.",
    "detail.ignitionOn": "on",
    "detail.ignitionOff": "off",
    "banner.theftAlert": "vehicle with active theft alerts",
    "banner.theftAlertPlural": "vehicles with active theft alerts",
    "banner.withActiveTheftAlerts": "with active theft alerts",
    "map.light": "Light",
    "map.dark": "Dark",
    "map.aerial": "Aerial",
    "map.aerialDisabled":
      "Aerial requires a provider URL (NEXT_PUBLIC_MAP_AERIAL_URL)",
    "map.switchLabel": "Basemap style",
    "list.ignOff": "ign off",
    "list.alerts": "alerts",
    "lang.toggle": "日本語",
    "auth.signOut": "Sign out",
    "auth.signIn": "Sign in",
    "auth.signingIn": "Signing in…",
    "auth.signInToContinue": "Sign in to continue",
    "auth.username": "Username",
    "auth.password": "Password",
    "auth.invalidCredentials": "Incorrect username or password.",
    "auth.serverUnreachable": "Could not reach the server. Please try again.",
    "history.title": "Alert History",
    "history.empty": "No alerts recorded yet.",
    "history.ago": "ago",
  },
  ja: {
    "app.title": "FleetGuard",
    "app.sub": "フリート管理",
    "status.connecting": "接続中",
    "status.live": "ライブ",
    "status.reconnecting": "再接続中",
    "status.offline": "オフライン",
    "fleet.title": "フリート",
    "fleet.vehicles": "台",
    "fleet.loadingMap": "地図を読み込み中…",
    "fleet.noVehicleSelected": "車両を選択すると詳細が表示されます。",
    "fleet.ignitionOff": "エンジン停止",
    "fleet.alerts": "アラート",
    "fleet.alertsCount": "件のアラート",
    "detail.plate": "ナンバー",
    "detail.speed": "速度",
    "detail.heading": "方向",
    "detail.ignition": "エンジン",
    "detail.position": "位置",
    "detail.lastUpdate": "最終更新",
    "detail.geofence": "ジオフェンス",
    "detail.geofenceRadius": "半径",
    "detail.alerts": "アラート",
    "detail.noAlerts": "アクティブなアラートはありません。",
    "detail.ignitionOn": "オン",
    "detail.ignitionOff": "オフ",
    "banner.theftAlert": "台に盗難アラートがあります",
    "banner.theftAlertPlural": "台に盗難アラートがあります",
    "banner.withActiveTheftAlerts": "に盗難アラートがあります",
    "map.light": "ライト",
    "map.dark": "ダーク",
    "map.aerial": "航空写真",
    "map.aerialDisabled":
      "航空写真はプロバイダ設定が必要 (NEXT_PUBLIC_MAP_AERIAL_URL)",
    "map.switchLabel": "ベースマップ",
    "list.ignOff": "エンジン停止",
    "list.alerts": "件のアラート",
    "lang.toggle": "EN",
    "auth.signOut": "サインアウト",
    "auth.signIn": "サインイン",
    "auth.signingIn": "サインイン中…",
    "auth.signInToContinue": "続行するにはサインイン",
    "auth.username": "ユーザー名",
    "auth.password": "パスワード",
    "auth.invalidCredentials": "ユーザー名またはパスワードが正しくありません。",
    "auth.serverUnreachable":
      "サーバーに接続できませんでした。もう一度お試しください。",
    "history.title": "アラート履歴",
    "history.empty": "アラートの記録はまだありません。",
    "history.ago": "前",
  },
};

// ---------------------------------------------------------------------------
// Storage & detection helpers
// ---------------------------------------------------------------------------

const STORAGE_KEY = "fleetguard.lang";

function detectLang(): Lang {
  // Guard SSR: typeof window may be undefined during prerender
  if (typeof window === "undefined") return "en";
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "en" || stored === "ja") return stored;
  } catch {
    // localStorage may be blocked (private browsing restrictions)
  }
  const nav = navigator.language ?? "";
  return nav.startsWith("ja") ? "ja" : "en";
}

function persistLang(lang: Lang): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // ignore write errors
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface LangContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: MessageKey) => string;
}

const LangContext = createContext<LangContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function LanguageProvider({
  children,
}: {
  children: ReactNode;
}): React.JSX.Element {
  const [lang, setLangState] = useState<Lang>("en");

  // Run detection only on the client after mount to avoid SSR mismatch
  useEffect(() => {
    setLangState(detectLang());
  }, []);

  const setLang = useCallback((next: Lang) => {
    persistLang(next);
    setLangState(next);
  }, []);

  const t = useCallback(
    (key: MessageKey): string => {
      const dict = messages[lang];
      // Fall back to English if key is somehow absent in the active lang
      return dict[key] ?? messages["en"][key] ?? key;
    },
    [lang],
  );

  return (
    <LangContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LangContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useLang(): Pick<LangContextValue, "lang" | "setLang"> {
  const ctx = useContext(LangContext);
  if (ctx === null) {
    throw new Error("useLang must be used within a LanguageProvider");
  }
  return { lang: ctx.lang, setLang: ctx.setLang };
}

export function useT(): LangContextValue["t"] {
  const ctx = useContext(LangContext);
  if (ctx === null) {
    throw new Error("useT must be used within a LanguageProvider");
  }
  return ctx.t;
}
