"""Tests for vds_platform_core.credentials — TSK-7.2."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import SecretStr
from vds_platform_core.credentials import HeaderAuthResolver, resolve_secret

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# resolve_secret — 5 tests
# ---------------------------------------------------------------------------


def test_resolve_secret_secretstr() -> None:
    """SecretStr is unwrapped to its plain string value."""
    assert resolve_secret(SecretStr("abc")) == "abc"


def test_resolve_secret_plain_str() -> None:
    """Plain str passes through unchanged."""
    assert resolve_secret("abc") == "abc"


def test_resolve_secret_none() -> None:
    """None returns None."""
    assert resolve_secret(None) is None


def test_resolve_secret_empty_str() -> None:
    """Empty string is treated as absent and returns None."""
    assert resolve_secret("") is None


def test_resolve_secret_idempotent() -> None:
    """resolve_secret applied twice is identical to applying it once."""
    once = resolve_secret(SecretStr("x"))
    twice = resolve_secret(once)
    assert once == twice == "x"
    # Nested-call form confirms idempotency in one expression:
    assert resolve_secret(resolve_secret(SecretStr("x"))) == resolve_secret(SecretStr("x")) == "x"


# ---------------------------------------------------------------------------
# HeaderAuthResolver — 3 tests
# ---------------------------------------------------------------------------


def test_header_auth_resolver_attributes() -> None:
    """Constructor stores token_field and header_name."""
    resolver = HeaderAuthResolver(token_field="X-Token", header_name="Authorization")
    assert resolver.token_field == "X-Token"
    assert resolver.header_name == "Authorization"


def test_header_auth_resolver_resolve_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve() returns the token value found in environment."""
    monkeypatch.setenv("VDS_TEST_TOKEN", "bearer-abc")
    resolver = HeaderAuthResolver(token_field="VDS_TEST_TOKEN", header_name="Authorization")
    assert resolver.resolve() == "bearer-abc"


def test_header_auth_resolver_resolve_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """resolve() returns None when the env var is not set."""
    monkeypatch.delenv("VDS_MISSING_TOKEN_XYZ", raising=False)
    resolver = HeaderAuthResolver(
        token_field="VDS_MISSING_TOKEN_XYZ",
        header_name="X-Api-Key",
    )
    assert resolver.resolve() is None
