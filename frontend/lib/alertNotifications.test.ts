import { describe, expect, it } from "vitest";

import { criticalVehicleIds, newCriticalAlerts } from "./alertNotifications";
import type { AlertSeverity, Vehicle } from "./types";

function makeVehicle(id: string, severities: AlertSeverity[]): Vehicle {
  return {
    id,
    name: `Vehicle ${id}`,
    plate: `plate-${id}`,
    position: {
      lat: 35.47,
      lon: 133.05,
      speed_mps: 0,
      course_deg: 0,
      ignition_on: false,
      recorded_at: "2026-05-27T12:00:00Z",
    },
    geofence: null,
    alerts: severities.map((severity) => ({
      type: "ignition_off_movement",
      severity,
      reason: `${severity} on ${id}`,
    })),
  };
}

describe("criticalVehicleIds", () => {
  it("collects only vehicles with a critical alert", () => {
    const vehicles = [
      makeVehicle("v1", ["critical"]),
      makeVehicle("v2", ["warning"]),
      makeVehicle("v3", []),
      makeVehicle("v4", ["info", "critical"]),
    ];
    expect(criticalVehicleIds(vehicles)).toEqual(new Set(["v1", "v4"]));
  });

  it("returns an empty set when nothing is critical", () => {
    expect(criticalVehicleIds([makeVehicle("v1", ["warning"])]).size).toBe(0);
  });
});

describe("newCriticalAlerts", () => {
  it("reports a vehicle that just became critical", () => {
    const fresh = newCriticalAlerts(new Set(), [
      makeVehicle("v1", ["critical"]),
    ]);
    expect(fresh).toEqual([
      { vehicleId: "v1", vehicleName: "Vehicle v1", reason: "critical on v1" },
    ]);
  });

  it("does not re-report a vehicle that was already critical", () => {
    const fresh = newCriticalAlerts(new Set(["v1"]), [
      makeVehicle("v1", ["critical"]),
    ]);
    expect(fresh).toEqual([]);
  });

  it("reports a recovered-then-reoffending vehicle afresh", () => {
    // prevIds does not include v1 (it had recovered), and it is critical again.
    const fresh = newCriticalAlerts(new Set(["v2"]), [
      makeVehicle("v1", ["critical"]),
    ]);
    expect(fresh.map((a) => a.vehicleId)).toEqual(["v1"]);
  });

  it("ignores non-critical vehicles", () => {
    const fresh = newCriticalAlerts(new Set(), [
      makeVehicle("v1", ["warning"]),
      makeVehicle("v2", []),
    ]);
    expect(fresh).toEqual([]);
  });

  it("uses the first critical alert's reason", () => {
    const vehicle = makeVehicle("v1", ["critical"]);
    vehicle.alerts = [
      { type: "geofence_breach", severity: "critical", reason: "first" },
      { type: "abnormal_speed", severity: "critical", reason: "second" },
    ];
    expect(newCriticalAlerts(new Set(), [vehicle])[0]?.reason).toBe("first");
  });
});
