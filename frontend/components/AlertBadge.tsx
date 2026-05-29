import type { AlertSeverity } from "@/lib/types";
import { SEVERITY_COLOR } from "@/components/severity";

export function AlertBadge({
  severity,
  children,
}: {
  severity: AlertSeverity;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <span
      style={{
        background: SEVERITY_COLOR[severity],
        color: "white",
        borderRadius: "9999px",
        padding: "0.1rem 0.5rem",
        fontSize: "0.7rem",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.03em",
      }}
    >
      {children}
    </span>
  );
}
