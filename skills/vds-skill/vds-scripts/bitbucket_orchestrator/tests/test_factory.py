"""Unit tests for factory functions (TSK-223).

Tests for create_client() and create_async_client() factory functions
that auto-load credentials from ~/.vds/.env.

References:
    - FR-21.2.2: Factory functions that load credentials from `~/.vds/.env` automatically
    - TSK-223: Factory functions for Bitbucket
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from vds_bitbucket_orchestrator.factory import (
    DEFAULT_VDS_ENV_PATH,
    create_async_client,
    create_client,
)
from vds_cli_common.paths import get_shared_env_path


def write_env(tmp_path: Path, content: str) -> Path:
    """Write a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime environment variables for testing."""
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "BITBUCKET_TOKEN",
        "VDS_BITBUCKET_URL",
        "BITBUCKET_BASE_URL",
        "VDS_BITBUCKET_HTTP_BASE",
        "BITBUCKET_CLOUD_WORKSPACE",
        "BITBUCKET_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


class TestDefaultEnvPath:
    """Test default environment path configuration."""

    def test_default_env_path_is_shared_env(self) -> None:
        """Test that default env path uses the shared VDS env helper."""
        expected = get_shared_env_path()
        assert expected == DEFAULT_VDS_ENV_PATH


class TestCreateClient:
    """Tests for create_client() factory function."""

    def test_create_client_with_valid_credentials(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test creating client with valid credentials from env file."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
BITBUCKET_MODE=server
""".strip(),
        )

        # Mock the BitbucketClient to avoid actual API calls
        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = create_client(env_path=env_path)

            # Verify client was created
            assert client is mock_instance
            mock_client.assert_called_once()

            # Verify settings were passed correctly
            call_args = mock_client.call_args
            settings = call_args[0][0]  # First positional arg
            assert settings.username == "test_user"
            assert settings.password == "test_pass"
            assert str(settings.base_url) == "https://bitbucket.test.com"
            assert settings.mode == "server"

    def test_create_client_with_token_auth(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test creating client with token authentication."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
BITBUCKET_TOKEN=test_token_12345
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = create_client(env_path=env_path)

            assert client is mock_instance
            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert settings.token == "test_token_12345"

    def test_create_client_mode_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that mode parameter overrides env file setting."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
BITBUCKET_MODE=server
BITBUCKET_CLOUD_WORKSPACE=testworkspace
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Override mode to cloud
            client = create_client(env_path=env_path, mode="cloud")

            assert client is mock_instance
            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert settings.mode == "cloud"

    def test_create_client_server_mode_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that server mode is the default when not specified."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            create_client(env_path=env_path)

            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert settings.mode == "server"

    def test_create_client_custom_timeout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test creating client with custom timeout."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            create_client(env_path=env_path, timeout=60)

            call_args = mock_client.call_args
            assert call_args.kwargs.get("timeout") == 60

    def test_create_client_strict_mode_fails_without_credentials(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that strict mode raises error when credentials are missing."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(tmp_path, "")

        with pytest.raises(ValueError, match="Missing credentials"):
            create_client(env_path=env_path, strict=True)

    def test_create_client_non_strict_mode_allows_missing_credentials(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that non-strict mode allows missing credentials."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        # Non-strict mode should not raise during settings load
        # But BitbucketClient will still validate credentials
        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # This should not raise during load_settings
            client = create_client(env_path=env_path, strict=False)
            assert client is mock_instance

    def test_create_client_cloud_mode(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test creating client in cloud mode."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
BITBUCKET_TOKEN=cloud_token
BITBUCKET_CLOUD_WORKSPACE=myworkspace
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            create_client(env_path=env_path, mode="cloud")

            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert settings.mode == "cloud"
            assert settings.cloud_workspace == "myworkspace"
            assert settings.is_cloud_mode


class TestCreateAsyncClient:
    """Tests for create_async_client() factory function."""

    def test_create_async_client_returns_async_client(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that create_async_client returns AsyncBitbucketClient (TSK-225 implemented)."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.AsyncBitbucketClient") as mock_async:
            with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient"):
                mock_instance = MagicMock()
                mock_async.return_value = mock_instance

                client = create_async_client(env_path=env_path)

                # Verify AsyncBitbucketClient was created (not NotImplementedError)
                assert client is mock_instance
                mock_async.assert_called_once()

    def test_create_async_client_passes_settings_and_timeout(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Test that create_async_client passes settings and timeout correctly."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.AsyncBitbucketClient") as mock_async:
            with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient"):
                mock_instance = MagicMock()
                mock_async.return_value = mock_instance

                create_async_client(env_path=env_path, timeout=60)

                call_args = mock_async.call_args
                settings = call_args[0][0]
                assert settings.username == "test_user"
                assert call_args.kwargs.get("timeout") == 60


class TestFactoryImports:
    """Test that factory functions are properly exported from package."""

    def test_factory_functions_importable_from_package(self) -> None:
        """Test that factory functions can be imported from package root."""
        from vds_bitbucket_orchestrator import create_async_client, create_client

        assert callable(create_client)
        assert callable(create_async_client)

    def test_default_env_path_importable(self) -> None:
        """Test that DEFAULT_VDS_ENV_PATH is accessible."""
        from vds_bitbucket_orchestrator.factory import DEFAULT_VDS_ENV_PATH

        assert isinstance(DEFAULT_VDS_ENV_PATH, Path)


class TestFactoryWithEnvVarPriority:
    """Test factory functions respect env var priority (FR-21.1.1)."""

    def test_factory_uses_primary_env_var(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that factory uses VDS_BITBUCKET_URL as primary."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://primary.bitbucket.com
BITBUCKET_BASE_URL=https://legacy.bitbucket.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            create_client(env_path=env_path)

            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert str(settings.base_url) == "https://primary.bitbucket.com"

    def test_factory_falls_back_to_legacy_env_var(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that factory falls back to BITBUCKET_BASE_URL."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
BITBUCKET_BASE_URL=https://legacy.bitbucket.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            create_client(env_path=env_path)

            call_args = mock_client.call_args
            settings = call_args[0][0]
            assert str(settings.base_url) == "https://legacy.bitbucket.com"
