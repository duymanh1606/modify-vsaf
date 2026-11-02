from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_file_list_requires_project(mock_load: Mock, mock_build: Mock) -> None:
    """Test that file-list requires --project-key."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "file-list", "--repository-slug", "repo"])
    assert result.exit_code != 0
    assert "--project-key required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_file_list_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful file-list."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_file_list.return_value = [{"path": "file1.py"}, {"path": "file2.py"}]
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-advanced",
            "file-list",
            "--project-key",
            "PRJ",
            "--repository-slug",
            "repo",
            "--sub-folder",
            "src",
            "--query",
            "*.py",
        ],
    )
    assert result.exit_code == 0
    client.get_file_list.assert_called_once_with("PRJ", "repo", sub_folder="src", query="*.py", start=0, limit=None)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_commit_info_requires_commit(mock_load: Mock, mock_build: Mock) -> None:
    """Test that commit-info requires --commit."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "commit-info", "--project-key", "PRJ", "--repository-slug", "repo"])
    assert result.exit_code != 0
    assert "--commit required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_commit_info_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful commit-info."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_commit_info.return_value = {"id": "abc123", "message": "Test commit"}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-advanced",
            "commit-info",
            "--project-key",
            "PRJ",
            "--repository-slug",
            "repo",
            "--commit",
            "abc123",
            "--path",
            "file.py",
        ],
    )
    assert result.exit_code == 0
    client.get_commit_info.assert_called_once_with("PRJ", "repo", "abc123", path="file.py")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_commit_changes_requires_commit(mock_load: Mock, mock_build: Mock) -> None:
    """Test that commit-changes requires --commit-id or --hash-newest."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(
        app, ["code-advanced", "commit-changes", "--project-key", "PRJ", "--repository-slug", "repo"]
    )
    assert result.exit_code != 0
    assert "--commit-id or --hash-newest required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_commit_changes_with_commit_id(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful commit-changes with commit-id."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_commit_changes.return_value = {"changes": []}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-advanced",
            "commit-changes",
            "--project-key",
            "PRJ",
            "--repository-slug",
            "repo",
            "--commit-id",
            "abc123",
            "--merges",
            "exclude",
        ],
    )
    assert result.exit_code == 0
    client.get_commit_changes.assert_called_once_with(
        "PRJ", "repo", commit_id="abc123", hash_newest=None, merges="exclude"
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_commit_changes_with_hash_newest(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful commit-changes with hash-newest."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_commit_changes.return_value = {"changes": []}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-advanced",
            "commit-changes",
            "--project-key",
            "PRJ",
            "--repository-slug",
            "repo",
            "--hash-newest",
            "def456",
        ],
    )
    assert result.exit_code == 0
    client.get_commit_changes.assert_called_once_with(
        "PRJ", "repo", commit_id=None, hash_newest="def456", merges="include"
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_search_requires_cloud_mode(mock_load: Mock, mock_build: Mock) -> None:
    """Test that search requires Cloud mode."""
    runner = _runner()
    settings = Mock()
    settings.is_cloud_mode = False
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "search", "--team", "workspace", "--search-query", "test"])
    assert result.exit_code != 0
    # Exit code 1 indicates Cloud mode requirement failed


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_search_requires_team(mock_load: Mock, mock_build: Mock) -> None:
    """Test that search requires --team."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "search", "--search-query", "test"])
    assert result.exit_code != 0
    assert "--team required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_search_requires_query(mock_load: Mock, mock_build: Mock) -> None:
    """Test that search requires --search-query."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "search", "--team", "workspace"])
    assert result.exit_code != 0
    assert "--search-query required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_search_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful code search."""
    runner = _runner()
    settings = Mock(is_cloud_mode=True)
    mock_load.return_value = settings

    client = Mock()
    client.search_code.return_value = {"values": [{"file": {"path": "file.py"}}]}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code-advanced",
            "search",
            "--team",
            "workspace",
            "--search-query",
            "def test",
            "--page",
            "2",
            "--limit",
            "20",
        ],
    )
    assert result.exit_code == 0
    client.search_code.assert_called_once_with("workspace", "def test", page=2, limit=20)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_unknown_action(mock_load: Mock, mock_build: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["code-advanced", "unknown"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_advanced_client_error(mock_load: Mock, mock_build: Mock) -> None:
    """Test that client errors are handled."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_file_list.side_effect = VDSClientError("Client error", context={})
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["code-advanced", "file-list", "--project-key", "PRJ", "--repository-slug", "repo"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
