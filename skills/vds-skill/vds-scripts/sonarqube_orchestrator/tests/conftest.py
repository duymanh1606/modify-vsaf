"""Shared fixtures for SonarQube orchestrator tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

# Add src directory to Python path at module load time
# This must happen before any test modules are imported
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


@pytest.fixture
def mock_settings_dict() -> dict[str, Any]:
    """Mock SonarQube settings."""
    return {
        "host_url": "http://sonar-test.example.com",
        "token": "test_token_12345",
        "user": None,
        "password": None,
        "project_key": "test-project",
        "branch_name": "main",
        "connect_timeout": 10.0,
        "request_timeout": 30.0,
        "max_retries": 3,
        "retry_backoff": 1.5,
        "verify_certs": False,
    }


@pytest.fixture
def sample_env_file(tmp_path: Path) -> Path:
    """Create a sample .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        """# SonarQube Test Configuration
VDS_SONAR_HOST_URL=http://sonar-test.example.com
VDS_SONAR_TOKEN=test_token_12345
VDS_SONAR_PROJECT_KEY=test-project
VDS_SONAR_BRANCH_NAME=main
"""
    )
    return env_file


@pytest.fixture
def sample_project_dir(tmp_path: Path) -> Path:
    """Create a sample Maven project directory for testing."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    (project_dir / "pom.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>test-project</artifactId>
    <version>1.0.0</version>
</project>
"""
    )
    return project_dir


@pytest.fixture
def mock_ping_response() -> dict[str, Any]:
    """Mock SonarQube ping response."""
    return {
        "id": "test-server",
        "version": "9.9.0.65466",
        "status": "UP",
    }


@pytest.fixture
def mock_project_response() -> dict[str, Any]:
    """Mock SonarQube project response."""
    return {
        "key": "test-project",
        "name": "Test Project",
        "qualifier": "TRK",
        "description": "A test project",
    }


@pytest.fixture
def mock_issues_response() -> list[dict[str, Any]]:
    """Mock SonarQube issues response."""
    return [
        {
            "key": "AX-GH1-JK2-LM3",
            "rule": "java:S117",
            "severity": "MINOR",
            "type": "CODE_SMELL",
            "status": "OPEN",
            "message": "Rename this local variable to match the regular expression",
        },
        {
            "key": "AX-GH1-JK2-LM4",
            "rule": "java:S106",
            "severity": "MAJOR",
            "type": "CODE_SMELL",
            "status": "OPEN",
            "message": "Remove this logging statement",
        },
    ]


@pytest.fixture
def mock_measures_response() -> dict[str, Any]:
    """Mock SonarQube measures response."""
    return {
        "bugs": "0",
        "vulnerabilities": "1",
        "code_smells": "5",
        "coverage": "75.5",
        "duplicated_lines_density": "2.3",
    }


@pytest.fixture
def mock_quality_gate_response() -> dict[str, Any]:
    """Mock SonarQube quality gate response."""
    return {
        "status": "OK",
        "conditions": [
            {"metric": "coverage", "operator": "LT", "value": "80", "status": "OK"},
            {"metric": "bugs", "operator": "GT", "value": "0", "status": "OK"},
        ],
    }
