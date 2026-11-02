"""Unit tests for command routing.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
Key Features: Fixtures, mocking
"""

import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from vds_cli.router import ORCHESTRATORS, run_orchestrator


def test_orchestrators_dict() -> None:
    """Test ORCHESTRATORS dictionary structure."""
    assert "jira" in ORCHESTRATORS
    assert "confluence" in ORCHESTRATORS
    assert "bitbucket" in ORCHESTRATORS
    assert "git" in ORCHESTRATORS

    for _name, config in ORCHESTRATORS.items():
        assert "module" in config
        assert "path" in config
        assert isinstance(config["module"], str)
        assert isinstance(config["path"], str)


def test_run_orchestrator_invalid_service(mock_script_dir: Path) -> None:
    """Test run_orchestrator with invalid service name."""
    with pytest.raises(ValueError, match="Unknown service"):
        run_orchestrator("invalid", [], mock_script_dir)


def test_run_orchestrator_missing_directory(mock_script_dir: Path) -> None:
    """Test run_orchestrator when orchestrator directory doesn't exist."""
    # Remove one orchestrator directory
    shutil.rmtree(mock_script_dir / "jira_orchestrator")

    with pytest.raises(FileNotFoundError, match="not found"):
        run_orchestrator("jira", [], mock_script_dir)


def test_run_orchestrator_missing_declared_entry(mock_script_dir: Path) -> None:
    """Test run_orchestrator fails when router entry is not declared in project scripts."""
    jira_pyproject = mock_script_dir / "jira_orchestrator" / "pyproject.toml"
    jira_pyproject.write_text(
        '[project]\nname = "mock-orchestrator"\nversion = "0.0.1"\n[project.scripts]\nother-entry = "mock.cli:app"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="not runnable"):
        run_orchestrator("jira", [], mock_script_dir)


@patch("vds_cli.router.subprocess.run")
def test_run_orchestrator_success(mock_subprocess: Mock, mock_script_dir: Path) -> None:
    """Test successful orchestrator execution."""
    mock_subprocess.return_value = Mock(returncode=0)

    exit_code = run_orchestrator("jira", ["search", "project = NTTC"], mock_script_dir)

    assert exit_code == 0
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "uv" in call_args
    assert "--project" in call_args
    assert "jira_orchestrator" in str(call_args)
    # entry point usage check
    assert "vds-jira-cli" in call_args
    assert "search" in call_args
    assert "project = NTTC" in call_args


@patch("vds_cli.router.subprocess.run")
def test_run_orchestrator_failure(mock_subprocess: Mock, mock_script_dir: Path) -> None:
    """Test orchestrator execution with non-zero exit code."""
    mock_subprocess.return_value = Mock(returncode=1)

    exit_code = run_orchestrator("confluence", ["content", "search"], mock_script_dir)

    assert exit_code == 1


@patch("vds_cli.router.subprocess.run")
def test_run_orchestrator_includes_venv_site_packages(mock_subprocess: Mock, mock_script_dir: Path) -> None:
    """Test that PYTHONPATH includes workspace .venv site-packages when present."""
    mock_subprocess.return_value = Mock(returncode=0)
    # Create a fake .venv/lib/python3.12/site-packages in the script_dir
    site_packages = mock_script_dir / ".venv" / "lib" / "python3.12" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)

    run_orchestrator("jira", [], mock_script_dir)

    call_kwargs = mock_subprocess.call_args[1]
    python_path = call_kwargs["env"]["PYTHONPATH"]
    assert "site-packages" in python_path
    assert str(site_packages) in python_path


