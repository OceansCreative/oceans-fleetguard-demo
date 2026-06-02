"""Tests for the structured JSON logging formatter."""

from __future__ import annotations

import json
import logging

from app.observability.logging import _JsonFormatter, configure_logging
from app.observability.request_id import _request_id_var


def _make_record(msg: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


class TestJsonFormatter:
    def test_emits_required_keys(self) -> None:
        fmt = _JsonFormatter()
        record = _make_record("test message")
        line = fmt.format(record)
        data = json.loads(line)
        assert set(data.keys()) >= {"ts", "level", "logger", "msg"}

    def test_msg_matches_record_message(self) -> None:
        fmt = _JsonFormatter()
        record = _make_record("my log line")
        data = json.loads(fmt.format(record))
        assert data["msg"] == "my log line"

    def test_level_is_upper_case_name(self) -> None:
        fmt = _JsonFormatter()
        record = _make_record()
        data = json.loads(fmt.format(record))
        assert data["level"] == "INFO"

    def test_logger_name_is_included(self) -> None:
        fmt = _JsonFormatter()
        record = _make_record()
        data = json.loads(fmt.format(record))
        assert data["logger"] == "test.logger"

    def test_request_id_absent_outside_request(self) -> None:
        # Ensure no lingering request-id from another test
        token = _request_id_var.set(None)
        try:
            fmt = _JsonFormatter()
            data = json.loads(fmt.format(_make_record()))
            assert "request_id" not in data
        finally:
            _request_id_var.reset(token)

    def test_request_id_present_when_set(self) -> None:
        token = _request_id_var.set("req-abc-123")
        try:
            fmt = _JsonFormatter()
            data = json.loads(fmt.format(_make_record()))
            assert data["request_id"] == "req-abc-123"
        finally:
            _request_id_var.reset(token)

    def test_exc_info_included_when_provided(self) -> None:
        fmt = _JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="t",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="err",
                args=(),
                exc_info=sys.exc_info(),
            )
        data = json.loads(fmt.format(record))
        assert "exc" in data
        assert "ValueError" in data["exc"]


class TestConfigureLogging:
    def test_sets_log_level_on_root_logger(self) -> None:
        configure_logging("DEBUG", json=False)
        assert logging.getLogger().level == logging.DEBUG
        # reset to INFO so other tests are unaffected
        configure_logging("INFO", json=False)

    def test_json_true_installs_json_formatter(self) -> None:
        configure_logging("INFO", json=True)
        root = logging.getLogger()
        assert root.handlers
        assert isinstance(root.handlers[0].formatter, _JsonFormatter)
        # reset
        configure_logging("INFO", json=False)

    def test_idempotent_does_not_add_extra_handlers(self) -> None:
        configure_logging("INFO", json=False)
        before = len(logging.getLogger().handlers)
        configure_logging("INFO", json=False)
        after = len(logging.getLogger().handlers)
        assert after == before
