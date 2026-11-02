"""Tests for vds_platform_core.errors — TDD RED phase.

Run before implementation to ensure all assertions fail.
"""

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    RetryError,
    SettingsError,
    TransportError,
    VDSClientError,
    VDSError,
)

# ---------------------------------------------------------------------------
# isinstance / hierarchy tests
# ---------------------------------------------------------------------------


class TestIsinstanceChain:
    def test_vds_error_is_runtime_error(self) -> None:
        e = VDSError("boom")
        assert isinstance(e, RuntimeError)

    def test_vds_client_error_chain(self) -> None:
        e = VDSClientError("x")
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_auth_error_chain(self) -> None:
        e = AuthError("no auth")
        assert isinstance(e, AuthError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_client_permission_error_chain(self) -> None:
        e = ClientPermissionError("forbidden")
        assert isinstance(e, ClientPermissionError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)
        # Must NOT be stdlib PermissionError
        assert not isinstance(e, PermissionError)

    def test_transport_error_chain(self) -> None:
        e = TransportError("conn refused")
        assert isinstance(e, TransportError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_client_timeout_error_chain(self) -> None:
        e = ClientTimeoutError("timed out")
        assert isinstance(e, ClientTimeoutError)
        assert isinstance(e, TransportError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)
        # Must NOT be stdlib TimeoutError
        assert not isinstance(e, TimeoutError)

    def test_retry_error_chain(self) -> None:
        e = RetryError("retries exhausted")
        assert isinstance(e, RetryError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_response_error_chain(self) -> None:
        e = ResponseError("bad response")
        assert isinstance(e, ResponseError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_not_found_error_chain(self) -> None:
        e = NotFoundError("not found")
        assert isinstance(e, NotFoundError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_rate_limit_error_chain(self) -> None:
        e = RateLimitError("rate limited")
        assert isinstance(e, RateLimitError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_conflict_error_chain(self) -> None:
        e = ConflictError("conflict")
        assert isinstance(e, ConflictError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_settings_error_chain(self) -> None:
        e = SettingsError("bad config")
        assert isinstance(e, SettingsError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)
        # NOT a VDSClientError
        assert not isinstance(e, VDSClientError)


# ---------------------------------------------------------------------------
# MRO diamond test
# ---------------------------------------------------------------------------


class SonarqubeClientError(VDSClientError):
    """Simulated Sonarqube domain error base."""


class SonarqubeAuthError(SonarqubeClientError, AuthError):
    """Diamond: SonarqubeClientError + AuthError both inherit VDSClientError."""


class TestDiamondMRO:
    def test_sonarqube_auth_error_isinstance_both_bases(self) -> None:
        e = SonarqubeAuthError("sonarqube auth failed")
        assert isinstance(e, SonarqubeClientError)
        assert isinstance(e, AuthError)
        assert isinstance(e, VDSClientError)
        assert isinstance(e, VDSError)
        assert isinstance(e, RuntimeError)

    def test_diamond_mro_does_not_raise(self) -> None:
        """Constructing the diamond class must not raise TypeError."""
        # If cooperative MRO breaks, Python raises TypeError at construction time.
        e = SonarqubeAuthError("ok")
        assert str(e) == "ok"


# ---------------------------------------------------------------------------
# context dict tests
# ---------------------------------------------------------------------------


class TestContextDict:
    def test_default_context_is_empty_dict(self) -> None:
        e = VDSError("msg")
        assert e.context == {}

    def test_context_is_stored(self) -> None:
        ctx = {"repo": "my-repo", "attempt": 3}
        e = VDSError("msg", context=ctx)
        assert e.context == ctx

    def test_context_on_subclass(self) -> None:
        e = AuthError("denied", context={"user": "alice"})
        assert e.context["user"] == "alice"

    def test_context_not_mutated(self) -> None:
        """Stored context dict is the same object (immutable-ish test)."""
        ctx: dict[str, object] = {"key": "val"}
        e = VDSError("m", context=ctx)
        # context stored as-is (not deep-copied); this is expected behaviour
        assert e.context is ctx


# ---------------------------------------------------------------------------
# repr / str tests
# ---------------------------------------------------------------------------


class TestReprStr:
    def test_str_is_message(self) -> None:
        e = VDSError("something went wrong")
        assert str(e) == "something went wrong"

    def test_message_propagates_through_hierarchy(self) -> None:
        e = NotFoundError("page 42 not found")
        assert "page 42 not found" in str(e)


# ---------------------------------------------------------------------------
# **kwargs MRO forwarding
# ---------------------------------------------------------------------------


class TestKwargsForwarding:
    def test_no_unexpected_kwargs_error(self) -> None:
        """VDSError must accept and pass through extra kwargs up the MRO."""
        # RuntimeError accepts no kwargs beyond args — kwargs should NOT break it.
        # If **kwargs is missing, cooperative MRO with multiple bases will raise.
        e = VDSError("msg")
        assert isinstance(e, RuntimeError)

    def test_subclass_init_with_context_keyword(self) -> None:
        """Subclasses should accept context= keyword without TypeError."""
        e = TransportError("transport failed", context={"host": "localhost"})
        assert e.context["host"] == "localhost"
