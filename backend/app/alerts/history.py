"""In-memory, bounded alert history recorder.

Records a timestamped entry whenever a (vehicle, alert_type) pair transitions
into the active state — identical dedup logic as CriticalAlertNotifier but
covering ALL severities.  Entries are stored newest-first on access.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from app.api.schemas import VehicleOut

_DEFAULT_MAXLEN = 200


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AlertHistoryEntry:
    """One recorded alert-activation event."""

    __slots__ = (
        "vehicle_id",
        "vehicle_name",
        "alert_type",
        "alert_severity",
        "alert_reason",
        "lat",
        "lon",
        "recorded_at",
    )

    def __init__(
        self,
        *,
        vehicle_id: str,
        vehicle_name: str,
        alert_type: str,
        alert_severity: str,
        alert_reason: str,
        lat: float,
        lon: float,
        recorded_at: datetime,
    ) -> None:
        self.vehicle_id = vehicle_id
        self.vehicle_name = vehicle_name
        self.alert_type = alert_type
        self.alert_severity = alert_severity
        self.alert_reason = alert_reason
        self.lat = lat
        self.lon = lon
        self.recorded_at = recorded_at


def _scan_vehicles(
    vehicles: Sequence[VehicleOut],
    now: datetime,
) -> dict[tuple[str, str], AlertHistoryEntry]:
    """Build a map of currently-active (vehicle_id, alert_type) -> entry.

    All entries share the same *now* timestamp — the clock is sampled once per
    tick, not once per alert, so an injected test clock advances predictably.
    """
    result: dict[tuple[str, str], AlertHistoryEntry] = {}
    for vehicle in vehicles:
        for alert in vehicle.alerts:
            key = (vehicle.id, alert.type)
            result[key] = AlertHistoryEntry(
                vehicle_id=vehicle.id,
                vehicle_name=vehicle.name,
                alert_type=alert.type,
                alert_severity=alert.severity,
                alert_reason=alert.reason,
                lat=vehicle.position.lat,
                lon=vehicle.position.lon,
                recorded_at=now,
            )
    return result


def _new_entries(
    current: dict[tuple[str, str], AlertHistoryEntry],
    active: set[tuple[str, str]],
) -> list[AlertHistoryEntry]:
    """Return entries whose keys just became active (absent from *active*)."""
    newly_active = set(current.keys()) - active
    return [current[key] for key in sorted(newly_active)]


class AlertHistory:
    """Bounded in-memory log of alert activation events.

    ``now`` is injectable for deterministic tests.  ``maxlen`` caps the buffer;
    once full the oldest entry is silently dropped (deque semantics).
    """

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
        maxlen: int = _DEFAULT_MAXLEN,
    ) -> None:
        self._now = now or _utcnow
        self._buf: deque[AlertHistoryEntry] = deque(maxlen=maxlen)
        self._active: set[tuple[str, str]] = set()

    def record(self, vehicles: Sequence[VehicleOut]) -> None:
        """Append one entry per (vehicle, alert_type) that just became active.

        The clock is sampled once per call so all new entries in the same tick
        share an identical timestamp, and an injected clock advances exactly
        once per ``record()`` invocation.
        """
        ts = self._now()
        current = _scan_vehicles(vehicles, ts)
        for entry in _new_entries(current, self._active):
            self._buf.appendleft(entry)
        self._active = set(current.keys())

    def entries(self, limit: int | None = None) -> list[AlertHistoryEntry]:
        """Return entries newest-first, optionally capped to *limit*."""
        result = list(self._buf)
        if limit is not None:
            result = result[:limit]
        return result
