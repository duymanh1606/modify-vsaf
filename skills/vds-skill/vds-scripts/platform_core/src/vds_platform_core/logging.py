"""VDS structlog factory.

Provides ``configure_structlog()`` to initialise a structlog pipeline with
VDS-standard processors.  Supports quiet / verbose / JSON modes and optional
file-based logging.

Usage::

    from vds_platform_core.logging import configure_structlog

    configure_structlog()                         # INFO, ConsoleRenderer → stderr
    configure_structlog(quiet=True)               # WARNING
    configure_structlog(verbose=True)             # DEBUG
    configure_structlog(json_logs=True)           # INFO + JSONRenderer
    configure_structlog(log_file=Path("app.log")) # also write to file
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import structlog


def configure_structlog(
    *,
    quiet: bool = False,
    verbose: bool = False,
    json_logs: bool = False,
    log_file: Path | None = None,
    custom_processors: Sequence[structlog.types.Processor] | None = None,
    logger_factory: Any | None = None,
    cache_logger: bool = False,
) -> None:
    """Configure the structlog pipeline and stdlib root logger.

    Call once at application startup.  Safe to call multiple times (each call
    reconfigures in place; extra ``FileHandler`` instances are deduplicated by
    path).

    Args:
        quiet: Set log level to WARNING.  Overridden by ``verbose``.
        verbose: Set log level to DEBUG.  Takes priority over ``quiet``.
        json_logs: Use ``structlog.dev.JSONRenderer`` instead of
            ``structlog.dev.ConsoleRenderer``.
        log_file: Optional path for a file handler (UTF-8, append mode).
            A new ``FileHandler`` is attached to the root logger only if no
            handler for the same path exists yet.
        custom_processors: Optional processors inserted before the renderer.
        logger_factory: Optional structlog logger factory override. Defaults
            to ``structlog.stdlib.LoggerFactory()``.
        cache_logger: Value forwarded to ``cache_logger_on_first_use``.
    """
    # ------------------------------------------------------------------
    # 1. Resolve log level
    # ------------------------------------------------------------------
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    # ------------------------------------------------------------------
    # 2. Configure stdlib root logger
    # ------------------------------------------------------------------
    formatter = logging.Formatter("%(message)s")
    logging.basicConfig(level=level, stream=sys.stderr, format="%(message)s")
    root = logging.getLogger()
    root.setLevel(level)

    # Ensure at least a stderr handler exists (avoid "No handlers found" noise)
    if not any(isinstance(h, logging.StreamHandler) and h.stream is sys.stderr for h in root.handlers):
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(level)
        stderr_handler.setFormatter(formatter)
        root.addHandler(stderr_handler)
    else:
        for h in root.handlers:
            h.setLevel(level)
            h.setFormatter(formatter)

    # ------------------------------------------------------------------
    # 3. Optional file handler (deduplicated by resolved path)
    # ------------------------------------------------------------------
    if log_file is not None:
        resolved = log_file.resolve()
        existing_paths = {Path(h.baseFilename).resolve() for h in root.handlers if isinstance(h, logging.FileHandler)}
        if resolved not in existing_paths:
            file_handler = logging.FileHandler(str(resolved), encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

    # ------------------------------------------------------------------
    # 4. Select renderer
    # ------------------------------------------------------------------
    if json_logs:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    # ------------------------------------------------------------------
    # 5. Build processor chain and configure structlog
    # ------------------------------------------------------------------
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            *(custom_processors or ()),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=logger_factory or structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=cache_logger,
    )


__all__ = ["configure_structlog"]
