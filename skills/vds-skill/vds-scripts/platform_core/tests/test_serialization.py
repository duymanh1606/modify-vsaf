"""Tests for safe_dump and SafeDumpMixin (FR-6.2)."""

from __future__ import annotations

from pydantic import BaseModel, Field, SecretStr
from vds_platform_core.serialization import SafeDumpMixin, safe_dump


class _SecretsModel(BaseModel):
    """Model with mixed secret and non-secret fields for testing."""

    api_key: SecretStr = Field(default_factory=lambda: SecretStr("sk-real"))
    host: str = "localhost"
    # Dict field where values are also SecretStr — explicitly typed so model_dump
    # preserves the SecretStr wrapper.
    auth_headers: dict[str, SecretStr] = Field(
        default_factory=lambda: {"x-token": SecretStr("bearer-secret")},
    )


class _SafeModel(SafeDumpMixin, BaseModel):
    """Model using the mixin."""

    api_key: SecretStr = Field(default_factory=lambda: SecretStr("sk-mixin"))
    value: int = 42


class _NestedContainer(BaseModel):
    """Model with SecretStr inside a nested model inside a list."""

    inner_key: SecretStr = Field(default_factory=lambda: SecretStr("deep-secret"))


class _ListContainer(BaseModel):
    items: list[_NestedContainer] = []


class TestSafeDump:
    """safe_dump() redacts SecretStr at all nesting levels."""

    def test_secret_str_redacted_at_root(self) -> None:
        model = _SecretsModel()
        dumped = safe_dump(model)
        assert dumped["api_key"] == "***"
        assert dumped["host"] == "localhost"

    def test_secret_str_redacted_in_nested_dict(self) -> None:
        """Dict[str, SecretStr] — model_dump preserves SecretStr wrapper."""
        model = _SecretsModel()
        dumped = safe_dump(model)
        assert dumped["auth_headers"]["x-token"] == "***"

    def test_secret_str_redacted_in_list_of_nested_models(self) -> None:
        """SecretStr inside a nested model inside a list."""
        model = _ListContainer(
            items=[_NestedContainer(), _NestedContainer()],
        )
        dumped = safe_dump(model)
        assert dumped["items"][0]["inner_key"] == "***"
        assert dumped["items"][1]["inner_key"] == "***"

    def test_non_secret_fields_unchanged(self) -> None:
        model = _SecretsModel(host="prod.example.com")
        dumped = safe_dump(model)
        assert dumped["host"] == "prod.example.com"

    def test_empty_secret_value(self) -> None:
        model = _SecretsModel(api_key=SecretStr(""))
        dumped = safe_dump(model)
        assert dumped["api_key"] == "***"

    def test_plain_dict_str_values_not_mistaken_for_secrets(self) -> None:
        """Plain str values in dict fields are not SecretStr — kept as-is."""
        model = _SecretsModel(host="plain-host.example.com")
        dumped = safe_dump(model)
        assert dumped["host"] == "plain-host.example.com"


class TestSafeDumpMixin:
    """SafeDumpMixin provides a .safe_dump() convenience method."""

    def test_safe_dump_redacts_secret(self) -> None:
        model = _SafeModel()
        assert model.safe_dump()["api_key"] == "***"

    def test_safe_dump_preserves_non_secret(self) -> None:
        model = _SafeModel(value=99)
        assert model.safe_dump()["value"] == 99

    def test_safe_dump_equals_safe_dump(self) -> None:
        model = _SafeModel()
        assert model.safe_dump() == safe_dump(model)
