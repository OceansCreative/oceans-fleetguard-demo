"""Readiness state for the /ready probe.

A lightweight flag that ``main.py`` sets once the fleet service has started
and produced its first snapshot. The ``/ready`` endpoint returns 503 until
``ReadinessState.mark_ready()`` is called.

This lives in its own module so it can be tested without the full ASGI app.
"""

from __future__ import annotations

import threading


class ReadinessState:
    """Thread-safe readiness flag."""

    def __init__(self) -> None:
        self._ready = False
        self._lock = threading.Lock()

    def mark_ready(self) -> None:
        """Signal that the application is ready to serve traffic."""
        with self._lock:
            self._ready = True

    def is_ready(self) -> bool:
        """Return *True* once :meth:`mark_ready` has been called."""
        with self._lock:
            return self._ready
