"""Tests for grafana_orchestrator config module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vds_grafana_orchestrator.config import (
    GrafanaSettings,
    SettingsError,
    load_settings,
)


class TestGrafanaSettings:
    """Tests for GrafanaSettings class."""

    def test_settings_from_env_vars(self, mock_env: dict[str, str]) -> None:
        """Test loading settings from environment variables."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        assert settings.grafana_url == mock_env["VDS_GRAFANA_URL"]
        assert settings.user == mock_env["VDS_GRAFANA_USER"]
        assert settings.password == mock_env["VDS_GRAFANA_PASSWORD"]

    def test_settings_with_token_auth(self, mock_env_with_token: dict[str, str]) -> None:
        """Test loading settings with token authentication."""
        with (
            patch("vds_grafana_orchestrator.config.DEFAULT_ENV_PATHS", ()),
            patch.dict(os.environ, mock_env_with_token, clear=True),
        ):
            settings = GrafanaSettings()

        assert settings.grafana_url == mock_env_with_token["VDS_GRAFANA_URL"]
        assert settings.token == mock_env_with_token["VDS_GRAFANA_TOKEN"]
        assert settings.user is None
        assert settings.password is None

    def test_settings_with_datasource(self, mock_env_with_datasource: dict[str, str]) -> None:
        """Test loading settings with datasource configuration."""
        with patch.dict(os.environ, mock_env_with_datasource, clear=False):
            settings = GrafanaSettings()

        assert settings.datasource_uid == mock_env_with_datasource["VDS_GRAFANA_DATASOURCE_UID"]
        assert settings.default_index == mock_env_with_datasource["VDS_QUICKWIT_INDEX"]
        assert settings.has_datasource_config() is True

    def test_settings_default_values(self, mock_env: dict[str, str]) -> None:
        """Test default values for optional settings."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        assert settings.connect_timeout == 10.0
        assert settings.request_timeout == 30.0
        assert settings.max_retries == 3
        assert settings.retry_backoff == 1.0
        assert settings.verify_certs is False

    def test_base_url_strips_trailing_slash(self, mock_env: dict[str, str]) -> None:
        """Test that base_url strips trailing slashes."""
        env_with_slash = {**mock_env, "VDS_GRAFANA_URL": "http://test.local:3000/"}
        with patch.dict(os.environ, env_with_slash, clear=False):
            settings = GrafanaSettings()

        assert settings.base_url == "http://test.local:3000"

    def test_auth_header_basic_auth(self, mock_env: dict[str, str]) -> None:
        """Test auth_header returns Basic auth when user/password set."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        auth_header = settings.auth_header
        assert "Authorization" in auth_header
        assert auth_header["Authorization"].startswith("Basic ")

    def test_auth_header_bearer_token(self, mock_env_with_token: dict[str, str]) -> None:
        """Test auth_header returns Bearer token when token set."""
        with patch.dict(os.environ, mock_env_with_token, clear=False):
            settings = GrafanaSettings()

        auth_header = settings.auth_header
        assert "Authorization" in auth_header
        assert auth_header["Authorization"].startswith("Bearer ")

    def test_auth_header_empty_when_no_credentials(self) -> None:
        """Test auth_header returns empty dict when no credentials."""
        env = {"VDS_GRAFANA_URL": "http://test.local:3000"}
        with (
            patch("vds_grafana_orchestrator.config.DEFAULT_ENV_PATHS", ()),
            patch.dict(os.environ, env, clear=True),
        ):
            settings = GrafanaSettings()

        assert settings.auth_header == {}

    def test_require_credentials_with_basic_auth(self, mock_env: dict[str, str]) -> None:
        """Test require_credentials passes with basic auth."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        # Should not raise
        settings.require_credentials()

    def test_require_credentials_with_token(self, mock_env_with_token: dict[str, str]) -> None:
        """Test require_credentials passes with token."""
        with patch.dict(os.environ, mock_env_with_token, clear=False):
            settings = GrafanaSettings()

        # Should not raise
        settings.require_credentials()

    def test_require_credentials_raises_without_credentials(self) -> None:
        """Test require_credentials raises when no credentials set."""
        env = {"VDS_GRAFANA_URL": "http://test.local:3000"}
        with (
            patch("vds_grafana_orchestrator.config.DEFAULT_ENV_PATHS", ()),
            patch.dict(os.environ, env, clear=True),
        ):
            settings = GrafanaSettings()

        with pytest.raises(ValueError, match="Missing Grafana credentials"):
            settings.require_credentials()

    def test_has_datasource_config_false(self, mock_env: dict[str, str]) -> None:
        """Test has_datasource_config returns False when not configured."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        assert settings.has_datasource_config() is False

    def test_password_property_unwraps_secret(self, mock_env: dict[str, str]) -> None:
        """Test password property unwraps SecretStr."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = GrafanaSettings()

        # Should return plain string, not SecretStr
        assert settings.password == mock_env["VDS_GRAFANA_PASSWORD"]
        assert isinstance(settings.password, str)

    def test_token_property_unwraps_secret(self, mock_env_with_token: dict[str, str]) -> None:
        """Test token property unwraps SecretStr."""
        with patch.dict(os.environ, mock_env_with_token, clear=False):
            settings = GrafanaSettings()

        assert settings.token == mock_env_with_token["VDS_GRAFANA_TOKEN"]
        assert isinstance(settings.token, str)


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_settings_from_env(self, mock_env: dict[str, str]) -> None:
        """Test load_settings loads from environment."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = load_settings()

        assert settings.grafana_url == mock_env["VDS_GRAFANA_URL"]

    def test_load_settings_with_overrides(self, mock_env: dict[str, str]) -> None:
        """Test load_settings applies overrides."""
        with patch.dict(os.environ, mock_env, clear=False):
            settings = load_settings(overrides={"connect_timeout": 20.0})

        assert settings.connect_timeout == 20.0

    def test_load_settings_from_env_file(self, temp_env_file: Path) -> None:
        """Test load_settings loads from .env file."""
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_path=temp_env_file)

        assert "test.grafana.local" in settings.grafana_url

    def test_load_settings_strict_mode(self, mock_env: dict[str, str]) -> None:
        """Test load_settings validates credentials in strict mode."""
        with patch.dict(os.environ, mock_env, clear=False):
            # Should not raise - credentials are valid
            settings = load_settings(strict=True)
            assert settings is not None

    def test_load_settings_strict_mode_raises(self) -> None:
        """Test load_settings raises in strict mode without credentials."""
        env = {"VDS_GRAFANA_URL": "http://test.local:3000"}
        with (
            patch("vds_grafana_orchestrator.config.load_shared_env", return_value={}),
            patch("vds_grafana_orchestrator.config.DEFAULT_ENV_PATHS", ()),
            patch.dict(os.environ, env, clear=True),
        ):
            with pytest.raises(SettingsError, match="Missing Grafana credentials"):
                load_settings(strict=True)

    def test_load_settings_validation_error(self) -> None:
        """Test load_settings raises SettingsError on validation failure."""
        with (
            patch("vds_grafana_orchestrator.config.load_shared_env", return_value={}),
            patch("vds_grafana_orchestrator.config.DEFAULT_ENV_PATHS", ()),
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(SettingsError),
        ):
            load_settings()
