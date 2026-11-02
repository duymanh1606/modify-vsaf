"""Tests for vds_cli_common.app — TSK-7.16."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import typer
from typer.testing import CliRunner

from vds_cli_common import CLIContext, make_vds_app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(*, settings_factory: Callable[[], Any] | None = None) -> tuple[typer.Typer, dict]:
    """Create app + captured dict + a registered dummy command."""
    captured: dict = {}
    factory = settings_factory or (lambda: None)
    app = make_vds_app(name="tst", help="test app", settings_factory=factory)

    @app.command()
    def cmd(ctx: typer.Context) -> None:
        captured["obj"] = ctx.obj

    return app, captured


# ---------------------------------------------------------------------------
# Context construction
# ---------------------------------------------------------------------------


def test_cli_context_created_on_invoke() -> None:
    """ctx.obj['cli_ctx'] is a CLIContext after app invocation."""
    app, captured = _make_app()
    runner.invoke(app, ["cmd"])
    assert isinstance(captured["obj"]["cli_ctx"], CLIContext)


# ---------------------------------------------------------------------------
# Flag propagation
# ---------------------------------------------------------------------------


def test_json_flag_propagates() -> None:
    """--json sets json_only=True on the CLIContext."""
    app, captured = _make_app()
    runner.invoke(app, ["--json", "cmd"])
    assert captured["obj"]["cli_ctx"].json_only is True


def test_quiet_flag_propagates() -> None:
    """--quiet sets quiet=True on the CLIContext."""
    app, captured = _make_app()
    runner.invoke(app, ["--quiet", "cmd"])
    assert captured["obj"]["cli_ctx"].quiet is True


def test_verbose_flag_sets_structured_logs() -> None:
    """--verbose sets structured_logs=True on the CLIContext."""
    app, captured = _make_app()
    runner.invoke(app, ["--verbose", "cmd"])
    assert captured["obj"]["cli_ctx"].structured_logs is True


def test_no_color_flag_propagates() -> None:
    """--no-color sets no_color=True on the CLIContext."""
    app, captured = _make_app()
    runner.invoke(app, ["--no-color", "cmd"])
    assert captured["obj"]["cli_ctx"].no_color is True


# ---------------------------------------------------------------------------
# settings_factory lifecycle
# ---------------------------------------------------------------------------


def test_settings_factory_called_once_per_invocation() -> None:
    """settings_factory is called exactly once per command run."""
    factory = MagicMock(return_value=None)
    app, _ = _make_app(settings_factory=factory)
    runner.invoke(app, ["cmd"])
    factory.assert_called_once()


def test_no_shared_state_between_invocations() -> None:
    """Each invocation yields a fresh CLIContext — no module-level state bleed."""
    app, captured = _make_app()
    runner.invoke(app, ["--json", "cmd"])
    first = captured["obj"]["cli_ctx"]
    runner.invoke(app, ["cmd"])
    second = captured["obj"]["cli_ctx"]
    assert first is not second
    assert second.json_only is False  # fresh context, not contaminated


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_app_returns_typer_instance() -> None:
    """make_vds_app returns a typer.Typer instance."""
    app = make_vds_app(name="x", help="x", settings_factory=lambda: None)
    assert isinstance(app, typer.Typer)


def test_make_vds_app_docstring_marks_factory_as_new_cli_only() -> None:
    """Factory docs state the Phase 8 new-CLI-only guidance."""
    doc = make_vds_app.__doc__ or ""
    assert "new CLIs only" in doc
    assert "Existing CLIs should" in doc


def test_make_vds_app_docstring_points_to_bitbucket_pattern() -> None:
    """Factory docs reference the direct Typer compatibility pattern."""
    doc = make_vds_app.__doc__ or ""
    assert "bitbucket_orchestrator/cli.py" in doc
    assert "direct `typer.Typer()`" in doc
