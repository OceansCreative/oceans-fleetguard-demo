"""Pydantic response schemas and converters from internal domain objects."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.detection.models import Alert, Position
from app.mock.generator import VehicleSample


class PositionOut(BaseModel):
    """A normalized position for API responses."""

    lat: float
    lon: float
    speed_mps: float
    course_deg: float
    ignition_on: bool
    recorded_at: datetime

    @classmethod
    def from_position(cls, position: Position) -> PositionOut:
        return cls(
            lat=position.point.lat,
            lon=position.point.lon,
            speed_mps=position.speed_mps,
            course_deg=position.course_deg,
            ignition_on=position.ignition_on,
            recorded_at=position.recorded_at,
        )


class AlertOut(BaseModel):
    """A fired detection alert for API responses."""

    type: str
    severity: str
    reason: str

    @classmethod
    def from_alert(cls, alert: Alert) -> AlertOut:
        return cls(type=alert.type, severity=alert.severity, reason=alert.reason)


class VehicleOut(BaseModel):
    """A vehicle with its latest position and any active alerts."""

    id: str
    name: str
    plate: str
    position: PositionOut
    alerts: list[AlertOut]

    @classmethod
    def from_sample(cls, sample: VehicleSample, alerts: list[Alert]) -> VehicleOut:
        return cls(
            id=sample.vehicle.id,
            name=sample.vehicle.name,
            plate=sample.vehicle.plate,
            position=PositionOut.from_position(sample.current),
            alerts=[AlertOut.from_alert(alert) for alert in alerts],
        )
