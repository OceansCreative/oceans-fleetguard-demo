import type { AlertSeverity } from "@/lib/types";

export function AlertBadge({
  severity,
  children,
}: {
  severity: AlertSeverity;
  children: React.ReactNode;
}): React.JSX.Element {
  return <span className={`badge badge--${severity}`}>{children}</span>;
}
