import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "FleetGuard",
  description:
    "Open-source Traccar-powered fleet tracking & anti-theft dashboard.",
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}): React.JSX.Element {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
