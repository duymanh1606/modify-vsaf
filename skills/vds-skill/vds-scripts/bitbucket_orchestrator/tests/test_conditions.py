from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner
from vds_bitbucket_orchestrator.cli import app
from vds_bitbucket_orchestrator.errors import VDSClientError


def _runner() -> CliRunner:
    return CliRunner()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_list_project(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_project_conditions.return_value = []
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["conditions", "list", "PRJ"])
    assert result.exit_code == 0
    client.get_project_conditions.assert_called_once_with("PRJ")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_list_repo(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_repo_conditions.return_value = []
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["conditions", "list", "PRJ", "--repo", "repo"])
    assert result.exit_code == 0
    client.get_repo_conditions.assert_called_once_with("PRJ", "repo")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_get_repo(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()
    client = Mock()
    client.get_repo_condition.return_value = {"id": 5}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["conditions", "get", "PRJ", "--repo", "repo", "--condition-id", "5"])
    assert result.exit_code == 0
    client.get_repo_condition.assert_called_once_with("PRJ", "repo", 5)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_create_project(mock_load: Mock, mock_build: Mock, tmp_path: Path) -> None:
    runner = _runner()
    client = Mock()
    client.create_project_condition.return_value = {}
    mock_build.return_value.__enter__.return_value = client

    payload = {"sourceMatcher": {"id": "any"}}
    condition_file = tmp_path / "condition.json"
    condition_file.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        ["conditions", "create", "PRJ", "--condition-file", str(condition_file), "--yes"],
    )
    assert result.exit_code == 0
    client.create_project_condition.assert_called_once_with("PRJ", payload)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_create_requires_file(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()

    result = runner.invoke(
        app,
        ["conditions", "create", "PRJ", "--yes"],
    )
    assert result.exit_code != 0
    assert "--condition-file required for create" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_create_project_error(mock_load: Mock, mock_build: Mock, tmp_path: Path) -> None:
    runner = _runner()
    client = Mock()
    client.create_project_condition.side_effect = VDSClientError("fail")
    mock_build.return_value.__enter__.return_value = client

    payload = {"sourceMatcher": {"id": "any"}}
    condition_file = tmp_path / "condition.json"
    condition_file.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        ["conditions", "create", "PRJ", "--condition-file", str(condition_file), "--yes"],
    )
    assert result.exit_code != 0
    assert "bitbucket_error" in result.stdout


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_update_repo(mock_load: Mock, mock_build: Mock, tmp_path: Path) -> None:
    runner = _runner()
    client = Mock()
    client.update_repo_condition.return_value = {}
    mock_build.return_value.__enter__.return_value = client

    payload = {"targetMatcher": {"id": "refs/heads/main"}}
    condition_file = tmp_path / "condition.json"
    condition_file.write_text(json.dumps(payload))

    result = runner.invoke(
        app,
        [
            "conditions",
            "update",
            "PRJ",
            "--repo",
            "repo",
            "--condition-id",
            "11",
            "--condition-file",
            str(condition_file),
            "--yes",
        ],
    )
    assert result.exit_code == 0
    client.update_repo_condition.assert_called_once_with("PRJ", "repo", payload, 11)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_conditions_delete_requires_id(mock_load: Mock, mock_build: Mock) -> None:
    runner = _runner()

    result = runner.invoke(
        app,
        ["conditions", "delete", "PRJ", "--yes"],
    )
    assert result.exit_code != 0
    assert "--condition-id required for delete" in result.stdout
