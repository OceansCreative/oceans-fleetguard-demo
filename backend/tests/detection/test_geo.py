"""Tests for the pure geospatial helpers."""

from __future__ import annotations

import pytest
from app.detection.geo import angular_difference_deg, haversine_m
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
