"""Tests for vds_platform_core.http.retry — TSK-7.3."""

from __future__ import annotations

import pytest
from vds_platform_core.http.retry import exponential_backoff, with_retry
from vds_platform_core.protocols import HTTPClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeClient:
    """Minimal HTTPClient stub."""

    def __init__(self, responses: list) -> None:
        """*responses* is consumed left-to-right; exceptions are raised."""
        self._responses = list(responses)
        self.get_calls = 0
        self.post_calls = 0
        self.aclose_calls = 0

    async def get(self, url: str, **kwargs: object) -> object:
        self.get_calls += 1
        r = self._responses.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    async def post(self, url: str, **kwargs: object) -> object:
        self.post_calls += 1
        r = self._responses.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r

    async def aclose(self) -> None:
        self.aclose_calls += 1


_INSTANT = exponential_backoff(initial_wait=0.0, max_wait=0.0, jitter=0.0)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_wrapper_isinstance_http_client() -> None:
    """with_retry() returns an object satisfying the HTTPClient protocol."""
    wrapper = with_retry(_FakeClient(["ok"]), _INSTANT)
    assert isinstance(wrapper, HTTPClient)


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_retries_on_retryable_error() -> None:
    """get() retries once on a retryable exception then returns success."""
    client = _FakeClient([OSError("timeout"), "result"])
    wrapper = with_retry(client, _INSTANT)
    result = await wrapper.get("http://x")
    assert result == "result"
    assert client.get_calls == 2


@pytest.mark.asyncio
async def test_post_retries_on_retryable_error() -> None:
    """post() retries once on a retryable exception then returns success."""
    client = _FakeClient([OSError("timeout"), "posted"])
    wrapper = with_retry(client, _INSTANT)
    result = await wrapper.post("http://x", json={})
    assert result == "posted"
    assert client.post_calls == 2


@pytest.mark.asyncio
async def test_non_retryable_propagates_immediately() -> None:
    """Exceptions outside the retryable tuple propagate without retry."""
    policy = exponential_backoff(retryable=(OSError,), initial_wait=0.0, jitter=0.0)
    client = _FakeClient([ValueError("not retryable")])
    wrapper = with_retry(client, policy)
    with pytest.raises(ValueError, match="not retryable"):
        await wrapper.get("http://x")
    assert client.get_calls == 1


@pytest.mark.asyncio
async def test_max_attempts_respected() -> None:
    """Raises after exhausting max_attempts retries."""
    policy = exponential_backoff(max_attempts=2, initial_wait=0.0, jitter=0.0)
    client = _FakeClient([OSError("a"), OSError("b"), "unreachable"])
    wrapper = with_retry(client, policy)
    with pytest.raises(OSError):
        await wrapper.get("http://x")
    assert client.get_calls == 2


@pytest.mark.asyncio
async def test_exception_type_preserved_after_exhaustion() -> None:
    """The original exception type is preserved after retries are exhausted."""
    policy = exponential_backoff(max_attempts=2, initial_wait=0.0, jitter=0.0)
    client = _FakeClient([ConnectionError("down"), ConnectionError("still down")])
    wrapper = with_retry(client, policy)
    with pytest.raises(ConnectionError):
        await wrapper.get("http://x")


# ---------------------------------------------------------------------------
# aclose delegation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aclose_delegates_to_underlying_client() -> None:
    """aclose() is forwarded to the wrapped client."""
    client = _FakeClient([])
    wrapper = with_retry(client, _INSTANT)
    await wrapper.aclose()
    assert client.aclose_calls == 1


# ---------------------------------------------------------------------------
# exponential_backoff policy unit tests
# ---------------------------------------------------------------------------


def test_wait_seconds_exponential_formula() -> None:
    """wait_seconds follows min(initial * multiplier**attempt, max_wait)."""
    policy = exponential_backoff(initial_wait=1.0, multiplier=2.0, max_wait=10.0, jitter=0.0)
    assert policy.wait_seconds(0) == 1.0
    assert policy.wait_seconds(1) == 2.0
    assert policy.wait_seconds(2) == 4.0
    assert policy.wait_seconds(10) == 10.0  # capped at max_wait


def test_can_retry_true_for_retryable_exception() -> None:
    """can_retry returns True for exceptions within the retryable tuple."""
    policy = exponential_backoff(retryable=(OSError, ValueError))
    assert policy.can_retry(0, OSError("x"))
    assert policy.can_retry(1, ValueError("y"))


def test_can_retry_false_for_non_retryable_exception() -> None:
    """can_retry returns False for exceptions outside the retryable tuple."""
    policy = exponential_backoff(retryable=(OSError,))
    assert not policy.can_retry(0, TypeError("x"))
