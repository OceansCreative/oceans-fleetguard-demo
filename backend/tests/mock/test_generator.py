"""Tests for the deterministic mock fleet simulation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.detection.geo import haversine_m
from app.mock.generator import DEFAULT_FLEET, MockFleet

START = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)


def test_initial_samples_have_no_previous_and_are_stationary() -> None:
    fleet = MockFleet(start_time=START)
    samples = fleet.samples()
    assert len(samples) == len(DEFAULT_FLEET)
    assert all(sample.previous is None for sample in samples)
    assert all(sample.current.speed_mps == 0.0 for sample in samples)


def test_step_records_previous_and_advances_time() -> None:
    fleet = MockFleet(start_time=START)
    moment = START + timedelta(seconds=2)
    fleet.step(2.0, moment)
    for sample in fleet.samples():
        assert sample.previous is not None
        assert sample.current.recorded_at == moment


def test_simulation_is_deterministic_for_a_given_seed() -> None:
    one = MockFleet(start_time=START, seed=7)
    two = MockFleet(start_time=START, seed=7)
    for _ in range(5):
        one.step(2.0, START)
        two.step(2.0, START)
    points_one = [(s.current.point.lat, s.current.point.lon) for s in one.samples()]
    points_two = [(s.current.point.lat, s.current.point.lon) for s in two.samples()]
    assert points_one == points_two


def test_suspicious_vehicle_moves_with_ignition_off() -> None:
    fleet = MockFleet(start_time=START)
    fleet.step(2.0, START)
    suspicious = next(s for s in fleet.samples() if s.vehicle.id == "v-005")
    assert suspicious.current.ignition_on is False
    assert suspicious.current.speed_mps > 0.0


def test_normal_vehicles_keep_ignition_on() -> None:
    fleet = MockFleet(start_time=START)
    fleet.step(2.0, START)
    normals = [s for s in fleet.samples() if s.vehicle.id != "v-005"]
    assert all(sample.current.ignition_on for sample in normals)


def test_normal_vehicle_stays_near_home_over_many_steps() -> None:
    fleet = MockFleet(start_time=START, seed=1)
    for _ in range(200):
        fleet.step(2.0, START)
    van = next(s for s in fleet.samples() if s.vehicle.id == "v-001")
    assert haversine_m(van.current.point, van.vehicle.home) < 4_000.0
