/** Shared API types mirroring the backend's Pydantic response schemas. */

export type AlertSeverity = "info" | "warning" | "critical";

export type AlertType =
  | "geofence_breach"
  | "off_hours_movement"
  | "ignition_off_movement"
  | "abnormal_speed"
  | "abnormal_heading";

export interface VehicleAlert {
  type: AlertType;
  severity: AlertSeverity;
  reason: string;
}

export interface VehiclePosition {
  lat: number;
  lon: number;
  speed_mps: number;
  course_deg: number;
  ignition_on: boolean;
  recorded_at: string;
}

/** A vehicle's circular geofence (center + radius in meters). */
export interface VehicleGeofence {
  lat: number;
  lon: number;
  radius_m: number;
}

export interface Vehicle {
  id: string;
  name: string;
  plate: string;
  position: VehiclePosition;
  geofence: VehicleGeofence | null;
  alerts: VehicleAlert[];
}

/** Shape of the WebSocket broadcast payload from `/ws/positions`. */
export interface PositionsMessage {
  vehicles: Vehicle[];
}
