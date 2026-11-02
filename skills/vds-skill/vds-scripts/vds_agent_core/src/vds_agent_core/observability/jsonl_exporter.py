"""JSONL exporter for LLM usage span events.

TSK-P3-0.2 (ecosystem-daily-report Phase 3, Wave 0).

The exporter subscribes to :class:`~vds_agent_core.observability.tracer.AgentTracer`
LLM-call events via the ``register_usage_observer`` hook and writes one JSON
record per LLM call to a date-rotated file under
``~/.vds/cache/llm-usage/<YYYY-MM-DD>.jsonl``.

Design notes
------------
* **Non-blocking write path.** The exporter never raises into the tracer:
  filesystem failures are logged and the offending event is dropped. The
  tracer-side observer wrapper also swallows observer exceptions, so this
  is double-safe.
* **Date rotation by UTC day.** The filename is derived from the event's
  own timestamp (UTC), so events generated near midnight land in the
  correct file even if observer callbacks are delayed.
* **Append-only single-process.** Each record is written with one
  ``write()`` call to a freshly-opened append-mode handle. This is
  safe for the single-process producer (`scheduler_orchestrator`
  daily-report worker). A multi-process producer can later bolt on
  ``fcntl.flock`` if needed; that's intentionally out of scope here.
* **Tests use ``tmp_path``.** The base directory is configurable via the
  ``base_dir`` constructor argument or the ``VDS_LLM_USAGE_DIR`` env var,
  so tests never touch ``~/.vds/cache/``.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

#: Default base directory under the user's ``$HOME``. Mirrors the broader
#: VDS cache convention (`~/.vds/cache/...`).
DEFAULT_BASE_DIR = Path.home() / ".vds" / "cache" / "llm-usage"

#: Override env var (used primarily by tests; ops can also set it
#: explicitly to redirect the cache to a non-home location).
ENV_BASE_DIR = "VDS_LLM_USAGE_DIR"

#: Schema fields, in stable order. Optional fields are emitted only when
#: present (i.e. non-None) to keep the JSONL records compact. Exposed as
#: public constants so consumers (e.g. analytics jobs, schema migrations)
#: can introspect the canonical record shape without re-parsing this file.
REQUIRED_FIELDS: tuple[str, ...] = (
    "timestamp",
    "provider",
    "model",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "request_id",
)
OPTIONAL_FIELDS: tuple[str, ...] = ("cost_usd",)


def _resolve_base_dir(base_dir: Path | str | None) -> Path:
    """Resolve the base directory, honoring env var and explicit overrides."""
    if base_dir is not None:
        return Path(base_dir)
    env_value = os.environ.get(ENV_BASE_DIR)
    if env_value:
        return Path(env_value)
    return DEFAULT_BASE_DIR


def _parse_timestamp(value: Any) -> datetime:
    """Best-effort parse of an event timestamp into a UTC ``datetime``.

    Accepts ISO-8601 strings (with ``Z`` or ``+00:00`` suffix) or
    ``datetime`` instances. Falls back to ``datetime.now(UTC)`` on parse
    failure — never raises, since exporter must not block the tracer.
    """
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
            ts = datetime.fromisoformat(normalized)
        except ValueError:
            logger.warning("Unparseable timestamp; using now()", value=value)
            ts = datetime.now(tz=UTC)
    else:
        ts = datetime.now(tz=UTC)

    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _normalize_record(event: dict[str, Any]) -> dict[str, Any]:
    """Project an event dict onto the canonical JSONL record shape.

    Tolerates missing optional fields (``provider``, ``request_id``,
    ``cost_usd``); fills missing token counts with ``0``. ``total_tokens``
    is recomputed if absent so consumers never see a ``None`` total.
    """
    prompt = int(event.get("prompt_tokens", 0) or 0)
    completion = int(event.get("completion_tokens", 0) or 0)
    total = event.get("total_tokens")
    if total is None:
        total = prompt + completion

    record: dict[str, Any] = {
        "timestamp": event.get("timestamp"),
        "provider": event.get("provider"),
        "model": event.get("model"),
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": int(total),
        "request_id": event.get("request_id"),
    }
    cost_usd = event.get("cost_usd")
    if cost_usd is not None:
        record["cost_usd"] = cost_usd
    return record


class JsonlUsageExporter:
    """Persist LLM-call usage events as date-rotated JSONL files.

    Construct one exporter per process and register it with
    :meth:`AgentTracer.register_usage_observer`::

        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        tracer = AgentTracer()
        exporter = JsonlUsageExporter()
        unregister = tracer.register_usage_observer(exporter)

    Calling ``exporter(event)`` (the ``__call__`` protocol) writes a single
    JSONL record. The class is intentionally callable so the registration
    site doesn't need to reach into a method name.
    """

    def __init__(
        self,
        base_dir: Path | str | None = None,
        *,
        ensure_dir: bool = True,
    ) -> None:
        self._base_dir: Path = _resolve_base_dir(base_dir)
        self._ensure_dir: bool = ensure_dir

    @property
    def base_dir(self) -> Path:
        """Resolved base directory the exporter writes into."""
        return self._base_dir

    def file_for(self, ts: datetime) -> Path:
        """Return the JSONL path for the UTC date of ``ts``."""
        utc = ts.astimezone(UTC) if ts.tzinfo else ts.replace(tzinfo=UTC)
        return self._base_dir / f"{utc.strftime('%Y-%m-%d')}.jsonl"

    def __call__(self, event: dict[str, Any]) -> None:
        """Observer entry point — write one JSONL record. Never raises.

        ``event`` is typed as ``dict[str, Any]`` for the documented contract,
        but defensive code still guards against non-dict inputs (tracer-side
        bugs, test scenarios). The runtime ``isinstance`` in the except
        branch is intentional — see ``_write`` for the full guard.
        """
        try:
            self._write(event)
        except Exception as exc:
            # Caller may pass a non-dict via ``# type: ignore`` in defensive
            # tests; runtime check ensures we don't crash on ``.keys()``.
            event_keys = (
                sorted(event.keys()) if isinstance(event, dict) else None  # pyright: ignore[reportUnnecessaryIsInstance]
            )
            logger.warning(
                "JSONL usage exporter dropped an event",
                error=str(exc),
                event_keys=event_keys,
            )

    # ----- Internals -------------------------------------------------------

    def _write(self, event: Any) -> None:
        # Accepts ``Any`` so the defensive runtime type-check below is not
        # short-circuited by static type narrowing — the tracer side may
        # legitimately hand us non-dict events when bug-shaped, and the
        # ``__call__`` wrapper relies on a real exception to swallow.
        if not isinstance(event, dict):
            raise TypeError(f"event must be dict, got {type(event).__name__}")

        record = _normalize_record(event)
        ts = _parse_timestamp(record.get("timestamp"))
        # Re-serialize the timestamp to canonical ISO-8601 with ``Z`` suffix
        # so consumers can rely on a single textual shape.
        record["timestamp"] = ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")

        path = self.file_for(ts)
        if self._ensure_dir:
            path.parent.mkdir(parents=True, exist_ok=True)

        # One write per record (line + newline) keeps records atomic on
        # POSIX append for sub-PIPE_BUF payloads — well within the 4096-byte
        # guarantee. We pass ensure_ascii=False so non-Latin model names
        # (rare but possible) round-trip cleanly.
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)


def make_observer(
    base_dir: Path | str | None = None,
    *,
    ensure_dir: bool = True,
) -> Callable[[dict[str, Any]], None]:
    """Convenience: build an exporter and return its callable form.

    Useful when the caller doesn't need to keep a reference to the
    exporter object (e.g. one-shot registration during process startup).
    """
    return JsonlUsageExporter(base_dir=base_dir, ensure_dir=ensure_dir)


__all__ = [
    "DEFAULT_BASE_DIR",
    "ENV_BASE_DIR",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "JsonlUsageExporter",
    "make_observer",
]
