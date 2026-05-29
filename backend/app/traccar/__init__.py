"""A thin relay that normalizes a live Traccar feed into the fleet domain.

The HTTP plumbing lives in :mod:`app.traccar.client`; the value-adding logic —
turning Traccar's JSON into our domain objects — lives in
:mod:`app.traccar.normalize` as pure functions that are trivial to test.
"""

from __future__ import annotations

from app.traccar.client import TraccarClient
from app.traccar.source import TraccarSource

__all__ = ["TraccarClient", "TraccarSource"]
