"""Centralized logging configuration for backend services."""

from __future__ import annotations

import logging
import os
from typing import Iterable

DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
DEFAULT_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging(
    *,
    level: str | None = None,
    format: str = DEFAULT_FORMAT,
    datefmt: str = DEFAULT_DATEFMT,
    include_uvicorn: bool = True,
    extra_loggers: Iterable[str] | None = None,
) -> logging.Logger:
    """Configure application logging with sensible defaults.

    Args:
        level: Optional explicit log level. Falls back to ``TANK_LOG_LEVEL`` env
            var or INFO when not provided.
        format: Log format string.
        datefmt: Date format string.
        include_uvicorn: Whether to align uvicorn loggers with the backend level.
        extra_loggers: Additional logger names to align with the configured level.

    Returns:
        The application logger configured for the backend (``tank.backend``).
    """

    raw_level = level if level is not None else os.getenv("TANK_LOG_LEVEL")
    resolved_level = (raw_level or "INFO").upper()
    logging.basicConfig(level=resolved_level, format=format, datefmt=datefmt)

    app_logger = logging.getLogger("tank.backend")
    app_logger.setLevel(resolved_level)

    if include_uvicorn:
        for uvicorn_logger in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logging.getLogger(uvicorn_logger).setLevel(resolved_level)

    if extra_loggers:
        for logger_name in extra_loggers:
            logging.getLogger(logger_name).setLevel(resolved_level)

    app_logger.debug("Logging configured", extra={"level": resolved_level, "format": format})
    return app_logger
