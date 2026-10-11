"""Structured logs, configured once per process: one line per event, fields not prose, UTC."""

from __future__ import annotations

import logging

import structlog

from app.core.config import ObservabilitySettings


def configure_logging(settings: ObservabilitySettings) -> None:
    level = logging.getLevelName(settings.log_level.upper())
    logging.basicConfig(format="%(message)s", level=level)
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer()
        if settings.log_as_json
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger(name)
