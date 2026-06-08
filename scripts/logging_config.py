"""Structured JSON logging utility for all platform components.

Provides a shared logging configuration with JSON-formatted output
that includes timestamp (ISO8601), level, component, message, and context fields.

Usage:
    from scripts.logging_config import get_logger

    logger = get_logger("mock_data_generator")
    logger.info("Generating events", extra={"context": {"count": 10000}})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for all platform components.

    Produces log entries with the following fields:
    - timestamp: ISO8601 UTC timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - component: The platform component that emitted the log
    - message: The log message
    - context: Additional structured context (run_id, batch_id, etc.)
    - exception: Exception traceback (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string."""
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": getattr(record, "component", "unknown"),
            "message": record.getMessage(),
            "context": getattr(record, "context", {}),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class ComponentAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically injects the component name.

    This adapter ensures that every log record produced by a component
    includes the component field without requiring it in every log call.
    Context can be passed via the `extra` dict with a "context" key.
    """

    def process(
        self, msg: str, kwargs: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Inject component and merge context into the log record extras."""
        extra = kwargs.get("extra", {})
        extra["component"] = self.extra["component"]
        # Merge any context passed in extra with adapter-level context
        if "context" not in extra:
            extra["context"] = {}
        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(component: str, level: int = logging.INFO) -> ComponentAdapter:
    """Get a configured logger for a platform component.

    Returns a ComponentAdapter that automatically includes the component
    name in all log entries. The logger outputs JSON-formatted messages
    to stderr.

    Args:
        component: Name of the platform component (e.g., "mock_data_generator",
                   "dlt_pipeline", "ml_detection").
        level: Logging level. Defaults to INFO.

    Returns:
        A ComponentAdapter wrapping a configured logger with JSON output.

    Example:
        logger = get_logger("dlt_pipeline")
        logger.info("Ingestion started", extra={"context": {"batch_id": "batch_20240115_001"}})
    """
    logger = logging.getLogger(f"platform.{component}")

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    logger.setLevel(level)

    return ComponentAdapter(logger, {"component": component})
