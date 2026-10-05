"""Central logging configuration for MarketingMind AI backend."""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings


class JsonFormatter(logging.Formatter):
    """Structured JSON logs for production aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("method", "path", "status_code", "duration_ms", "user_email", "event"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


def _resolve_log_level(settings: Settings) -> str:
    explicit = (getattr(settings, "log_level", None) or "").strip().upper()
    if explicit:
        return explicit
    if settings.environment == "production":
        return "INFO"
    if settings.environment == "staging":
        return "INFO"
    return "DEBUG"


def setup_logging(settings: Settings) -> None:
    """Configure root and uvicorn loggers once at application startup."""
    level = _resolve_log_level(settings)
    use_json = settings.environment == "production"

    if use_json:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.config.dictConfig({"version": 1, "disable_existing_loggers": False})

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        named = logging.getLogger(name)
        named.handlers.clear()
        named.propagate = True

    logging.getLogger("app").setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
