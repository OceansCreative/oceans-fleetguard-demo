/** Shared severity → color mapping for markers, badges, and lists. */

import type { AlertSeverity } from "@/lib/types";

export const SEVERITY_COLOR: Record<AlertSeverity, string> = {
  critical: "#fb5566",
  warning: "#f6a609",
  info: "#38bdf8",
};

export const CALM_COLOR = "#34d399";
