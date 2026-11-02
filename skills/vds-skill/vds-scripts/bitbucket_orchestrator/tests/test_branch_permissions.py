from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_get(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_branch_permission.return_value = {"id": 1}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["branch-permissions", "get", "PRJ", "--permission-id", "1"])
    assert result.exit_code == 0
    client.get_branch_permission.assert_called_once_with("PRJ", 1, repository_slug=None)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_get_requires_id(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()

    result = runner.invoke(app, ["branch-permissions", "get", "PRJ"])
    assert result.exit_code != 0
    assert "--permission-id required for get" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_set_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    result = runner.invoke(
        app,
        [
            "branch-permissions",
            "set",
            "PRJ",
            "--matcher-type",
            "BRANCH",
            "--matcher-value",
            "refs/heads/master",
            "--permission-type",
            "READ_ONLY",
        ],
    )
    assert result.exit_code != 0
    assert "Refusing to set permissions without --yes" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_set_success(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.set_branches_permissions.return_value = {}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "branch-permissions",
            "set",
            "PRJ",
            "--matcher-type",
            "BRANCH",
            "--matcher-value",
            "refs/heads/master",
            "--permission-type",
            "READ_ONLY",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.set_branches_permissions.assert_called_once_with(
        "PRJ",
        matcher_type="BRANCH",
        matcher_value="refs/heads/master",
        permission_type="READ_ONLY",
        repository_slug=None,
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_set_passes_repository(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.set_branches_permissions.return_value = {}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "branch-permissions",
            "set",
            "PRJ",
            "--repo",
            "app-repo",
            "--matcher-type",
            "BRANCH",
            "--matcher-value",
            "refs/heads/develop",
            "--permission-type",
            "WRITE",
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.set_branches_permissions.assert_called_once_with(
        "PRJ",
        matcher_type="BRANCH",
        matcher_value="refs/heads/develop",
        permission_type="WRITE",
        repository_slug="app-repo",
    )


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_set_error(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.set_branches_permissions.side_effect = VDSClientError("oops")
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(
        app,
        [
            "branch-permissions",
            "set",
            "PRJ",
            "--matcher-type",
            "BRANCH",
            "--matcher-value",
            "refs/heads/master",
            "--permission-type",
            "READ_ONLY",
            "--yes",
        ],
    )
    assert result.exit_code != 0
    assert "bitbucket_error" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_delete_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    result = runner.invoke(app, ["branch-permissions", "delete", "PRJ", "--permission-id", "7"])
    assert result.exit_code != 0
    assert "Refusing to delete without --yes" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_branch_permissions_delete_success(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["branch-permissions", "delete", "PRJ", "--permission-id", "7", "--yes"])
    assert result.exit_code == 0
    client.delete_branch_permission.assert_called_once_with("PRJ", 7, repository_slug=None)
