from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator import cli
from vds_jira_orchestrator.errors import VDSClientError


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def _mock_settings(mock_settings_cls: MagicMock) -> MagicMock:
    settings = mock_settings_cls.return_value
    settings.require_basic_or_token.return_value = None
    settings.username = "user"
    settings.password = "pass"
    settings.token = "token"
    settings.base_url = "https://jira.test"
    return settings


class TestJiraCLI:
    @pytest.mark.parametrize("flag", ["--version"])
    def test_version_option(self, runner: CliRunner, flag: str) -> None:
        result = runner.invoke(cli.app, [flag])
        assert result.exit_code == 0
        assert cli.APP_NAME in result.stdout
        assert cli.APP_VERSION in result.stdout

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_projects_success(
        self, mock_settings_cls: MagicMock, mock_adapter_cls: MagicMock, runner: CliRunner
    ) -> None:
        _mock_settings(mock_settings_cls)
        mock_adapter = mock_adapter_cls.return_value
        mock_adapter.list_projects.return_value = [{"key": "TEST", "name": "Test Project"}]

        result = runner.invoke(cli.app, ["projects"])

        assert result.exit_code == 0
        assert "TEST" in result.stdout
        assert "Test Project" in result.stdout

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_search_failure_sets_exit_code(
        self, mock_settings_cls: MagicMock, mock_adapter_cls: MagicMock, runner: CliRunner
    ) -> None:
        _mock_settings(mock_settings_cls)
        mock_adapter = mock_adapter_cls.return_value
        mock_adapter.jql.side_effect = VDSClientError("boom")

        result = runner.invoke(cli.app, ["search", "project = TEST"])

        assert result.exit_code == 1
        assert "Error" in result.stderr

    def test_worklog_requires_issue_key(self, runner: CliRunner) -> None:
        result = runner.invoke(cli.app, ["worklog", "get"])
        assert result.exit_code == 1
        assert "issue-key" in result.stderr

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_worklog_updated_success(
        self, mock_settings_cls: MagicMock, mock_adapter_cls: MagicMock, runner: CliRunner
    ) -> None:
        _mock_settings(mock_settings_cls)
        mock_adapter = mock_adapter_cls.return_value
        mock_adapter.get_updated_worklogs.return_value = {"values": []}

        result = runner.invoke(cli.app, ["worklog", "updated", "--since", "2025-11-01T00:00:00Z"])

        assert result.exit_code == 0
        assert "values" in result.stdout

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_transitions_success(
        self, mock_settings_cls: MagicMock, mock_adapter_cls: MagicMock, runner: CliRunner
    ) -> None:
        _mock_settings(mock_settings_cls)
        mock_adapter = mock_adapter_cls.return_value
        mock_adapter.get_issue_transitions.return_value = {"transitions": [{"name": "Done"}]}

        result = runner.invoke(cli.app, ["transitions", "TEST-123"])

        assert result.exit_code == 0
        assert "Done" in result.stdout

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_changelog_status_success(
        self, mock_settings_cls: MagicMock, mock_adapter_cls: MagicMock, runner: CliRunner
    ) -> None:
        _mock_settings(mock_settings_cls)
        mock_adapter = mock_adapter_cls.return_value
        mock_adapter.get_issue_status_changelog.return_value = {"values": []}

        result = runner.invoke(cli.app, ["changelog", "status", "TEST-123"])

        assert result.exit_code == 0
        assert "values" in result.stdout
