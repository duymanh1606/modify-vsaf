"""Unit tests for router --help proxy (FR-2, Phase 174).

Verifies that PASS_THRU_CONTEXT commands delegate --help and -h to the
underlying orchestrator via _run_service, instead of letting Typer intercept
them and show its own one-line docstring.
"""

from unittest.mock import patch

from typer.testing import CliRunner
from vds_cli.cli import app

runner = CliRunner()


def test_router_help_delegates_to_service() -> None:
    """vds-cli jira --help must delegate to _run_service, not show Typer's help."""
    with patch("vds_cli.cli._run_service") as mock_run:
        runner.invoke(app, ["jira", "--help"])
        mock_run.assert_called_once()
        service, args = mock_run.call_args.args
        assert service == "jira"
        assert "--help" in args


def test_router_help_short_form() -> None:
    """vds-cli jira -h must also delegate to _run_service."""
    with patch("vds_cli.cli._run_service") as mock_run:
        runner.invoke(app, ["jira", "-h"])
        mock_run.assert_called_once()
        service, args = mock_run.call_args.args
        assert service == "jira"
        assert "-h" in args


def test_router_no_args_still_works() -> None:
    """vds-cli jira with no extra args still routes to _run_service without crashing."""
    with patch("vds_cli.cli._run_service") as mock_run:
        runner.invoke(app, ["jira"])
        mock_run.assert_called_once()
        service, args = mock_run.call_args.args
        assert service == "jira"
        assert args == []
