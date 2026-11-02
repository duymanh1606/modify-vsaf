from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_requires_cloud_mode(mock_load: Mock, mock_build: Mock) -> None:
    """Test that Code Insights requires Cloud mode."""
    runner = _runner()
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-insights", "get", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code != 0
    # Exit code 1 indicates Cloud mode requirement failed
    mock_build.assert_not_called()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_get_requires_report_key(mock_load: Mock, mock_build: Mock) -> None:
    """Test that get requires --report-key."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-insights", "get", "PRJ", "repo", "abc123"])
    assert result.exit_code != 0
    assert "--report-key required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_get_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful Code Insights get."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.get_code_insights_report.return_value = {"title": "Test Report", "result": "PASSED"}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["code-insights", "get", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code == 0
    client.get_code_insights_report.assert_called_once_with("PRJ", "repo", "abc123", "test-report")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_create_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that create requires --yes."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "code-insights",
            "create",
            "PRJ",
            "repo",
            "abc123",
            "--report-key",
            "test-report",
            "--title",
            "Test",
            "--reporter",
            "test",
            "--result",
            "PASSED",
        ],
    )
    assert result.exit_code != 0
    assert "Refusing to create report without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_create_requires_title(mock_load: Mock, mock_build: Mock) -> None:
    """Test that create requires --title."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(
        app,
        [
            "code-insights",
            "create",
            "PRJ",
            "repo",
            "abc123",
            "--report-key",
            "test-report",
            "--reporter",
            "test",
            "--result",
            "PASSED",
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "--title required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_create_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful Code Insights create."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.create_code_insights_report.return_value = {"title": "Test Report", "result": "PASSED"}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-insights",
            "create",
            "PRJ",
            "repo",
            "abc123",
            "--report-key",
            "test-report",
            "--title",
            "Test Report",
            "--reporter",
            "test-reporter",
            "--result",
            "PASSED",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.create_code_insights_report.assert_called_once()
    call_kwargs = client.create_code_insights_report.call_args[1]
    assert call_kwargs["project_key"] == "PRJ"
    assert call_kwargs["repository_slug"] == "repo"
    assert call_kwargs["commit_id"] == "abc123"
    assert call_kwargs["report_key"] == "test-report"
    assert call_kwargs["report_title"] == "Test Report"
    assert call_kwargs["reporter"] == "test-reporter"
    assert call_kwargs["result"] == "PASSED"


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_create_with_data_file(mock_load: Mock, mock_build: Mock) -> None:
    """Test create with data file."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.create_code_insights_report.return_value = {"title": "Test Report"}
    mock_build.return_value.__enter__.return_value = client

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('[{"title": "Coverage", "type": "NUMBER", "value": 85}]')
        data_file = Path(f.name)

    try:
        result = runner.invoke(
            app,
            [
                "code-insights",
                "create",
                "PRJ",
                "repo",
                "abc123",
                "--report-key",
                "test-report",
                "--title",
                "Test Report",
                "--reporter",
                "test",
                "--result",
                "PASSED",
                "--data-file",
                str(data_file),
                "--yes",
            ],
        )
        assert result.exit_code == 0
        call_kwargs = client.create_code_insights_report.call_args[1]
        assert call_kwargs["data"] == [{"title": "Coverage", "type": "NUMBER", "value": 85}]
    finally:
        data_file.unlink()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_annotate_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that annotate requires --yes."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-insights", "annotate", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code != 0
    assert "Refusing to add annotations without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_annotate_requires_file(mock_load: Mock, mock_build: Mock) -> None:
    """Test that annotate requires --annotations-file."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(
        app, ["code-insights", "annotate", "PRJ", "repo", "abc123", "--report-key", "test-report", "--yes"]
    )
    assert result.exit_code != 0
    assert "--annotations-file required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_annotate_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful Code Insights annotate."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.add_code_insights_annotations_to_report.return_value = {"annotations": []}
    mock_build.return_value.__enter__.return_value = client

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('[{"path": "file.py", "line": 10, "severity": "HIGH"}]')
        annotations_file = Path(f.name)

    try:
        result = runner.invoke(
            app,
            [
                "code-insights",
                "annotate",
                "PRJ",
                "repo",
                "abc123",
                "--report-key",
                "test-report",
                "--annotations-file",
                str(annotations_file),
                "--yes",
            ],
        )
        assert result.exit_code == 0
        client.add_code_insights_annotations_to_report.assert_called_once_with(
            "PRJ", "repo", "abc123", "test-report", [{"path": "file.py", "line": 10, "severity": "HIGH"}]
        )
    finally:
        annotations_file.unlink()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_delete_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that delete requires --yes."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-insights", "delete", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code != 0
    assert "Refusing to delete report without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_delete_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful Code Insights delete."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app, ["code-insights", "delete", "PRJ", "repo", "abc123", "--report-key", "test-report", "--yes"]
    )
    assert result.exit_code == 0
    client.delete_code_insights_report.assert_called_once_with("PRJ", "repo", "abc123", "test-report")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_unknown_action(mock_load: Mock, mock_build: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-insights", "unknown", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_insights_client_error(mock_load: Mock, mock_build: Mock) -> None:
    """Test that client errors are handled."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.get_code_insights_report.side_effect = VDSClientError("Client error", context={})
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["code-insights", "get", "PRJ", "repo", "abc123", "--report-key", "test-report"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
