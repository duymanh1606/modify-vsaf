from __future__ import annotations

import os
from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator import config as config_module
from vds_bitbucket_orchestrator.config import BitbucketSettings
from vds_bitbucket_orchestrator.errors import TransportError


@pytest.fixture(autouse=True)
def isolate_shared_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep whoever runs the suite out of its results.

    ``BitbucketSettings`` lists the shared env file (``~/.vds/.env``) among its sources,
    so on a machine with real credentials configured every test that builds settings
    without naming a field inherits that field. Two consequences, both seen for real: the
    assertion compares against the wrong value, and pytest prints both sides — putting a
    live personal access token in the output.

    ``DEFAULT_ENV_PATHS`` is evaluated at import time, so pointing ``HOME`` somewhere
    empty from inside a test is too late. The list has to be emptied where the config
    module reads it. Clearing the variables covers the shell-supplied case.
    """
    monkeypatch.setattr(config_module, "DEFAULT_ENV_PATHS", (), raising=False)
    for name in (
        "BITBUCKET_TOKEN",
        "BITBUCKET_ACCESS_TOKEN",
        "BITBUCKET_BASE_URL",
        "BITBUCKET_MODE",
        "BITBUCKET_CLOUD_WORKSPACE",
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "VDS_BITBUCKET_URL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    """Create server-mode settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_client_initialization_server_mode(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    """Client should initialize correctly in server mode."""
    client = BitbucketClient(mock_settings)
    assert client._settings == mock_settings
    assert client._settings.is_server_mode
    assert not client._settings.is_cloud_mode
    mock_bitbucket_class.assert_called_once()


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_client_initialization_cloud_mode(mock_bitbucket_class: Mock) -> None:
    """Client should initialize correctly in cloud mode."""
    settings = BitbucketSettings(
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_MODE="cloud",
        BITBUCKET_CLOUD_WORKSPACE="test_workspace",
    )
    client = BitbucketClient(settings)
    assert client._settings == settings
    assert client._settings.is_cloud_mode
    assert not client._settings.is_server_mode
    mock_bitbucket_class.assert_called_once()


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_list_projects_server_mode(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    client = BitbucketClient(mock_settings)
    mock_bitbucket = Mock()
    mock_bitbucket.project_list.return_value = [{"key": "TEST", "name": "Test Project"}]
    client._client = mock_bitbucket

    result = client.list_projects()

    assert result == [{"key": "TEST", "name": "Test Project"}]
    mock_bitbucket.project_list.assert_called_once_with(limit=25)


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_list_repositories_server_mode(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    client = BitbucketClient(mock_settings)
    mock_bitbucket = Mock()
    mock_bitbucket.repo_list.return_value = [{"slug": "test-repo", "name": "Test Repository"}]
    client._client = mock_bitbucket

    result = client.list_repositories("TEST")

    assert result == [{"slug": "test-repo", "name": "Test Repository"}]
    mock_bitbucket.repo_list.assert_called_once_with("TEST", limit=25)


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_get_project_server_mode(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    client = BitbucketClient(mock_settings)
    mock_bitbucket = Mock()
    mock_bitbucket.project.return_value = {"key": "TEST", "name": "Test Project"}
    client._client = mock_bitbucket

    result = client.get_project("TEST")

    assert result == {"key": "TEST", "name": "Test Project"}
    mock_bitbucket.project.assert_called_once_with("TEST")


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_get_repository_server_mode(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    client = BitbucketClient(mock_settings)
    mock_bitbucket = Mock()
    mock_bitbucket.get_repo.return_value = {"slug": "test-repo", "name": "Test Repository"}
    client._client = mock_bitbucket

    result = client.get_repository("TEST", "test-repo")

    assert result == {"slug": "test-repo", "name": "Test Repository"}
    mock_bitbucket.get_repo.assert_called_once_with("TEST", "test-repo")


def test_get_url_server_mode(mock_settings: BitbucketSettings) -> None:
    url = mock_settings.get_url()
    assert url == "https://bitbucket.test.com"


def test_get_url_cloud_mode() -> None:
    settings = BitbucketSettings(
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_MODE="cloud",
        BITBUCKET_CLOUD_WORKSPACE="test_workspace",
    )
    url = settings.get_url()
    assert url == "https://api.bitbucket.org/workspace/test_workspace"


def test_get_url_cloud_mode_missing_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BITBUCKET_CLOUD_WORKSPACE", raising=False)
    settings = BitbucketSettings(BITBUCKET_TOKEN="test_token", BITBUCKET_MODE="cloud")
    with pytest.raises(ValueError, match="BITBUCKET_CLOUD_WORKSPACE is required"):
        settings.get_url()


def test_get_auth_kwargs_with_token() -> None:
    settings = BitbucketSettings(BITBUCKET_TOKEN="test_token")
    auth_kwargs = settings.get_auth_kwargs()
    assert auth_kwargs == {"token": "test_token"}


def test_get_auth_kwargs_with_username_password() -> None:
    settings = BitbucketSettings(VDS_USERNAME="test_user", VDS_PASSWORD="test_pass")
    auth_kwargs = settings.get_auth_kwargs()
    assert auth_kwargs == {"username": "test_user", "password": "test_pass"}


@patch.dict(os.environ, {}, clear=True)
def test_get_auth_kwargs_no_credentials() -> None:
    settings = BitbucketSettings(
        VDS_USERNAME=None,
        VDS_PASSWORD=None,
        BITBUCKET_TOKEN=None,
    )
    with pytest.raises(ValueError, match="No valid authentication credentials"):
        settings.get_auth_kwargs()


def test_require_basic_or_token_success() -> None:
    settings = BitbucketSettings(BITBUCKET_TOKEN="test_token")
    settings.require_basic_or_token()


@patch.dict(os.environ, {}, clear=True)
def test_require_basic_or_token_failure() -> None:
    settings = BitbucketSettings(
        VDS_USERNAME=None,
        VDS_PASSWORD=None,
        BITBUCKET_TOKEN=None,
    )
    with pytest.raises(ValueError, match="Missing credentials"):
        settings.require_basic_or_token()


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_handle_api_error_classifies_timeout_as_transport(
    mock_bitbucket_class: Mock, mock_settings: BitbucketSettings
) -> None:
    client = BitbucketClient(mock_settings)
    with pytest.raises(TransportError, match="Transport error"):
        client._handle_api_error(TimeoutError("Read timed out"), "list_repositories TEST")


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_list_repositories_retries_on_timeout_then_succeeds(
    mock_bitbucket_class: Mock, mock_settings: BitbucketSettings
) -> None:
    client = BitbucketClient(mock_settings)
    client._max_retries = 1
    client._retry_backoff_factor = 0
    mock_bitbucket = Mock()
    mock_bitbucket.repo_list.side_effect = [
        TimeoutError("Read timed out"),
        [{"slug": "test-repo", "name": "Test Repository"}],
    ]
    client._client = mock_bitbucket

    result = client.list_repositories("TEST")

    assert result == [{"slug": "test-repo", "name": "Test Repository"}]
    assert mock_bitbucket.repo_list.call_count == 2


@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def test_get_commits_respects_limit_for_iterators(mock_bitbucket_class: Mock, mock_settings: BitbucketSettings) -> None:
    client = BitbucketClient(mock_settings)

    class _PagedCommits:
        def __iter__(self):
            for idx in range(1000):
                yield {"id": f"c{idx}"}

    mock_bitbucket = Mock()
    mock_bitbucket.get_commits.return_value = _PagedCommits()
    client._client = mock_bitbucket

    result = client.get_commits("TEST", "repo", limit=1)

    assert len(result) == 1
    assert result[0]["id"] == "c0"
