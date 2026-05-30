/** Shared severity → color mapping for markers, badges, and lists. */

import type { AlertSeverity } from "@/lib/types";

export const SEVERITY_COLOR: Record<AlertSeverity, string> = {
  critical: "#ef4d54",
  warning: "#f59e0b",
  info: "#3b82f6",
};

export const CALM_COLOR = "#22c55e";
