"""Pure geospatial helpers used by the detection rules."""

from __future__ import annotations

import math

from app.detection.models import GeoPoint

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    """Great-circle distance between two points in meters.

    Uses the haversine formula; accurate enough for fleet-scale distances.
    """
    lat1, lon1, lat2, lon2 = (
        math.radians(a.lat),
        math.radians(a.lon),
        math.radians(b.lat),
        math.radians(b.lon),
    )
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def angular_difference_deg(a_deg: float, b_deg: float) -> float:
    """Smallest absolute difference between two bearings, in ``[0, 180]``.

    Handles wraparound, e.g. 350° vs 10° -> 20°.
    """
    diff = abs(a_deg - b_deg) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


# Meters per degree of latitude (roughly constant across the globe).
_M_PER_DEG_LAT = 111_320.0


def offset_point(origin: GeoPoint, north_m: float, east_m: float) -> GeoPoint:
    """Return ``origin`` shifted by the given north/east offsets in meters.

    A local flat-earth approximation; accurate at fleet scale.
    """
    d_lat = north_m / _M_PER_DEG_LAT
    d_lon = east_m / (_M_PER_DEG_LAT * math.cos(math.radians(origin.lat)))
    return GeoPoint(lat=origin.lat + d_lat, lon=origin.lon + d_lon)


def destination_point(
    origin: GeoPoint, bearing_deg: float, distance_m: float
) -> GeoPoint:
    """Return the point ``distance_m`` from ``origin`` along ``bearing_deg``.

    Bearing is measured clockwise from north.
    """
    bearing = math.radians(bearing_deg)
    return offset_point(
        origin,
        north_m=distance_m * math.cos(bearing),
        east_m=distance_m * math.sin(bearing),
    )
