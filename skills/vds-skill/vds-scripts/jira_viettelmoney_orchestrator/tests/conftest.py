from __future__ import annotations

from pathlib import Path

import pytest
from vds_jira_orchestrator.config import JiraSettings


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime environment variables for testing."""
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "JIRA_TOKEN",
        "JIRA_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def write_env(tmp_path: Path, content: str) -> Path:
    """Write a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


@pytest.fixture
def mock_jira_settings() -> JiraSettings:
    """Create mock Jira settings for testing."""
    return JiraSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        JIRA_TOKEN="test_token",
        JIRA_BASE_URL="https://jira.test.com",
    )


@pytest.fixture
def sample_issue_response() -> dict[str, object]:
    """Sample Jira issue response."""
    return {
        "id": "10001",
        "key": "TEST-123",
        "fields": {
            "summary": "Test Issue",
            "description": "This is a test issue",
            "status": {"name": "Open"},
            "priority": {"name": "Medium"},
            "issuetype": {"name": "Task"},
            "project": {"key": "TEST", "name": "Test Project"},
        },
    }


@pytest.fixture
def sample_project_response() -> dict[str, object]:
    """Sample Jira project response."""
    return {
        "id": "10000",
        "key": "TEST",
        "name": "Test Project",
        "description": "A test project",
        "projectTypeKey": "software",
        "lead": {"displayName": "Test User"},
    }


@pytest.fixture
def sample_search_results() -> dict[str, object]:
    """Sample Jira search results."""
    return {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [
            {
                "id": "10001",
                "key": "TEST-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "Open"},
                    "priority": {"name": "Medium"},
                },
            }
        ],
    }
