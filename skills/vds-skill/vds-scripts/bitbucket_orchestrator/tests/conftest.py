from __future__ import annotations

from pathlib import Path

import pytest
from vds_bitbucket_orchestrator.config import BitbucketSettings


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime environment variables for testing."""
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "BITBUCKET_TOKEN",
        "BITBUCKET_BASE_URL",
        "BITBUCKET_CLOUD_WORKSPACE",
        "BITBUCKET_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


def write_env(tmp_path: Path, content: str) -> Path:
    """Write a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


@pytest.fixture
def mock_bitbucket_settings() -> BitbucketSettings:
    """Create mock Bitbucket settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


@pytest.fixture
def sample_project_response() -> dict[str, object]:
    """Sample Bitbucket project response."""
    return {
        "key": "TEST",
        "name": "Test Project",
        "description": "A test project",
        "type": "NORMAL",
        "public": False,
        "links": {"self": {"href": "https://bitbucket.test.com/projects/TEST"}},
    }


@pytest.fixture
def sample_repository_response() -> dict[str, object]:
    """Sample Bitbucket repository response."""
    return {
        "slug": "test-repo",
        "name": "Test Repository",
        "description": "A test repository",
        "scm": "git",
        "state": "AVAILABLE",
        "public": False,
        "links": {"self": {"href": "https://bitbucket.test.com/projects/TEST/repos/test-repo"}},
    }
