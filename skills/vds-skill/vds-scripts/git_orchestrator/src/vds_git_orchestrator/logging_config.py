from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from rich.console import Console
from rich.logging import RichHandler


class JsonFormatter(logging.Formatter):
    """
    Minimal JSON formatter suitable for async workloads.
    """

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - simple wrapper
        base: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        if record.__dict__.get("repo"):
            base["repo"] = record.__dict__["repo"]
        if record.__dict__.get("project"):
            base["project"] = record.__dict__["project"]
        return json.dumps(base, ensure_ascii=False)


def configure_logging(json_log: bool = False) -> None:
    """
    Configure logging for both human and machine consumption.
    """

    logging.captureWarnings(True)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    handlers: list[logging.Handler] = []

    console = Console(stderr=True)
    handlers.append(
        RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=False,
            show_level=True,
            show_path=False,
        )
    )

    if json_log or os.getenv("VDS_GIT_JSON_LOG") == "1":
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setFormatter(JsonFormatter())
        handlers.append(json_handler)

    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        format="%(message)s",
    )
