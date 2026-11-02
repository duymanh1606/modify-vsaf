"""TDD tests for vds_agent_core.observability.jsonl_exporter.

TSK-P3-0.2 (ecosystem-daily-report Phase 3 Wave 0). Covers:
* Date rotation by UTC date
* Required record shape
* Missing-dir auto-create
* Sequential append safety (concurrent-style writes from a single process)
* Exception during write does not propagate
* Integration with the AgentTracer record_llm_call hook
* JSON.loads round-trip
* ISO-8601 timestamp format
* Missing-fields tolerance
* Multi-call accumulation in same file
* Env var override
* Optional cost_usd serialization
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

ISO8601_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """Isolated cache directory for every test."""
    return tmp_path / "llm-usage"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestRecordShape:
    """Required JSONL record fields and types."""

    def test_writes_required_fields(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-30T12:34:56Z",
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801,
            "request_id": "req_abc",
        })

        files = list(base_dir.glob("*.jsonl"))
        assert len(files) == 1, f"expected 1 file, got {files}"
        records = _read_jsonl(files[0])
        assert len(records) == 1
        rec = records[0]
        for field in ("timestamp", "provider", "model", "prompt_tokens",
                      "completion_tokens", "total_tokens", "request_id"):
            assert field in rec, f"missing field {field!r} in {rec}"
        assert rec["provider"] == "openai"
        assert rec["model"] == "gpt-4o-2024-11-20"
        assert rec["prompt_tokens"] == 1234
        assert rec["completion_tokens"] == 567
        assert rec["total_tokens"] == 1801
        assert rec["request_id"] == "req_abc"

    def test_iso8601_timestamp_format(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-30T12:34:56Z",
            "provider": "openai",
            "model": "gpt-4o",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "request_id": "r1",
        })
        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        assert ISO8601_Z.match(rec["timestamp"]), rec["timestamp"]


class TestDateRotation:
    """One file per UTC day."""

    def test_separate_files_for_separate_days(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-29T23:59:59Z",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "a",
        })
        exporter({
            "timestamp": "2026-04-30T00:00:01Z",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "b",
        })

        names = sorted(p.name for p in base_dir.glob("*.jsonl"))
        assert names == ["2026-04-29.jsonl", "2026-04-30.jsonl"]

    def test_filename_uses_utc_not_local(self, base_dir: Path) -> None:
        """Even if the timestamp carries a non-UTC offset, the file uses UTC."""
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        # 2026-04-30 02:00 +07:00 == 2026-04-29 19:00 UTC
        exporter({
            "timestamp": "2026-04-30T02:00:00+07:00",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "x",
        })
        names = [p.name for p in base_dir.glob("*.jsonl")]
        assert names == ["2026-04-29.jsonl"]


class TestDirectoryHandling:
    """Auto-create the cache directory on first write."""

    def test_creates_missing_base_dir(self, tmp_path: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        nested = tmp_path / "deep" / "nested" / "llm-usage"
        assert not nested.exists()

        exporter = JsonlUsageExporter(base_dir=nested)
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "x",
        })
        assert nested.exists() and nested.is_dir()
        assert any(nested.glob("*.jsonl"))


class TestAppendSafety:
    """Sequential appends accumulate in the same file."""

    def test_multiple_records_same_day_accumulate(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        for i in range(5):
            exporter({
                "timestamp": "2026-04-30T12:00:00Z",
                "provider": "openai",
                "model": "gpt-4o",
                "prompt_tokens": 100 + i,
                "completion_tokens": 50,
                "total_tokens": 150 + i,
                "request_id": f"req_{i}",
            })

        files = list(base_dir.glob("*.jsonl"))
        assert len(files) == 1
        records = _read_jsonl(files[0])
        assert len(records) == 5
        assert [r["request_id"] for r in records] == [f"req_{i}" for i in range(5)]

    def test_each_line_parses_via_json_loads(self, base_dir: Path) -> None:
        """Explicit assertion that the JSONL parses back via json.loads."""
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
            "request_id": "req_z",
        })
        path = next(base_dir.glob("*.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = json.loads(line)  # must not raise
            assert parsed["model"] == "claude-sonnet-4-5"


class TestErrorIsolation:
    """Exporter must never raise into the tracer."""

    def test_write_failure_is_swallowed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=tmp_path / "ok")

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "open", boom)

        # Must not raise.
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "x",
        })

    def test_non_dict_event_is_swallowed(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        # Must not raise.
        exporter("not a dict")  # type: ignore[arg-type]
        exporter(None)  # type: ignore[arg-type]


class TestMissingFieldTolerance:
    """Optional fields can be absent without breaking the writer."""

    def test_missing_optional_fields_filled_with_none(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "model": "m",
            "prompt_tokens": 5,
            "completion_tokens": 7,
        })  # no provider, request_id, total_tokens
        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        assert rec["provider"] is None
        assert rec["request_id"] is None
        # total_tokens is recomputed when absent.
        assert rec["total_tokens"] == 12
        # cost_usd is omitted when not provided.
        assert "cost_usd" not in rec

    def test_cost_usd_emitted_when_present(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "openai",
            "model": "gpt-4o",
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
            "request_id": "r",
            "cost_usd": 0.0042,
        })
        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        assert rec["cost_usd"] == pytest.approx(0.0042)


class TestEnvVarOverride:
    """VDS_LLM_USAGE_DIR env var redirects the cache."""

    def test_env_var_resolves_base_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vds_agent_core.observability.jsonl_exporter import (
            ENV_BASE_DIR,
            JsonlUsageExporter,
        )

        target = tmp_path / "from-env"
        monkeypatch.setenv(ENV_BASE_DIR, str(target))

        exporter = JsonlUsageExporter()
        assert exporter.base_dir == target
        exporter({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "p", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "x",
        })
        assert any(target.glob("*.jsonl"))

    def test_explicit_base_dir_beats_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from vds_agent_core.observability.jsonl_exporter import (
            ENV_BASE_DIR,
            JsonlUsageExporter,
        )

        monkeypatch.setenv(ENV_BASE_DIR, str(tmp_path / "env"))
        explicit = tmp_path / "explicit"
        exporter = JsonlUsageExporter(base_dir=explicit)
        assert exporter.base_dir == explicit


class TestTracerIntegration:
    """End-to-end: tracer.record_llm_call dispatches to the exporter."""

    def test_register_and_record_via_tracer(self, base_dir: Path) -> None:
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        tracer = AgentTracer(service_name="test-jsonl", enabled=False)
        exporter = JsonlUsageExporter(base_dir=base_dir)
        unregister = tracer.register_usage_observer(exporter)

        try:
            tracer.record_llm_call(
                model="gpt-4o",
                prompt_tokens=100,
                completion_tokens=50,
                provider="openai",
                request_id="req_int",
                timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
            )
        finally:
            unregister()

        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        assert rec["provider"] == "openai"
        assert rec["model"] == "gpt-4o"
        assert rec["prompt_tokens"] == 100
        assert rec["completion_tokens"] == 50
        assert rec["total_tokens"] == 150
        assert rec["request_id"] == "req_int"
        assert ISO8601_Z.match(rec["timestamp"])

    def test_unregister_stops_recording(self, base_dir: Path) -> None:
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        tracer = AgentTracer(service_name="test-unreg", enabled=False)
        exporter = JsonlUsageExporter(base_dir=base_dir)
        unregister = tracer.register_usage_observer(exporter)
        unregister()

        tracer.record_llm_call(
            model="gpt-4o",
            prompt_tokens=1,
            completion_tokens=1,
            provider="openai",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        assert not any(base_dir.glob("*.jsonl"))

    def test_observer_exception_does_not_break_tracer(
        self, base_dir: Path,
    ) -> None:
        """A failing observer must not stop subsequent observers or the tracer."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

        tracer = AgentTracer(service_name="test-iso", enabled=False)
        good = JsonlUsageExporter(base_dir=base_dir)

        def bad(_: dict) -> None:
            raise RuntimeError("observer is broken")

        tracer.register_usage_observer(bad)
        tracer.register_usage_observer(good)

        # Must not raise even though the first observer raises.
        tracer.record_llm_call(
            model="gpt-4o",
            prompt_tokens=10,
            completion_tokens=10,
            provider="openai",
            request_id="r",
            timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
        )
        # The good exporter still recorded.
        assert any(base_dir.glob("*.jsonl"))


class TestMakeObserverHelper:
    """The make_observer convenience returns a callable."""

    def test_make_observer_returns_callable(self, base_dir: Path) -> None:
        from vds_agent_core.observability.jsonl_exporter import make_observer

        observer = make_observer(base_dir=base_dir)
        assert callable(observer)
        observer({
            "timestamp": "2026-04-30T12:00:00Z",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "x",
        })
        assert any(base_dir.glob("*.jsonl"))


class TestDefaultBaseDir:
    """Default base dir resolves under HOME, not CWD."""

    def test_default_base_dir_under_home(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        from vds_agent_core.observability.jsonl_exporter import (
            ENV_BASE_DIR,
            JsonlUsageExporter,
        )

        monkeypatch.delenv(ENV_BASE_DIR, raising=False)
        # We don't write — we just check the resolved path.
        # ensure_dir=False makes this safe even though the dir doesn't exist.
        exporter = JsonlUsageExporter(ensure_dir=False)
        # Path components must include .vds/cache/llm-usage.
        parts = exporter.base_dir.parts
        assert parts[-3:] == (".vds", "cache", "llm-usage")


class TestParseTimestampBranches:
    """Cover the _parse_timestamp helper (gap 84, 89-93, 96).

    Exercised indirectly via the public ``__call__``; every branch
    asserts an observable side-effect (filename or record content)
    rather than just executing.
    """

    def test_datetime_value_used_directly_for_filename(
        self, base_dir: Path,
    ) -> None:
        """datetime instance bypasses ISO-parse branch (line 84)."""
        from vds_agent_core.observability.jsonl_exporter import (
            JsonlUsageExporter,
        )

        exporter = JsonlUsageExporter(base_dir=base_dir)
        # Pass a real datetime, not an ISO string. The exporter must
        # honor it for the filename rotation.
        exporter({
            "timestamp": datetime(2026, 3, 15, 8, 30, 0, tzinfo=UTC),
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "dt",
        })
        names = [p.name for p in base_dir.glob("*.jsonl")]
        assert names == ["2026-03-15.jsonl"]
        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        # Re-serialized to canonical Z-suffix ISO-8601.
        assert rec["timestamp"] == "2026-03-15T08:30:00Z"

    def test_unparseable_iso_string_falls_back_to_now(
        self,
        base_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ValueError on fromisoformat → use datetime.now(UTC) (lines 89-91).

        We pin ``datetime.now`` so the fallback timestamp is deterministic
        and verify the file name uses the pinned date instead of crashing.
        """
        from vds_agent_core.observability import jsonl_exporter as mod
        from vds_agent_core.observability.jsonl_exporter import (
            JsonlUsageExporter,
        )

        pinned_now = datetime(2026, 7, 4, 18, 0, 0, tzinfo=UTC)

        class _PinnedDateTime:
            @staticmethod
            def now(tz=None):
                return pinned_now

            @staticmethod
            def fromisoformat(value):
                return datetime.fromisoformat(value)

        # Patch the symbol the helper uses, not the global stdlib.
        monkeypatch.setattr(mod, "datetime", _PinnedDateTime)

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            # Definitely not ISO-8601 — triggers ValueError fallback.
            "timestamp": "not-a-real-iso-stamp",
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "bad",
        })
        # File must use pinned-now's UTC date, proving the fallback ran.
        names = [p.name for p in base_dir.glob("*.jsonl")]
        assert names == ["2026-07-04.jsonl"]

    def test_non_str_non_datetime_value_falls_back_to_now(
        self,
        base_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Non-string, non-datetime value triggers the else branch (lines 92-93).

        e.g. an integer epoch slipped in by a misconfigured upstream;
        the exporter must not crash and must use the now() fallback.
        """
        from vds_agent_core.observability import jsonl_exporter as mod
        from vds_agent_core.observability.jsonl_exporter import (
            JsonlUsageExporter,
        )

        pinned_now = datetime(2026, 8, 9, 5, 0, 0, tzinfo=UTC)

        class _PinnedDateTime:
            @staticmethod
            def now(tz=None):
                return pinned_now

            @staticmethod
            def fromisoformat(value):
                return datetime.fromisoformat(value)

        monkeypatch.setattr(mod, "datetime", _PinnedDateTime)

        exporter = JsonlUsageExporter(base_dir=base_dir)
        exporter({
            "timestamp": 1719331200,  # int, not str/datetime
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "int",
        })
        names = [p.name for p in base_dir.glob("*.jsonl")]
        assert names == ["2026-08-09.jsonl"]

    def test_naive_datetime_value_normalized_to_utc(
        self, base_dir: Path,
    ) -> None:
        """A naive datetime gets UTC tzinfo applied (line 96).

        The naive instant must be interpreted as UTC, not local time —
        verifies via the resulting filename and ISO output.
        """
        from vds_agent_core.observability.jsonl_exporter import (
            JsonlUsageExporter,
        )

        exporter = JsonlUsageExporter(base_dir=base_dir)
        # Naive datetime — no tzinfo. The helper must coerce to UTC.
        naive = datetime(2026, 5, 1, 14, 0, 0)
        assert naive.tzinfo is None
        exporter({
            "timestamp": naive,
            "provider": "openai", "model": "m", "prompt_tokens": 1,
            "completion_tokens": 1, "total_tokens": 2, "request_id": "naive",
        })
        names = [p.name for p in base_dir.glob("*.jsonl")]
        assert names == ["2026-05-01.jsonl"]
        rec = _read_jsonl(next(base_dir.glob("*.jsonl")))[0]
        # 14:00 naive interpreted as UTC -> 14:00Z.
        assert rec["timestamp"] == "2026-05-01T14:00:00Z"
