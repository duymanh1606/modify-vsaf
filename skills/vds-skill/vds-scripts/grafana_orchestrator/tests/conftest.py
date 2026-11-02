"""Pytest fixtures for grafana_orchestrator tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from vds_grafana_orchestrator.config import GrafanaSettings


# Default test configuration values
TEST_GRAFANA_URL = "http://test.grafana.local:3000"
TEST_GRAFANA_USER = "testuser"
TEST_GRAFANA_PASSWORD = "testpassword"
TEST_GRAFANA_TOKEN = "test-token-123"
TEST_DATASOURCE_UID = "test-ds-uid"
TEST_DATASOURCE_ID = 59
TEST_DATASOURCE_NAME = "Quickwit-TEST"
TEST_DEFAULT_INDEX = "otel-logs-v0_7"


@pytest.fixture
def mock_env() -> dict[str, str]:
    """Return a dict of mock environment variables for testing."""
    return {
        "VDS_GRAFANA_URL": TEST_GRAFANA_URL,
        "VDS_GRAFANA_USER": TEST_GRAFANA_USER,
        "VDS_GRAFANA_PASSWORD": TEST_GRAFANA_PASSWORD,
    }


@pytest.fixture
def mock_env_with_token() -> dict[str, str]:
    """Return mock env with token auth instead of basic auth."""
    return {
        "VDS_GRAFANA_URL": TEST_GRAFANA_URL,
        "VDS_GRAFANA_TOKEN": TEST_GRAFANA_TOKEN,
    }


@pytest.fixture
def mock_env_with_datasource(mock_env: dict[str, str]) -> dict[str, str]:
    """Return mock env with datasource configuration."""
    return {
        **mock_env,
        "VDS_GRAFANA_DATASOURCE_UID": TEST_DATASOURCE_UID,
        "VDS_QUICKWIT_INDEX": TEST_DEFAULT_INDEX,
    }


@pytest.fixture
def mock_env_with_defaults(mock_env: dict[str, str]) -> dict[str, str]:
    """Return mock env with explicit default values."""
    return {
        **mock_env,
        "VDS_GRAFANA_CONNECT_TIMEOUT": "10",
        "VDS_GRAFANA_REQUEST_TIMEOUT": "30",
        "VDS_GRAFANA_MAX_RETRIES": "3",
        "VDS_GRAFANA_RETRY_BACKOFF": "1.0",
        "VDS_GRAFANA_VERIFY_CERTS": "false",
        "VDS_GRAFANA_DATASOURCE_UID": TEST_DATASOURCE_UID,
        "VDS_QUICKWIT_INDEX": TEST_DEFAULT_INDEX,
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
VDS_GRAFANA_URL={TEST_GRAFANA_URL}
VDS_GRAFANA_USER={TEST_GRAFANA_USER}
VDS_GRAFANA_PASSWORD={TEST_GRAFANA_PASSWORD}
VDS_GRAFANA_DATASOURCE_UID={TEST_DATASOURCE_UID}
VDS_QUICKWIT_INDEX={TEST_DEFAULT_INDEX}
"""
    )
    return env_file


@pytest.fixture
def settings(mock_env: dict[str, str]) -> GrafanaSettings:
    """Create GrafanaSettings instance with mock environment."""
    from vds_grafana_orchestrator.config import GrafanaSettings

    with patch.dict(os.environ, mock_env, clear=False):
        return GrafanaSettings()


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create a mock GrafanaSettings for client testing."""
    mock = MagicMock()
    mock.grafana_url = TEST_GRAFANA_URL
    mock.base_url = TEST_GRAFANA_URL.rstrip("/")
    mock.user = TEST_GRAFANA_USER
    mock.password = TEST_GRAFANA_PASSWORD
    mock.token = None
    mock.auth_header = {"Authorization": "Basic dGVzdHVzZXI6dGVzdHBhc3N3b3Jk"}
    mock.datasource_uid = TEST_DATASOURCE_UID
    mock.datasource_id = None
    mock.datasource_name = None
    mock.default_index = TEST_DEFAULT_INDEX
    mock.connect_timeout = 10.0
    mock.request_timeout = 30.0
    mock.max_retries = 3
    mock.retry_backoff = 1.0
    mock.verify_certs = False
    mock.has_datasource_config.return_value = True
    return mock


# Sample Grafana/Quickwit responses for mocking
@pytest.fixture
def sample_grafana_health() -> dict[str, Any]:
    """Sample Grafana health response."""
    return {
        "commit": "abc123def",
        "database": "ok",
        "version": "10.0.0",
    }


@pytest.fixture
def sample_datasources() -> list[dict[str, Any]]:
    """Sample Grafana datasources list."""
    return [
        {
            "id": 59,
            "uid": "cditnbnbvzugwb",
            "orgId": 1,
            "name": "Quickwit-PRODUCTION",
            "type": "quickwit-quickwit-datasource",
            "typeName": "Quickwit",
            "typeLogoUrl": "",
            "access": "proxy",
            "url": "http://quickwit-apr24.digital.int:21050/api/v1",
            "user": "",
            "database": "",
            "basicAuth": False,
            "isDefault": False,
            "jsonData": {"index": "otel-logs-v0_7"},
            "readOnly": False,
        },
        {
            "id": 60,
            "uid": "dditnbp6calmoe",
            "orgId": 1,
            "name": "Quickwit-UAT",
            "type": "quickwit-quickwit-datasource",
            "typeName": "Quickwit",
            "typeLogoUrl": "",
            "access": "proxy",
            "url": "http://quickwit-uat.digital.int:21050/api/v1",
            "user": "",
            "database": "",
            "basicAuth": False,
            "isDefault": False,
            "jsonData": {"index": "otel-logs-v0_7"},
            "readOnly": False,
        },
        {
            "id": 1,
            "uid": "prometheus",
            "orgId": 1,
            "name": "Prometheus",
            "type": "prometheus",
            "typeName": "Prometheus",
            "access": "proxy",
            "url": "http://prometheus:9090",
            "basicAuth": False,
            "isDefault": True,
            "jsonData": {},
            "readOnly": False,
        },
    ]


@pytest.fixture
def sample_quickwit_search_response() -> dict[str, Any]:
    """Sample Quickwit REST search response."""
    return {
        "num_hits": 100,
        "hits": [
            {
                "timestamp": 1705320000000000000,
                "service_name": "api-gateway",
                "severity_text": "INFO",
                "body": "Request processed successfully",
                "trace_id": "abc123",
                "span_id": "def456",
            },
            {
                "timestamp": 1705319900000000000,
                "service_name": "payment-service",
                "severity_text": "ERROR",
                "body": "Payment failed: timeout",
                "trace_id": "ghi789",
                "span_id": "jkl012",
            },
        ],
        "elapsed_time_micros": 15234,
        "errors": [],
    }


@pytest.fixture
def sample_es_search_response() -> dict[str, Any]:
    """Sample Quickwit ES-compatible search response."""
    return {
        "took": 15,
        "timed_out": False,
        "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
        "hits": {
            "total": {"value": 100, "relation": "eq"},
            "max_score": 1.0,
            "hits": [
                {
                    "_index": "otel-logs-v0_7",
                    "_id": "1",
                    "_score": 1.0,
                    "_source": {
                        "timestamp": 1705320000000000000,
                        "service_name": "api-gateway",
                        "severity_text": "INFO",
                        "body": "Request processed successfully",
                    },
                }
            ],
        },
    }


@pytest.fixture
def sample_cat_indices_response() -> list[dict[str, Any]]:
    """Sample ES-compatible _cat/indices response."""
    return [
        {
            "health": "green",
            "status": "open",
            "index": "otel-logs-v0_7",
            "uuid": "abc123",
            "pri": "1",
            "rep": "0",
            "docs.count": "1000000",
            "docs.deleted": "0",
            "store.size": "500mb",
            "pri.store.size": "500mb",
        },
        {
            "health": "green",
            "status": "open",
            "index": "otel-traces-v0_7",
            "uuid": "def456",
            "pri": "1",
            "rep": "0",
            "docs.count": "500000",
            "docs.deleted": "0",
            "store.size": "250mb",
            "pri.store.size": "250mb",
        },
    ]


@pytest.fixture
def sample_permission_error() -> dict[str, Any]:
    """Sample Grafana permission error response."""
    return {
        "message": "Access denied to this resource",
        "status": "Forbidden",
    }


@pytest.fixture
def sample_auth_error() -> dict[str, Any]:
    """Sample authentication error response."""
    return {
        "message": "Invalid username or password",
    }


@pytest.fixture
def sample_not_found_error() -> dict[str, Any]:
    """Sample not found error response."""
    return {
        "message": "Datasource not found",
    }
