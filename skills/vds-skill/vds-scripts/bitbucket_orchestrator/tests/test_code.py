from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_file_requires_file(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["code", "file", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "--file required for file action" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_commits(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_commits.return_value = []
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["code", "commits", "PRJ", "repo", "--limit", "5"])
    assert result.exit_code == 0
    client.get_commits.assert_called_once_with("PRJ", "repo", None, None, limit=5)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_commits_error(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_commits.side_effect = VDSClientError("nope")
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["code", "commits", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "bitbucket_error" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_diff_requires_arguments(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["code", "diff", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "--file, --hash-oldest, and --hash-newest required" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_diff(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_diff.return_value = {"diff": "..."}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "code",
            "diff",
            "PRJ",
            "repo",
            "--file",
            "path/to/file.py",
            "--hash-oldest",
            "aaa",
            "--hash-newest",
            "bbb",
        ],
    )
    assert result.exit_code == 0
    client.get_diff.assert_called_once_with("PRJ", "repo", "path/to/file.py", "aaa", "bbb")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_code_changelog(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_changelog.return_value = []
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        ["code", "changelog", "PRJ", "repo", "--ref-from", "main", "--ref-to", "develop", "--limit", "10"],
    )
    assert result.exit_code == 0
    client.get_changelog.assert_called_once_with("PRJ", "repo", "main", "develop", limit=10)
