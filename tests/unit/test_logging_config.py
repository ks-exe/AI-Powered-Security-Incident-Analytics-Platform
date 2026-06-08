"""Unit tests for the shared logging utility."""

import json
import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from scripts.logging_config import ComponentAdapter, JSONFormatter, get_logger


class TestJSONFormatter:
    """Tests for the JSONFormatter class."""

    def setup_method(self):
        """Set up a formatter instance for each test."""
        self.formatter = JSONFormatter()

    def test_format_produces_valid_json(self):
        """Log output must be valid JSON."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=None,
            exc_info=None,
        )
        record.component = "test_component"
        record.context = {}
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_format_includes_required_fields(self):
        """Log output must contain timestamp, level, component, message, context."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Something happened",
            args=None,
            exc_info=None,
        )
        record.component = "dlt_pipeline"
        record.context = {"batch_id": "batch_001"}
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        assert parsed["level"] == "WARNING"
        assert parsed["component"] == "dlt_pipeline"
        assert parsed["message"] == "Something happened"
        assert parsed["context"] == {"batch_id": "batch_001"}

    def test_timestamp_is_iso8601_utc(self):
        """Timestamp must be ISO8601 format in UTC."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=None,
            exc_info=None,
        )
        record.component = "test"
        record.context = {}
        output = self.formatter.format(record)
        parsed = json.loads(output)

        # Should parse as a valid datetime with timezone info
        ts = datetime.fromisoformat(parsed["timestamp"])
        assert ts.tzinfo is not None
        assert ts.tzinfo == timezone.utc

    def test_format_with_exception(self):
        """Exception info should be included when present."""
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=None,
            exc_info=exc_info,
        )
        record.component = "ml_detection"
        record.context = {}
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert "ValueError: test error" in parsed["exception"]

    def test_format_without_exception(self):
        """When no exception, the exception field should not appear."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="No error",
            args=None,
            exc_info=None,
        )
        record.component = "test"
        record.context = {}
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert "exception" not in parsed

    def test_default_component_is_unknown(self):
        """When component attribute is missing, default to 'unknown'."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=None,
            exc_info=None,
        )
        # Don't set record.component
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert parsed["component"] == "unknown"

    def test_default_context_is_empty_dict(self):
        """When context attribute is missing, default to empty dict."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="msg",
            args=None,
            exc_info=None,
        )
        # Don't set record.context
        record.component = "test"
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert parsed["context"] == {}

    def test_message_with_format_args(self):
        """Message should be formatted with args when present."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Processed %d records in %.2f seconds",
            args=(100, 1.5),
            exc_info=None,
        )
        record.component = "test"
        record.context = {}
        output = self.formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "Processed 100 records in 1.50 seconds"


class TestGetLogger:
    """Tests for the get_logger function."""

    def setup_method(self):
        """Clear any existing handlers before each test."""
        # Remove handlers to ensure clean state
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith("platform."):
                logger = logging.getLogger(name)
                logger.handlers.clear()

    def test_returns_component_adapter(self):
        """get_logger should return a ComponentAdapter instance."""
        logger = get_logger("test_component")
        assert isinstance(logger, ComponentAdapter)

    def test_logger_has_json_formatter(self):
        """The underlying logger should use JSONFormatter."""
        adapter = get_logger("test_json")
        logger = adapter.logger
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0].formatter, JSONFormatter)

    def test_logger_outputs_to_stderr(self):
        """Logger should output to stderr by default."""
        import sys
        adapter = get_logger("test_stderr")
        logger = adapter.logger
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

    def test_logger_default_level_is_info(self):
        """Default logging level should be INFO."""
        adapter = get_logger("test_level")
        assert adapter.logger.level == logging.INFO

    def test_logger_custom_level(self):
        """Logger should support custom levels."""
        adapter = get_logger("test_debug", level=logging.DEBUG)
        assert adapter.logger.level == logging.DEBUG

    def test_no_duplicate_handlers(self):
        """Calling get_logger twice for same component should not add duplicate handlers."""
        get_logger("test_dup")
        adapter = get_logger("test_dup")
        assert len(adapter.logger.handlers) == 1

    def test_component_injected_in_log_output(self, capsys):
        """Component name should appear in JSON output."""
        import io
        adapter = get_logger("my_component")
        # Replace handler stream with a StringIO to capture output
        stream = io.StringIO()
        adapter.logger.handlers[0].stream = stream

        adapter.info("Hello")
        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["component"] == "my_component"

    def test_context_passed_via_extra(self, capsys):
        """Context dict should be included in JSON output."""
        import io
        adapter = get_logger("ctx_test")
        stream = io.StringIO()
        adapter.logger.handlers[0].stream = stream

        adapter.info("test msg", extra={"context": {"run_id": "run_001"}})
        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["context"] == {"run_id": "run_001"}

    def test_different_components_get_different_loggers(self):
        """Different component names should create distinct loggers."""
        a = get_logger("component_a")
        b = get_logger("component_b")
        assert a.logger is not b.logger
        assert a.logger.name == "platform.component_a"
        assert b.logger.name == "platform.component_b"
