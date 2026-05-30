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
    <span className="badge" style={{ background: SEVERITY_COLOR[severity] }}>
      {children}
    </span>
  );
}
