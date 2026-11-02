"""Structured logging configuration for Excel orchestrator."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for the orchestrator.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE)
    """
    if level.upper() == "NONE":
        logging.getLogger().addHandler(logging.NullHandler())
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL + 1),
        )
        return

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            (structlog.processors.JSONRenderer() if not sys.stderr.isatty() else structlog.dev.ConsoleRenderer()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (defaults to calling module)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
