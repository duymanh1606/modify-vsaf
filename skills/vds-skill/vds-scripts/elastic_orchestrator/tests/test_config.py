"""Tests for Elasticsearch configuration module.

Tests cover:
- Settings loading from environment variables
- Settings loading from .env files
- SecretStr handling for passwords
- Validation of required fields
- Default values for optional fields
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vds_elastic_orchestrator.config import (
    DEFAULT_ENV_PATHS,
    ElasticSettings,
    SettingsError,
    load_settings,
)


class TestElasticSettings:
    """Tests for ElasticSettings model."""

    def test_required_fields_from_env(self):
        """Test loading required fields from environment variables."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            assert settings.kibana_url == "log.digital.vn"
            assert settings.kibana_ip == "10.207.56.26"
            assert settings.user == "testuser"
            assert settings.password == "testpass"

    def test_password_secret_str(self):
        """Test that password is stored as SecretStr."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            # SecretStr should not reveal value in str representation
            assert "secret123" not in str(settings.password_secret)
            assert "secret123" not in repr(settings.password_secret)
            # But get_secret_value() should return actual value
            assert settings.password_secret.get_secret_value() == "secret123"
            # Property wrapper should also work
            assert settings.password == "secret123"

    def test_default_values(self):
        """Test default values for optional fields."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            # Check defaults
            assert settings.connect_timeout == 10.0
            assert settings.request_timeout == 30.0
            assert settings.max_retries == 3
            assert settings.retry_backoff == 1.0
            assert settings.verify_certs is False
            assert settings.default_index == "*"
            assert settings.default_time_field == "@timestamp"
            assert settings.default_size == 10

    def test_custom_timeout_values(self):
        """Test overriding default timeout values via overrides dict."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            # Use overrides to set timeout values (avoids load_shared_env env-var clobbering)
            overrides = {
                "connect_timeout": 5.0,
                "request_timeout": 60.0,
                "max_retries": 5,
                "retry_backoff": 2.0,
            }
            settings = load_settings(overrides=overrides)
            assert settings.connect_timeout == 5.0
            assert settings.request_timeout == 60.0
            assert settings.max_retries == 5
            assert settings.retry_backoff == 2.0

    def test_base_url_property(self):
        """Test base_url property generation."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            assert settings.base_url == "https://10.207.56.26"

    def test_proxy_endpoint_property(self):
        """Test proxy_endpoint property."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            assert settings.proxy_endpoint == "/api/console/proxy"

    def test_require_credentials_success(self):
        """Test require_credentials passes when credentials present."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            # Should not raise
            settings.require_credentials()

    def test_require_credentials_missing_user(self):
        """Test require_credentials fails when user is missing."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = ElasticSettings()
            with pytest.raises(ValueError, match="Missing VDS_ELASTIC_USER"):
                settings.require_credentials()


class TestLoadSettings:
    """Tests for load_settings factory function."""

    def test_load_from_env(self):
        """Test loading settings from environment variables."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = load_settings()
            assert settings.kibana_url == "log.digital.vn"
            assert settings.user == "testuser"

    def test_load_from_env_file(self, tmp_path):
        """Test loading settings from a custom .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
VDS_ELASTIC_KIBANA_URL=custom.host.com
VDS_ELASTIC_KIBANA_IP=192.168.1.1
VDS_ELASTIC_USER=fileuser
VDS_ELASTIC_PASSWORD=filepass
"""
        )

        # Clear env vars to ensure file is used
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings(env_path=env_file)
            assert settings.kibana_url == "custom.host.com"
            assert settings.kibana_ip == "192.168.1.1"
            assert settings.user == "fileuser"
            assert settings.password == "filepass"

    def test_env_overrides_file(self, tmp_path):
        """Test that env vars override .env file values."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
VDS_ELASTIC_KIBANA_URL=file.host.com
VDS_ELASTIC_KIBANA_IP=10.0.0.1
VDS_ELASTIC_USER=fileuser
VDS_ELASTIC_PASSWORD=filepass
"""
        )

        env = {
            "VDS_ELASTIC_USER": "envuser",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings(env_path=env_file)
            # Env var should override
            assert settings.user == "envuser"
            # File values should be used for others
            assert settings.kibana_url == "file.host.com"
            assert settings.password == "filepass"

    def test_load_with_overrides(self):
        """Test loading settings with explicit overrides."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = load_settings(overrides={"default_size": 100})
            assert settings.default_size == 100

    def test_strict_mode_success(self):
        """Test strict mode with valid credentials."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "testuser",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False):
            # Should not raise
            settings = load_settings(strict=True)
            assert settings.user == "testuser"

    def test_strict_mode_missing_credentials(self):
        """Test strict mode fails when credentials are missing."""
        env = {
            "VDS_ELASTIC_KIBANA_URL": "log.digital.vn",
            "VDS_ELASTIC_KIBANA_IP": "10.207.56.26",
            "VDS_ELASTIC_USER": "",
            "VDS_ELASTIC_PASSWORD": "testpass",
        }
        with patch.dict(os.environ, env, clear=False), pytest.raises(SettingsError):
            load_settings(strict=True)

    def test_validation_error_handling(self, tmp_path):
        """Test that validation errors are wrapped in SettingsError."""
        # Missing required fields should raise SettingsError
        # Use a non-existent env file to avoid reading from real ~/.vds/.env
        fake_env = tmp_path / "nonexistent.env"
        with patch.dict(os.environ, {}, clear=True), pytest.raises(SettingsError):
            load_settings(env_path=fake_env)


class TestDefaultEnvPaths:
    """Tests for DEFAULT_ENV_PATHS constant."""

    def test_default_paths_exist(self):
        """Test that DEFAULT_ENV_PATHS is defined correctly."""
        # platform_core.env defines a single-path tuple:
        # DEFAULT_ENV_PATHS = (_vds_env_path(),)
        assert len(DEFAULT_ENV_PATHS) == 1
        assert DEFAULT_ENV_PATHS[0] == Path.home() / ".vds" / ".env"
