"""Tests for vds_platform_core.logging — TDD RED phase."""

import json
import logging
import tempfile
from pathlib import Path

import structlog
from vds_platform_core.logging import configure_structlog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _processor_types(config: dict) -> list[str]:
    """Return list of class names for processors in structlog config."""
    procs = config.get("processors", [])
    return [type(p).__name__ for p in procs]


def _payload_for_event(stderr: str, event: str) -> dict:
    """Extract JSON payload for a given event from stderr lines."""
    for line in stderr.splitlines():
        if event not in line:
            continue
        start = line.find("{")
        if start == -1:
            continue
        try:
            payload = json.loads(line[start:])
        except json.JSONDecodeError:
            continue
        if payload.get("event") == event:
            return payload
    raise AssertionError(f"Event '{event}' not found in stderr")


# ---------------------------------------------------------------------------
# Log level mapping
# ---------------------------------------------------------------------------


class TestLogLevelMapping:
    def test_default_sets_info(self) -> None:
        configure_structlog()
        assert logging.root.level == logging.INFO

    def test_quiet_sets_warning(self) -> None:
        configure_structlog(quiet=True)
        assert logging.root.level == logging.WARNING

    def test_verbose_sets_debug(self) -> None:
        configure_structlog(verbose=True)
        assert logging.root.level == logging.DEBUG

    def test_verbose_overrides_quiet(self) -> None:
        """When both are set, verbose wins (DEBUG < WARNING)."""
        configure_structlog(quiet=True, verbose=True)
        assert logging.root.level == logging.DEBUG


# ---------------------------------------------------------------------------
# Renderer selection
# ---------------------------------------------------------------------------


class TestRendererSelection:
    def test_default_uses_console_renderer(self) -> None:
        configure_structlog()
        config = structlog.get_config()
        proc_names = _processor_types(config)
        assert "ConsoleRenderer" in proc_names

    def test_json_mode_uses_json_renderer(self) -> None:
        configure_structlog(json_logs=True)
        config = structlog.get_config()
        proc_names = _processor_types(config)
        assert "JSONRenderer" in proc_names

    def test_json_mode_not_console_renderer(self) -> None:
        configure_structlog(json_logs=True)
        config = structlog.get_config()
        proc_names = _processor_types(config)
        assert "ConsoleRenderer" not in proc_names

    def test_json_mode_includes_logger_key(self, capsys) -> None:
        configure_structlog(json_logs=True)
        structlog.get_logger("platform_core.test").info("logger-key-check")

        stderr = capsys.readouterr().err
        payload = _payload_for_event(stderr, "logger-key-check")
        assert payload["logger"] == "platform_core.test"


# ---------------------------------------------------------------------------
# File logging
# ---------------------------------------------------------------------------


class TestFileLogging:
    def test_log_file_creates_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test.log"
            configure_structlog(log_file=log_path)
            # The root logger should have a FileHandler pointing to log_path.
            # Use .resolve() for symlink-safe comparison (macOS /tmp → /private/tmp).
            file_handlers = [h for h in logging.root.handlers if isinstance(h, logging.FileHandler)]
            assert any(Path(h.baseFilename).resolve() == log_path.resolve() for h in file_handlers)


# ---------------------------------------------------------------------------
# Idempotency / multiple calls
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_multiple_calls_do_not_raise(self) -> None:
        """configure_structlog must be callable multiple times without error."""
        configure_structlog()
        configure_structlog(quiet=True)
        configure_structlog(verbose=True, json_logs=True)
        # No assertion needed — just must not raise


class TestExtendedApi:
    def test_default_logger_factory_is_stdlib(self) -> None:
        configure_structlog()
        assert isinstance(structlog.get_config()["logger_factory"], structlog.stdlib.LoggerFactory)

    def test_custom_processors_are_applied(self, capsys) -> None:
        def inject_wave(_logger, _method_name, event_dict):
            event_dict["wave"] = "w1"
            return event_dict

        configure_structlog(json_logs=True, custom_processors=[inject_wave])
        structlog.get_logger("platform_core.test").info("custom-processor-check")

        stderr = capsys.readouterr().err
        payload = _payload_for_event(stderr, "custom-processor-check")
        assert payload["wave"] == "w1"

    def test_logger_factory_override_and_cache_flag(self) -> None:
        factory = structlog.stdlib.LoggerFactory()
        configure_structlog(logger_factory=factory, cache_logger=True)
        config = structlog.get_config()
        assert config["logger_factory"] is factory
        assert config["cache_logger_on_first_use"] is True
