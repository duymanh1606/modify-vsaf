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
def test_repo_settings_branching_model_get(mock_load: Mock, mock_build: Mock) -> None:
    """Test branching model get."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_branching_model.return_value = {"development": {"branch": {"name": "develop"}}}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "branching-model", "get", "PRJ", "repo"])
    assert result.exit_code == 0
    client.get_branching_model.assert_called_once_with("PRJ", "repo")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_branching_model_set_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that branching model set requires --yes."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"development": {"branch": {"name": "develop"}}}')
        model_file = Path(f.name)

    try:
        result = runner.invoke(
            app, ["repo-settings", "branching-model", "set", "PRJ", "repo", "--model-file", str(model_file)]
        )
        assert result.exit_code != 0
        assert "Refusing to set branching model without --yes" in result.stderr
    finally:
        model_file.unlink()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_branching_model_set_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful branching model set."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.set_branching_model.return_value = {"development": {"branch": {"name": "develop"}}}
    mock_build.return_value.__enter__.return_value = client

    with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"development": {"branch": {"name": "develop"}}}')
        model_file = Path(f.name)

    try:
        result = runner.invoke(
            app,
            [
                "repo-settings",
                "branching-model",
                "set",
                "PRJ",
                "repo",
                "--model-file",
                str(model_file),
                "--yes",
            ],
        )
        assert result.exit_code == 0
        client.set_branching_model.assert_called_once()
        call_args = client.set_branching_model.call_args
        assert call_args[0][0] == "PRJ"
        assert call_args[0][1] == "repo"
        assert call_args[0][2] == {"development": {"branch": {"name": "develop"}}}
    finally:
        model_file.unlink()


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_default_branch_get(mock_load: Mock, mock_build: Mock) -> None:
    """Test default branch get."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_default_branch.return_value = {"id": "refs/heads/main"}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "default-branch", "get", "PRJ", "repo"])
    assert result.exit_code == 0
    client.get_default_branch.assert_called_once_with("PRJ", "repo")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_default_branch_set_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that default branch set requires --yes."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "default-branch", "set", "PRJ", "repo", "--branch", "main"])
    assert result.exit_code != 0
    assert "Refusing to set default branch without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_default_branch_set_requires_branch(mock_load: Mock, mock_build: Mock) -> None:
    """Test that default branch set requires --branch."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "default-branch", "set", "PRJ", "repo", "--yes"])
    assert result.exit_code != 0
    assert "--branch required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_default_branch_set_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful default branch set."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.set_default_branch.return_value = {"id": "refs/heads/main"}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "default-branch", "set", "PRJ", "repo", "--branch", "main", "--yes"])
    assert result.exit_code == 0
    client.set_default_branch.assert_called_once_with("PRJ", "repo", "main")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_hooks_get(mock_load: Mock, mock_build: Mock) -> None:
    """Test hooks get."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_repo_hook_settings.return_value = [{"key": "hook1", "enabled": True}]
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "hooks", "get", "PRJ", "repo"])
    assert result.exit_code == 0
    client.get_repo_hook_settings.assert_called_once_with("PRJ", "repo", start=0, limit=None, filter_type=None)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_hooks_enable_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that hooks enable requires --yes."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "hooks", "enable", "PRJ", "repo", "--hook-key", "hook1"])
    assert result.exit_code != 0
    assert "Refusing to enable hook without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_hooks_enable_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful hooks enable."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.enable_repo_hook_settings.return_value = {"key": "hook1", "enabled": True}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "hooks", "enable", "PRJ", "repo", "--hook-key", "hook1", "--yes"])
    assert result.exit_code == 0
    client.enable_repo_hook_settings.assert_called_once_with("PRJ", "repo", "hook1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_hooks_disable_success(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful hooks disable."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.disable_repo_hook_settings.return_value = {"key": "hook1", "enabled": False}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "hooks", "disable", "PRJ", "repo", "--hook-key", "hook1", "--yes"])
    assert result.exit_code == 0
    client.disable_repo_hook_settings.assert_called_once_with("PRJ", "repo", "hook1")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_lfs_get(mock_load: Mock, mock_build: Mock) -> None:
    """Test LFS get."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_lfs_repo_status.return_value = {"enabled": True}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "lfs", "get", "PRJ", "repo"])
    assert result.exit_code == 0
    client.get_lfs_repo_status.assert_called_once_with("PRJ", "repo")


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_lfs_set_requires_yes(mock_load: Mock, mock_build: Mock) -> None:
    """Test that LFS set requires --yes."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "lfs", "set", "PRJ", "repo", "--enabled"])
    assert result.exit_code != 0
    assert "Refusing to set LFS status without --yes" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_lfs_set_requires_enabled_flag(mock_load: Mock, mock_build: Mock) -> None:
    """Test that LFS set requires --enabled or --disabled."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "lfs", "set", "PRJ", "repo", "--yes"])
    assert result.exit_code != 0
    assert "--enabled or --disabled required" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_lfs_set_enabled(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful LFS set enabled."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.set_lfs_repo_status.return_value = {"enabled": True}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "lfs", "set", "PRJ", "repo", "--enabled", "--yes"])
    assert result.exit_code == 0
    client.set_lfs_repo_status.assert_called_once_with("PRJ", "repo", True)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_lfs_set_disabled(mock_load: Mock, mock_build: Mock) -> None:
    """Test successful LFS set disabled."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.set_lfs_repo_status.return_value = {"enabled": False}
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "lfs", "set", "PRJ", "repo", "--disabled", "--yes"])
    assert result.exit_code == 0
    client.set_lfs_repo_status.assert_called_once_with("PRJ", "repo", False)


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_unknown_category(mock_load: Mock, mock_build: Mock) -> None:
    """Test that unknown category raises error."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "unknown", "get", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "Unknown category" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_unknown_action(mock_load: Mock, mock_build: Mock) -> None:
    """Test that unknown action raises error."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    result = runner.invoke(app, ["repo-settings", "branching-model", "unknown", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stderr


@patch("vds_bitbucket_orchestrator.cli._build_client")
@patch("vds_bitbucket_orchestrator.cli.load_settings")
def test_repo_settings_client_error(mock_load: Mock, mock_build: Mock) -> None:
    """Test that client errors are handled."""
    runner = _runner()
    settings = Mock()
    mock_load.return_value = settings

    client = Mock()
    client.get_branching_model.side_effect = VDSClientError("Client error", context={})
    mock_build.return_value.__enter__.return_value = client

    result = runner.invoke(app, ["repo-settings", "branching-model", "get", "PRJ", "repo"])
    assert result.exit_code != 0
    assert "Error" in result.stderr
