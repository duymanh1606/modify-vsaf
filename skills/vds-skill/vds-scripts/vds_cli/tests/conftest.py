"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def mock_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".vds" / ".env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        "VDS_USERNAME=test_user\n"
        "VDS_PASSWORD=test_pass\n"
        "BITBUCKET_ACCESS_TOKEN=test_token\n"
        "INTERNAL_CONFLUENCE_TOKEN=test_internal\n"
        "EXTERNAL_CONFLUENCE_TOKEN=test_external\n"
    )
    # Mock Path.home() to return our test directory
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return env_file


@pytest.fixture
def mock_script_dir(tmp_path: Path) -> Path:
    """Create a mock scripts directory with orchestrators."""
    orchestrators = {
        "jira_orchestrator": "vds-jira-cli",
        "confluence_orchestrator": "vds-confluence-cli",
        "bitbucket_orchestrator": "vds-bitbucket-cli",
        "git_orchestrator": "vds-git-orchestrator",
        "spec_orchestrator": "vds-spec",
        "circular_dependency_orchestrator": "vds-circular-dependency",
        "vds_evolution": "vds-evolution",
    }
    for name, entry in orchestrators.items():
        project_dir = tmp_path / name
        project_dir.mkdir(parents=True, exist_ok=True)
        src_module_dir = project_dir / "src" / "mock"
        src_module_dir.mkdir(parents=True, exist_ok=True)
        (src_module_dir / "__init__.py").write_text("", encoding="utf-8")
        (src_module_dir / "cli.py").write_text("def app() -> None:\n    return None\n", encoding="utf-8")
        (project_dir / "pyproject.toml").write_text(
            f'[project]\nname = "mock-orchestrator"\nversion = "0.0.1"\n[project.scripts]\n{entry} = "mock.cli:app"\n',
            encoding="utf-8",
        )
    return tmp_path


@pytest.fixture
def mock_home_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock home directory for environment file."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def credentials_available() -> bool:
    """Check if real credentials are available for verification tests."""
    return bool(os.getenv("VDS_USERNAME") and os.getenv("VDS_PASSWORD") and os.getenv("BITBUCKET_ACCESS_TOKEN"))
