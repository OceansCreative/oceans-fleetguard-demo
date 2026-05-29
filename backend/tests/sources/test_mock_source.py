"""Tests for the MockSource adapter over the simulation."""

from __future__ import annotations

from datetime import UTC, datetime

from app.mock.generator import MockFleet
from app.sources.base import FleetSource
from app.sources.mock_source import MockSource

START = datetime(2026, 5, 27, 12, 0, tzinfo=UTC)


def test_mock_source_satisfies_the_fleet_source_protocol() -> None:
    source = MockSource(MockFleet(start_time=START))
    assert isinstance(source, FleetSource)


def test_advance_steps_the_underlying_simulation() -> None:
    source = MockSource(MockFleet(start_time=START))
    assert all(s.previous is None for s in source.snapshot())
    source.advance(2.0, START)
    assert all(s.previous is not None for s in source.snapshot())


def test_close_is_a_harmless_no_op() -> None:
    source = MockSource(MockFleet(start_time=START))
    source.close()  # must not raise
    assert source.snapshot()  # still usable
