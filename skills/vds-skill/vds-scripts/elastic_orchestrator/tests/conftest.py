"""Pytest fixtures for elastic_orchestrator tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from vds_elastic_orchestrator.config import ElasticSettings


# Default test configuration values
TEST_KIBANA_URL = "test.kibana.local"
TEST_KIBANA_IP = "10.0.0.1"
TEST_USER = "testuser"
TEST_PASSWORD = "testpassword"


@pytest.fixture
def mock_env() -> dict[str, str]:
    """Return a dict of mock environment variables for testing."""
    return {
        "VDS_ELASTIC_KIBANA_URL": TEST_KIBANA_URL,
        "VDS_ELASTIC_KIBANA_IP": TEST_KIBANA_IP,
        "VDS_ELASTIC_USER": TEST_USER,
        "VDS_ELASTIC_PASSWORD": TEST_PASSWORD,
    }


@pytest.fixture
def mock_env_with_defaults(mock_env: dict[str, str]) -> dict[str, str]:
    """Return mock env with explicit default values."""
    return {
        **mock_env,
        "VDS_ELASTIC_CONNECT_TIMEOUT": "10",
        "VDS_ELASTIC_REQUEST_TIMEOUT": "30",
        "VDS_ELASTIC_MAX_RETRIES": "3",
        "VDS_ELASTIC_RETRY_BACKOFF": "1.0",
        "VDS_ELASTIC_VERIFY_CERTS": "false",
        "VDS_ELASTIC_DEFAULT_INDEX": "*",
        "VDS_ELASTIC_DEFAULT_TIME_FIELD": "@timestamp",
        "VDS_ELASTIC_DEFAULT_SIZE": "10",
    }


@pytest.fixture
def patched_env(mock_env: dict[str, str]) -> Generator[dict[str, str], None, None]:
    """Fixture that patches os.environ with mock values."""
    with patch.dict(os.environ, mock_env, clear=False):
        yield mock_env


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture that clears environment variables for testing."""
    with patch.dict(os.environ, {}, clear=True):
        yield


@pytest.fixture
def temp_env_file(tmp_path: Path) -> Path:
    """Create a temporary .env file for testing."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"""
VDS_ELASTIC_KIBANA_URL={TEST_KIBANA_URL}
VDS_ELASTIC_KIBANA_IP={TEST_KIBANA_IP}
VDS_ELASTIC_USER={TEST_USER}
VDS_ELASTIC_PASSWORD={TEST_PASSWORD}
"""
    )
    return env_file


@pytest.fixture
def settings(mock_env: dict[str, str]) -> ElasticSettings:
    """Create ElasticSettings instance with mock environment."""
    from vds_elastic_orchestrator.config import ElasticSettings

    with patch.dict(os.environ, mock_env, clear=False):
        return ElasticSettings()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create a mock ElasticSettings for client testing."""
    mock = MagicMock()
    mock.kibana_url = TEST_KIBANA_URL
    mock.kibana_ip = TEST_KIBANA_IP
    mock.user = TEST_USER
    mock.password = TEST_PASSWORD
    mock.connect_timeout = 10.0
    mock.request_timeout = 30.0
    mock.max_retries = 3
    mock.retry_backoff = 1.0
    mock.verify_certs = False
    mock.default_index = "*"
    mock.default_time_field = "@timestamp"
    mock.default_size = 10
    mock.base_url = f"https://{TEST_KIBANA_IP}"
    mock.proxy_endpoint = "/api/console/proxy"
    return mock


# Sample Elasticsearch responses for mocking
@pytest.fixture
def sample_search_response() -> dict[str, Any]:
    """Sample Elasticsearch search response."""
    return {
        "took": 15,
        "timed_out": False,
        "_shards": {"total": 5, "successful": 5, "skipped": 0, "failed": 0},
        "hits": {
            "total": {"value": 100, "relation": "eq"},
            "max_score": 1.0,
            "hits": [
                {
                    "_index": "logs-2025.01.15",
                    "_id": "1",
                    "_score": 1.0,
                    "_source": {
                        "@timestamp": "2025-01-15T12:00:00Z",
                        "message": "Test log message",
                        "level": "INFO",
                    },
                }
            ],
        },
    }


@pytest.fixture
def sample_count_response() -> dict[str, Any]:
    """Sample Elasticsearch count response."""
    return {
        "count": 1407366242,
        "_shards": {"total": 333, "successful": 333, "skipped": 0, "failed": 0},
    }


@pytest.fixture
def sample_cluster_info() -> dict[str, Any]:
    """Sample Elasticsearch cluster info response."""
    return {
        "name": "es-node-1",
        "cluster_name": "vds-production",
        "cluster_uuid": "abc123",
        "version": {
            "number": "8.11.0",
            "build_flavor": "default",
            "build_type": "docker",
        },
        "tagline": "You Know, for Search",
    }


@pytest.fixture
def sample_cluster_health() -> dict[str, Any]:
    """Sample Elasticsearch cluster health response."""
    return {
        "cluster_name": "vds-production",
        "status": "green",
        "timed_out": False,
        "number_of_nodes": 5,
        "number_of_data_nodes": 3,
        "active_primary_shards": 100,
        "active_shards": 200,
    }


@pytest.fixture
def sample_user_info() -> dict[str, Any]:
    """Sample Kibana user info response."""
    return {
        "username": "dev",
        "roles": ["viewer", "viewer-save-search"],
        "full_name": "Dev User",
        "email": "dev@example.com",
        "enabled": True,
    }


@pytest.fixture
def sample_kibana_status() -> dict[str, Any]:
    """Sample Kibana status response."""
    return {
        "name": "kibana",
        "uuid": "kibana-uuid-123",
        "version": {"number": "8.11.0"},
        "status": {
            "overall": {"level": "available"},
            "core": {"elasticsearch": {"level": "available"}},
        },
    }


@pytest.fixture
def sample_permission_error() -> dict[str, Any]:
    """Sample Elasticsearch permission error response."""
    return {
        "error": {
            "root_cause": [
                {
                    "type": "security_exception",
                    "reason": "action [cluster:monitor/health] requires [monitor] privilege",
                }
            ],
            "type": "security_exception",
            "reason": "action [cluster:monitor/health] requires [monitor] privilege",
        },
        "status": 403,
    }


@pytest.fixture
def sample_auth_error() -> dict[str, Any]:
    """Sample authentication error response."""
    return {
        "error": "Unauthorized",
        "message": "Invalid credentials",
        "statusCode": 401,
    }
