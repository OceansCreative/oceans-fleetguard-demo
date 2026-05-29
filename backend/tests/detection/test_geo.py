"""Tests for the pure geospatial helpers."""

from __future__ import annotations

import pytest
from app.detection.geo import (
    angular_difference_deg,
    destination_point,
    haversine_m,
    offset_point,
)
from app.detection.models import GeoPoint

# Matsue Castle and Yonago Station, ~25 km apart.
MATSUE = GeoPoint(lat=35.4750, lon=133.0505)
YONAGO = GeoPoint(lat=35.4280, lon=133.3310)


def test_haversine_is_zero_for_identical_points() -> None:
    assert haversine_m(MATSUE, MATSUE) == pytest.approx(0.0, abs=1e-6)


def test_haversine_is_symmetric() -> None:
    assert haversine_m(MATSUE, YONAGO) == pytest.approx(haversine_m(YONAGO, MATSUE))


def test_haversine_matsue_to_yonago_is_about_25km() -> None:
    assert haversine_m(MATSUE, YONAGO) == pytest.approx(25_700, rel=0.05)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (0.0, 0.0, 0.0),
        (10.0, 350.0, 20.0),  # wraparound across 0/360
        (350.0, 10.0, 20.0),
        (0.0, 180.0, 180.0),  # opposite directions
        (0.0, 270.0, 90.0),  # takes the shorter arc
        (90.0, 90.0, 0.0),
    ],
)
def test_angular_difference(a: float, b: float, expected: float) -> None:
    assert angular_difference_deg(a, b) == pytest.approx(expected)


def test_offset_point_moves_the_expected_distance() -> None:
    moved = offset_point(MATSUE, north_m=1_000.0, east_m=0.0)
    assert haversine_m(MATSUE, moved) == pytest.approx(1_000.0, rel=0.01)
    assert moved.lat > MATSUE.lat  # moved north


def test_destination_point_respects_bearing_and_distance() -> None:
    east = destination_point(MATSUE, bearing_deg=90.0, distance_m=500.0)
    assert haversine_m(MATSUE, east) == pytest.approx(500.0, rel=0.01)
    assert east.lon > MATSUE.lon  # due east increases longitude


def test_destination_point_north_increases_latitude() -> None:
    north = destination_point(MATSUE, bearing_deg=0.0, distance_m=500.0)
    assert north.lat > MATSUE.lat
    assert north.lon == pytest.approx(MATSUE.lon)
