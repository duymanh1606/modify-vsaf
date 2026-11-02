"""Tests for HTTPClientSettings mixin — TSK-7.15."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_platform_core.config import VDS_BASE_SETTINGS_CONFIG, HTTPClientSettings
from vds_platform_core.protocols import RetryPolicy


class TestHTTPClientSettingsDefaults:
    def test_connect_timeout_default(self) -> None:
        assert HTTPClientSettings().connect_timeout == 5.0

    def test_read_timeout_default(self) -> None:
        assert HTTPClientSettings().read_timeout == 30.0

    def test_write_timeout_default(self) -> None:
        assert HTTPClientSettings().write_timeout == 30.0

    def test_pool_timeout_default(self) -> None:
        assert HTTPClientSettings().pool_timeout == 5.0

    def test_max_retries_default(self) -> None:
        assert HTTPClientSettings().max_retries == 3

    def test_retry_backoff_initial_default(self) -> None:
        assert HTTPClientSettings().retry_backoff_initial == 0.5

    def test_retry_backoff_multiplier_default(self) -> None:
        assert HTTPClientSettings().retry_backoff_multiplier == 2.0

    def test_retry_max_wait_default(self) -> None:
        assert HTTPClientSettings().retry_max_wait == 60.0

    def test_rate_limit_aware_default(self) -> None:
        assert HTTPClientSettings().rate_limit_aware is True


class TestHTTPClientSettingsValidation:
    def test_negative_connect_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HTTPClientSettings(connect_timeout=-1.0)

    def test_negative_read_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HTTPClientSettings(read_timeout=-0.1)

    def test_max_retries_above_20_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HTTPClientSettings(max_retries=21)

    def test_max_retries_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HTTPClientSettings(max_retries=-1)

    def test_retry_backoff_multiplier_below_1_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HTTPClientSettings(retry_backoff_multiplier=0.5)


class TestToRetryPolicy:
    def test_returns_retry_policy_protocol(self) -> None:
        policy = HTTPClientSettings().to_retry_policy()
        assert isinstance(policy, RetryPolicy)

    def test_max_attempts_matches_max_retries(self) -> None:
        settings = HTTPClientSettings(max_retries=7)
        policy = settings.to_retry_policy()
        assert policy.can_retry(0, Exception()) or True  # can_retry is callable
        assert getattr(policy, "max_attempts", None) == 7

    def test_initial_wait_matches_backoff_initial(self) -> None:
        settings = HTTPClientSettings(retry_backoff_initial=1.5)
        policy = settings.to_retry_policy()
        assert getattr(policy, "initial_wait", None) == 1.5

    def test_max_wait_matches_retry_max_wait(self) -> None:
        settings = HTTPClientSettings(retry_max_wait=120.0)
        policy = settings.to_retry_policy()
        assert getattr(policy, "max_wait", None) == 120.0


class TestEnvVarOverride:
    def test_connect_timeout_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CONNECT_TIMEOUT", "99.0")
        assert HTTPClientSettings().connect_timeout == 99.0

    def test_max_retries_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MAX_RETRIES", "10")
        assert HTTPClientSettings().max_retries == 10


class TestInheritanceComposition:
    def test_subclass_combines_with_basesettings(self) -> None:
        class _TestSettings(HTTPClientSettings, BaseSettings):
            model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="TST__")
            extra_field: str = "hello"

        s = _TestSettings()
        assert s.connect_timeout == 5.0
        assert s.extra_field == "hello"

    def test_subclass_env_prefix_scopes_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _PrefixSettings(HTTPClientSettings, BaseSettings):
            model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="TST2__")

        monkeypatch.setenv("TST2__CONNECT_TIMEOUT", "42.0")
        assert _PrefixSettings().connect_timeout == 42.0

    def test_to_retry_policy_available_on_subclass(self) -> None:
        class _SubSettings(HTTPClientSettings, BaseSettings):
            model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="SUB__")

        assert isinstance(_SubSettings().to_retry_policy(), RetryPolicy)
