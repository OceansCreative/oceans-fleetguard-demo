"""Tests for the pure Traccar normalization functions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.traccar.normalize import (
    knots_to_mps,
    merge_readings,
    parse_time,
    to_position,
    to_vehicle,
)

from tests.traccar._helpers import (
    DEVICE_GHOST,
    DEVICE_TRUCK,
    DEVICE_VAN,
    DEVICES,
    POSITION_TRUCK,
    POSITION_VAN,
    POSITIONS,
)


def test_knots_to_mps_converts_using_the_nautical_factor() -> None:
    assert knots_to_mps(0.0) == 0.0
    assert knots_to_mps(20.0) == pytest.approx(10.28888)


def test_boolean_numeric_fields_do_not_leak_through_as_one() -> None:
    # bool is an int subclass; a stray True must coerce to 0.0, not 1.0.
    position = to_position(
        {
            "latitude": True,
            "longitude": 0,
            "speed": 0,
            "fixTime": "2026-05-29T03:00:00Z",
        }
    )
    assert position.point.lat == 0.0


def test_parse_time_handles_z_suffix_and_offsets() -> None:
    assert parse_time("2026-05-29T03:00:05Z") == datetime(
        2026, 5, 29, 3, 0, 5, tzinfo=UTC
    )
    assert parse_time("2026-05-29T03:00:00.000+00:00") == datetime(
        2026, 5, 29, 3, 0, 0, tzinfo=UTC
    )


@pytest.mark.parametrize("bad", [None, "", "not-a-date", 12345])
def test_parse_time_returns_none_for_unusable_values(bad: object) -> None:
    assert parse_time(bad) is None


def test_to_position_converts_speed_and_reads_ignition() -> None:
    position = to_position(POSITION_VAN)
    assert position.speed_mps == pytest.approx(10.28888)
    assert position.course_deg == 90.0
    assert position.ignition_on is True
    assert position.point.lat == 35.4723
    assert position.recorded_at == datetime(2026, 5, 29, 3, 0, tzinfo=UTC)


def test_to_position_uses_device_time_when_fix_time_absent() -> None:
    position = to_position(POSITION_TRUCK)
    assert position.ignition_on is False
    assert position.recorded_at == datetime(2026, 5, 29, 3, 0, 5, tzinfo=UTC)


def test_to_position_falls_back_to_motion_then_speed_for_ignition() -> None:
    from_motion = to_position(
        {
            "latitude": 0,
            "longitude": 0,
            "speed": 0,
            "fixTime": "2026-05-29T03:00:00Z",
            "attributes": {"motion": True},
        }
    )
    assert from_motion.ignition_on is True

    from_speed = to_position(
        {"latitude": 0, "longitude": 0, "speed": 5.0, "fixTime": "2026-05-29T03:00:00Z"}
    )
    assert from_speed.ignition_on is True

    stationary = to_position(
        {"latitude": 0, "longitude": 0, "speed": 0.0, "fixTime": "2026-05-29T03:00:00Z"}
    )
    assert stationary.ignition_on is False


def test_to_position_raises_without_a_timestamp() -> None:
    with pytest.raises(ValueError):
        to_position({"latitude": 0, "longitude": 0, "speed": 0})


def test_to_vehicle_maps_identity_and_leaves_home_unknown() -> None:
    vehicle = to_vehicle(DEVICE_VAN)
    assert vehicle.id == "1"
    assert vehicle.name == "Van 01"
    assert vehicle.plate == "matsue-001"  # Traccar uniqueId stands in for plate
    assert vehicle.home is None


def test_to_vehicle_falls_back_to_unique_id_when_name_blank() -> None:
    assert to_vehicle(DEVICE_TRUCK).name == "yasugi-002"


def test_merge_joins_devices_with_their_latest_positions() -> None:
    readings = merge_readings(DEVICES, POSITIONS)
    assert {r.vehicle.id for r in readings} == {"1", "2"}  # ghost dropped
    van = next(r for r in readings if r.vehicle.id == "1")
    assert van.position.ignition_on is True


def test_merge_drops_devices_without_a_position() -> None:
    readings = merge_readings([DEVICE_GHOST], POSITIONS)
    assert readings == []


def test_merge_skips_positions_without_a_device_id() -> None:
    orphan = {**POSITION_VAN, "deviceId": None}
    assert merge_readings(DEVICES, [orphan]) == []


def test_merge_keeps_the_most_recent_position_per_device() -> None:
    older = {**POSITION_VAN, "fixTime": "2026-05-29T02:00:00Z", "course": 10.0}
    newer = {**POSITION_VAN, "fixTime": "2026-05-29T04:00:00Z", "course": 99.0}
    readings = merge_readings([DEVICE_VAN], [newer, older])
    assert len(readings) == 1
    assert readings[0].position.course_deg == 99.0


def test_merge_skips_a_position_that_cannot_be_normalized() -> None:
    # A record with a deviceId but no parseable timestamp is dropped, not fatal.
    broken = {"deviceId": 1, "latitude": 1.0, "longitude": 2.0, "speed": 0.0}
    assert merge_readings([DEVICE_VAN], [broken]) == []


def test_to_position_coerces_string_and_garbage_numeric_fields() -> None:
    position = to_position(
        {
            "latitude": "35.5",  # Traccar normally sends floats; be defensive
            "longitude": "bad",  # unparseable -> treated as 0.0
            "speed": "10",
            "fixTime": "2026-05-29T03:00:00Z",
        }
    )
    assert position.point.lat == 35.5
    assert position.point.lon == 0.0
    assert position.speed_mps == pytest.approx(knots_to_mps(10.0))
