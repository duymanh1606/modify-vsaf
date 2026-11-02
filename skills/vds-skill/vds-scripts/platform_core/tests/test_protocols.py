"""Tests for vds_platform_core.protocols — TSK-7.1.

Duck-type verification for all three runtime_checkable Protocols.
Note: Python's @runtime_checkable isinstance() checks presence of method/attribute
*names* only — not signatures. A class with the right names but wrong signatures
still passes isinstance() at runtime; this is expected Protocol behavior.
"""

from __future__ import annotations

from vds_platform_core.protocols import CredentialResolver, HTTPClient, RetryPolicy

# ---------------------------------------------------------------------------
# HTTPClient — 3 tests
# ---------------------------------------------------------------------------


class _GoodHTTPClient:
    """Minimal valid HTTPClient implementation."""

    async def get(self, url: str, **kw: object) -> object:
        return None

    async def post(self, url: str, **kw: object) -> object:
        return None

    async def aclose(self) -> None:
        pass


class _MissingAcloseHTTPClient:
    async def get(self, url: str, **kw: object) -> object:
        return None

    async def post(self, url: str, **kw: object) -> object:
        return None


class _MissingPostHTTPClient:
    async def get(self, url: str, **kw: object) -> object:
        return None

    async def aclose(self) -> None:
        pass


def test_http_client_positive() -> None:
    """Object with all required methods passes isinstance check."""
    assert isinstance(_GoodHTTPClient(), HTTPClient)


def test_http_client_missing_aclose() -> None:
    """Object missing aclose() fails isinstance check."""
    assert not isinstance(_MissingAcloseHTTPClient(), HTTPClient)


def test_http_client_missing_post() -> None:
    """Object missing post() fails isinstance check."""
    assert not isinstance(_MissingPostHTTPClient(), HTTPClient)


# ---------------------------------------------------------------------------
# CredentialResolver — 3 tests
# ---------------------------------------------------------------------------


class _GoodCredentialResolver:
    def resolve(self) -> str | None:
        return "secret"


class _MissingResolveCredentialResolver:
    def something_else(self) -> str:
        return ""


class _WrongNameCredentialResolver:
    def resolver(self) -> str | None:  # typo: resolver vs resolve
        return None


def test_credential_resolver_positive() -> None:
    """Object with resolve() passes isinstance check."""
    assert isinstance(_GoodCredentialResolver(), CredentialResolver)


def test_credential_resolver_missing_resolve() -> None:
    """Object missing resolve() fails isinstance check."""
    assert not isinstance(_MissingResolveCredentialResolver(), CredentialResolver)


def test_credential_resolver_wrong_method_name() -> None:
    """Object with misspelled method name fails isinstance check."""
    assert not isinstance(_WrongNameCredentialResolver(), CredentialResolver)


# ---------------------------------------------------------------------------
# RetryPolicy — 3 tests
# ---------------------------------------------------------------------------


class _GoodRetryPolicy:
    def can_retry(self, attempt: int, exc: BaseException) -> bool:
        return attempt < 3

    def wait_seconds(self, attempt: int) -> float:
        return 2.0**attempt


class _MissingWaitSecondsRetryPolicy:
    def can_retry(self, attempt: int, exc: BaseException) -> bool:
        return False


class _MissingCanRetryPolicy:
    def wait_seconds(self, attempt: int) -> float:
        return 1.0


def test_retry_policy_positive() -> None:
    """Object with both required methods passes isinstance check."""
    assert isinstance(_GoodRetryPolicy(), RetryPolicy)


def test_retry_policy_missing_wait_seconds() -> None:
    """Object missing wait_seconds() fails isinstance check."""
    assert not isinstance(_MissingWaitSecondsRetryPolicy(), RetryPolicy)


def test_retry_policy_missing_can_retry() -> None:
    """Object missing can_retry() fails isinstance check."""
    assert not isinstance(_MissingCanRetryPolicy(), RetryPolicy)
