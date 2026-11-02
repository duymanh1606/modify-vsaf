"""Tests for JIRA Agile/Scrum operations."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner
from vds_jira_orchestrator.cli import app
from vds_jira_orchestrator.errors import VDSClientError


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_board() -> dict:
    """Sample agile board response."""
    return {
        "id": 1,
        "name": "Test Board",
        "type": "scrum",
        "location": {"projectId": 10000, "displayName": "Test Project"},
    }


@pytest.fixture
def sample_epic() -> dict:
    """Sample epic response."""
    return {
        "id": 1,
        "key": "TEST-100",
        "name": "Test Epic",
        "summary": "Test Epic Summary",
        "done": False,
    }


class TestAgileBoardOperations:
    """Test suite for Agile board operations."""

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_list(
        self,
        mock_settings: Mock,
        mock_adapter_class: Mock,
        runner: CliRunner,
        sample_board: dict,
    ) -> None:
        """Test board list command."""
        mock_adapter = Mock()
        mock_adapter.get_all_agile_boards.return_value = [sample_board]
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "list", "--limit", "10"])
        assert result.exit_code == 0
        mock_adapter.get_all_agile_boards.assert_called_once_with(project_key=None, board_type=None, start=0, limit=10)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_get_by_id(
        self,
        mock_settings: Mock,
        mock_adapter_class: Mock,
        runner: CliRunner,
        sample_board: dict,
    ) -> None:
        """Test board get by ID command."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board.return_value = sample_board
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "get", "--board-id", "1"])
        assert result.exit_code == 0
        mock_adapter.get_agile_board.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_get_by_filter(
        self,
        mock_settings: Mock,
        mock_adapter_class: Mock,
        runner: CliRunner,
        sample_board: dict,
    ) -> None:
        """Test board get by filter ID command."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board_by_filter_id.return_value = sample_board
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "get", "--filter-id", "100"])
        assert result.exit_code == 0
        mock_adapter.get_agile_board_by_filter_id.assert_called_once_with(100)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_create(
        self,
        mock_settings: Mock,
        mock_adapter_class: Mock,
        runner: CliRunner,
        sample_board: dict,
    ) -> None:
        """Test board create command."""
        mock_adapter = Mock()
        mock_adapter.create_agile_board.return_value = sample_board
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(
            app,
            [
                "board",
                "create",
                "--name",
                "Test Board",
                "--type",
                "scrum",
                "--filter-id",
                "100",
                "--yes",
            ],
        )
        assert result.exit_code == 0
        mock_adapter.create_agile_board.assert_called_once_with("Test Board", "scrum", 100)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_create_requires_yes(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board create requires --yes flag."""
        result = runner.invoke(
            app,
            [
                "board",
                "create",
                "--name",
                "Test Board",
                "--type",
                "scrum",
                "--filter-id",
                "100",
            ],
        )
        assert result.exit_code != 0
        assert "Refusing to create without --yes" in result.stderr

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_delete(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board delete command."""
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "delete", "--board-id", "1", "--yes"])
        assert result.exit_code == 0
        mock_adapter.delete_agile_board.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_config(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board config command."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board_configuration.return_value = {"config": "test"}
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "config", "--board-id", "1"])
        assert result.exit_code == 0
        mock_adapter.get_agile_board_configuration.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_issues(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board issues command."""
        mock_adapter = Mock()
        mock_adapter.get_issues_for_board.return_value = []
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "issues", "--board-id", "1"])
        assert result.exit_code == 0
        mock_adapter.get_issues_for_board.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_properties(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board properties command."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board_properties.return_value = [{"key": "prop1", "value": "val1"}]
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "properties", "--board-id", "1"])
        assert result.exit_code == 0
        mock_adapter.get_agile_board_properties.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_velocity(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board velocity command."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board_refined_velocity.return_value = {"velocity": 10}
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "velocity", "--board-id", "1"])
        assert result.exit_code == 0
        mock_adapter.get_agile_board_refined_velocity.assert_called_once_with(1)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_board_error_handling(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test board command error handling."""
        mock_adapter = Mock()
        mock_adapter.get_agile_board.side_effect = VDSClientError("Test error")
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["board", "get", "--board-id", "1"])
        assert result.exit_code != 0


class TestEpicOperations:
    """Test suite for Epic operations."""

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_epic_issues(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test epic issues command."""
        mock_adapter = Mock()
        mock_adapter.epic_issues.return_value = []
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["epic", "issues", "--epic-key", "TEST-100"])
        assert result.exit_code == 0
        mock_adapter.epic_issues.assert_called_once_with("TEST-100")

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_epic_list(
        self,
        mock_settings: Mock,
        mock_adapter_class: Mock,
        runner: CliRunner,
        sample_epic: dict,
    ) -> None:
        """Test epic list command."""
        mock_adapter = Mock()
        mock_adapter.get_epics.return_value = [sample_epic]
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["epic", "list", "--board-id", "1", "--limit", "10"])
        assert result.exit_code == 0
        mock_adapter.get_epics.assert_called_once_with(1, done=False, start=0, limit=10)

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_epic_issues_for_epic(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test epic issues-for-epic command."""
        mock_adapter = Mock()
        mock_adapter.get_issues_for_epic.return_value = []
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(
            app,
            [
                "epic",
                "issues-for-epic",
                "--board-id",
                "1",
                "--epic-id",
                "100",
                "--limit",
                "10",
            ],
        )
        assert result.exit_code == 0
        mock_adapter.get_issues_for_epic.assert_called_once_with(
            1,
            100,
            jql="",
            validate_query="",
            fields="*all",
            expand="",
            start=0,
            limit=10,
        )

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_epic_requires_epic_key(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test epic issues requires epic-key."""
        result = runner.invoke(app, ["epic", "issues"])
        assert result.exit_code != 0
        assert "--epic-key required" in result.stderr

    @patch("vds_jira_orchestrator.cli.JiraAdapter")
    @patch("vds_jira_orchestrator.cli.JiraSettings")
    def test_epic_error_handling(self, mock_settings: Mock, mock_adapter_class: Mock, runner: CliRunner) -> None:
        """Test epic command error handling."""
        mock_adapter = Mock()
        mock_adapter.epic_issues.side_effect = VDSClientError("Test error")
        mock_adapter_class.return_value = mock_adapter

        result = runner.invoke(app, ["epic", "issues", "--epic-key", "TEST-100"])
        assert result.exit_code != 0
