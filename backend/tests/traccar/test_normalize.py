"""Tests for the pure Traccar normalization functions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.sources.base import VehicleSample
from app.traccar.normalize import (
    apply_positions,
    geofences_by_id,
    knots_to_mps,
    merge_readings,
    parse_circular_geofence,
    parse_time,
    roster_from_devices,
    to_position,
    to_vehicle,
)

from tests.traccar._helpers import (
    DEVICE_GHOST,
    DEVICE_TRUCK,
    DEVICE_VAN,
    DEVICES,
    GEOFENCES,
    POSITION_TRUCK,
    POSITION_VAN,
    POSITIONS,
)


def test_knots_to_mps_converts_using_the_nautical_factor() -> None:
    assert knots_to_mps(0.0) == 0.0
    assert knots_to_mps(20.0) == pytest.approx(10.28888)


def test_boolean_numeric_fields_do_not_leak_through_as_one() -> None:
    # bool is an int subclass; a stray True on a non-positional field (speed,
    # course) must coerce to 0.0, not 1.0.
    position = to_position(
        {
            "latitude": 1.0,
            "longitude": 2.0,
            "speed": True,
            "course": True,
            "fixTime": "2026-05-29T03:00:00Z",
        }
    )
    assert position.speed_mps == 0.0
    assert position.course_deg == 0.0


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


def test_parse_time_pins_zoneless_timestamps_to_utc() -> None:
    # A timestamp with no offset must come back tz-aware (UTC), not naive, so it
    # stays comparable with the aware timestamps Traccar usually sends.
    parsed = parse_time("2026-05-29T03:00:00")
    assert parsed == datetime(2026, 5, 29, 3, 0, tzinfo=UTC)
    assert parsed is not None and parsed.tzinfo is not None


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


def test_to_vehicle_maps_identity_and_leaves_geofence_unknown() -> None:
    vehicle = to_vehicle(DEVICE_VAN)
    assert vehicle.id == "1"
    assert vehicle.name == "Van 01"
    assert vehicle.plate == "matsue-001"  # Traccar uniqueId stands in for plate
    assert vehicle.geofence is None


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


def test_merge_handles_mixed_aware_and_naive_timestamps() -> None:
    # One device reporting both an aware and a zone-less timestamp must not crash
    # the recency comparison (it used to raise TypeError); the later wins.
    aware = {**POSITION_VAN, "fixTime": "2026-05-29T03:00:00Z", "course": 1.0}
    naive = {**POSITION_VAN, "fixTime": "2026-05-29T04:00:00", "course": 2.0}
    readings = merge_readings([DEVICE_VAN], [aware, naive])
    assert len(readings) == 1
    assert readings[0].position.course_deg == 2.0


def test_to_position_coerces_numeric_strings() -> None:
    position = to_position(
        {
            "latitude": "35.5",  # Traccar normally sends floats; be defensive
            "longitude": "133.05",
            "speed": "10",
            "fixTime": "2026-05-29T03:00:00Z",
        }
    )
    assert position.point.lat == 35.5
    assert position.point.lon == 133.05
    assert position.speed_mps == pytest.approx(knots_to_mps(10.0))


def test_to_position_zeroes_a_garbage_speed_but_keeps_the_fix() -> None:
    # speed is non-positional: a garbage value degrades to 0.0 rather than
    # dropping the whole (still placeable) position.
    position = to_position(
        {
            "latitude": 35.5,
            "longitude": 133.05,
            "speed": "fast",
            "fixTime": "2026-05-29T03:00:00Z",
        }
    )
    assert position.speed_mps == 0.0
    assert position.point.lat == 35.5


@pytest.mark.parametrize(
    "coords",
    [
        {},  # both absent
        {"latitude": 35.5},  # longitude absent
        {"longitude": 133.05},  # latitude absent
        {"latitude": "bad", "longitude": 133.05},  # unparseable latitude
        {"latitude": 35.5, "longitude": None},  # explicit null
        {"latitude": True, "longitude": 133.05},  # bool is not a coordinate
    ],
)
def test_to_position_drops_records_without_usable_coordinates(
    coords: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        to_position({**coords, "speed": 0, "fixTime": "2026-05-29T03:00:00Z"})


def test_to_position_keeps_legitimate_zero_coordinates() -> None:
    # A device genuinely on the equator / prime meridian reports (0, 0); that is
    # real data and must be kept, unlike a missing coordinate.
    position = to_position(
        {"latitude": 0, "longitude": 0.0, "speed": 0, "fixTime": "2026-05-29T03:00:00Z"}
    )
    assert position.point.lat == 0.0
    assert position.point.lon == 0.0


def test_merge_drops_a_position_with_missing_coordinates() -> None:
    no_coords = {"deviceId": 1, "speed": 0.0, "fixTime": "2026-05-29T03:00:00Z"}
    assert merge_readings([DEVICE_VAN], [no_coords]) == []


def test_merge_skips_devices_without_an_id() -> None:
    # An id-less device can't be keyed; it must be skipped, not surfaced as
    # vehicle id "None" (which would alias every id-less device together).
    idless = {"uniqueId": "u9", "geofenceIds": []}
    readings = merge_readings([idless, DEVICE_VAN], [POSITION_VAN])
    assert {r.vehicle.id for r in readings} == {"1"}


def test_roster_from_devices_skips_devices_without_an_id() -> None:
    roster = roster_from_devices([{"uniqueId": "u9"}, DEVICE_VAN])
    assert set(roster) == {"1"}  # no "None" key for the id-less device


def test_roster_from_devices_keys_identities_by_device_id() -> None:
    roster = roster_from_devices(DEVICES)
    assert set(roster) == {"1", "2", "3"}
    assert roster["1"].name == "Van 01"
    assert roster["2"].name == "yasugi-002"  # blank name -> uniqueId


def test_apply_positions_seeds_then_tracks_previous() -> None:
    roster = roster_from_devices([DEVICE_VAN])

    first = apply_positions(roster, {}, [POSITION_VAN])
    assert set(first) == {"1"}
    assert first["1"].previous is None  # first sighting has no history
    assert first["1"].vehicle.name == "Van 01"

    moved = {**POSITION_VAN, "course": 123.0, "fixTime": "2026-05-29T03:05:00Z"}
    second = apply_positions(roster, first, [moved])
    assert second["1"].current.course_deg == 123.0
    assert second["1"].previous is not None
    assert second["1"].previous.course_deg == 90.0


def test_apply_positions_leaves_untouched_devices_in_place() -> None:
    roster = roster_from_devices(DEVICES)
    seeded = apply_positions(roster, {}, POSITIONS)  # van + truck
    # A frame that only mentions the van must not drop the truck.
    updated = apply_positions(roster, seeded, [{**POSITION_VAN, "course": 45.0}])
    assert set(updated) == {"1", "2"}
    assert updated["2"] is seeded["2"]


def test_apply_positions_does_not_mutate_the_input_cache() -> None:
    roster = roster_from_devices([DEVICE_VAN])
    before: dict[str, VehicleSample] = {}
    apply_positions(roster, before, [POSITION_VAN])
    assert before == {}  # the input mapping is left untouched


def test_apply_positions_falls_back_for_unknown_devices() -> None:
    # Position arrives before the roster knows the device.
    result = apply_positions({}, {}, [POSITION_VAN])
    assert result["1"].vehicle.id == "1"
    assert result["1"].vehicle.name == "1"
    assert result["1"].vehicle.geofence is None


def test_apply_positions_skips_malformed_or_orphan_records() -> None:
    roster = roster_from_devices([DEVICE_VAN])
    no_device = {**POSITION_VAN, "deviceId": None}
    no_time = {"deviceId": 1, "latitude": 1.0, "longitude": 2.0, "speed": 0.0}
    assert apply_positions(roster, {}, [no_device, no_time]) == {}


def test_parse_circular_geofence_reads_lat_lon_radius() -> None:
    circle = parse_circular_geofence("CIRCLE (35.4723 133.0505, 500)")
    assert circle is not None
    assert circle.center.lat == 35.4723
    assert circle.center.lon == 133.0505
    assert circle.radius_m == 500.0


@pytest.mark.parametrize(
    "area",
    [
        None,
        42,
        "POLYGON ((35.47 133.05, 35.48 133.06, 35.47 133.05))",
        "LINESTRING (35.47 133.05, 35.48 133.06)",
        "garbage",
    ],
)
def test_parse_circular_geofence_ignores_non_circles(area: object) -> None:
    assert parse_circular_geofence(area) is None


def test_geofences_by_id_keeps_only_circles() -> None:
    lookup = geofences_by_id(GEOFENCES)
    assert set(lookup) == {"10"}  # polygon dropped
    assert lookup["10"].radius_m == 500.0


def test_to_vehicle_attaches_an_assigned_circular_geofence() -> None:
    vehicle = to_vehicle(DEVICE_VAN, geofences_by_id(GEOFENCES))
    assert vehicle.geofence is not None
    assert vehicle.geofence.radius_m == 500.0


def test_to_vehicle_has_no_geofence_when_device_assigns_none() -> None:
    # DEVICE_TRUCK carries no geofenceIds.
    assert to_vehicle(DEVICE_TRUCK, geofences_by_id(GEOFENCES)).geofence is None


def test_to_vehicle_ignores_geofence_ids_with_no_circular_match() -> None:
    # The device is assigned only the polygon geofence (id 11), which is dropped
    # from the circle lookup, so _pick_geofence must scan its ids and still
    # fall through to None rather than attach a non-circular fence.
    device = {**DEVICE_VAN, "geofenceIds": [11]}
    assert to_vehicle(device, geofences_by_id(GEOFENCES)).geofence is None


def test_merge_readings_attaches_geofences() -> None:
    readings = merge_readings(DEVICES, POSITIONS, geofences_by_id(GEOFENCES))
    van = next(r for r in readings if r.vehicle.id == "1")
    assert van.vehicle.geofence is not None


def test_roster_from_devices_attaches_geofences() -> None:
    roster = roster_from_devices(DEVICES, geofences_by_id(GEOFENCES))
    assert roster["1"].geofence is not None
    assert roster["2"].geofence is None
