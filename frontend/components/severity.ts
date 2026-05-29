/** Shared severity → color mapping for markers, badges, and lists. */

import type { AlertSeverity } from "@/lib/types";

export const SEVERITY_COLOR: Record<AlertSeverity, string> = {
  critical: "#dc2626",
  warning: "#d97706",
  info: "#2563eb",
};

export const CALM_COLOR = "#16a34a";
