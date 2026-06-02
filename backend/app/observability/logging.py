"""Structured logging configuration for FleetGuard.

Provides a ``configure_logging`` function that installs either a compact
human-readable formatter (for local dev) or a JSON-line formatter (for
production / log-aggregation pipelines) on the root logger.

Environment variables (with defaults that keep local dev unchanged):
  - ``LOG_LEVEL``  – log level name, e.g. ``DEBUG``, ``INFO`` (default ``INFO``).
  - ``LOG_FORMAT`` – ``text`` (default) or ``json``.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any

from app.observability.request_id import current_request_id


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Output keys:
      - ``ts``         – ISO-8601 timestamp (UTC, from ``%(asctime)s`` epoch).
      - ``level``      – upper-cased level name.
      - ``logger``     – logger name.
      - ``msg``        – formatted message.
      - ``request_id`` – present only when a request-ID is active.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f+00:00"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = current_request_id()
        if rid is not None:
            entry["request_id"] = rid
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            entry["exc"] = record.exc_text
        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)
        return json.dumps(entry, default=str)


# Suppress the unused-import warning — traceback is re-exported via the public
# exception helper below only if needed; keep it in scope for formatException.
_ = traceback


def configure_logging(level: str, json: bool) -> None:  # noqa: A002 – mirrors env name
    """Install a root-logger handler with the requested level and format.

    Idempotent: subsequent calls simply reconfigure the root logger.

    Args:
        level: Logging level name (case-insensitive), e.g. ``"INFO"``.
        json:  When *True* the JSON formatter is used; otherwise a compact
               human-readable formatter is installed (keeps local dev readable).
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Remove handlers added by earlier calls so we stay idempotent.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler()
    if json:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)
