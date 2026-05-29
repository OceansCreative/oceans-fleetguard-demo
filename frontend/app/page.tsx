import { formatSpeedKmh } from "@/lib/format";

export default function HomePage(): React.JSX.Element {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>🛰️ FleetGuard</h1>
      <p>
        Open-source Traccar-powered fleet tracking &amp; anti-theft dashboard.
      </p>
      <p>
        Backend health and the live map will appear here. Example speed
        formatting: <strong>{formatSpeedKmh(16.7)}</strong>.
      </p>
    </main>
  );
}
