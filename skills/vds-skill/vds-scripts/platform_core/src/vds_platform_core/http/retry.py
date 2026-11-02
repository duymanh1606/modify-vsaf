"""HTTP retry middleware — platform_core.http.retry (TSK-7.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import stamina

if TYPE_CHECKING:
    from vds_platform_core.protocols import HTTPClient, RetryPolicy


@dataclass(frozen=True)
class exponential_backoff:
    """Default RetryPolicy: exponential backoff with optional jitter."""

    max_attempts: int = 3
    initial_wait: float = 0.1
    multiplier: float = 2.0
    max_wait: float = 5.0
    jitter: float = 1.0
    retryable: tuple[type[BaseException], ...] = (Exception,)

    def can_retry(self, attempt: int, exc: BaseException) -> bool:
        return isinstance(exc, self.retryable)

    def wait_seconds(self, attempt: int) -> float:
        return min(self.initial_wait * (self.multiplier**attempt), self.max_wait)


class _RetryWrappedClient:
    """HTTPClient proxy that retries get/post using a RetryPolicy."""

    def __init__(self, client: HTTPClient, policy: RetryPolicy) -> None:
        self._client = client
        p = policy
        self._caller = stamina.AsyncRetryingCaller(
            attempts=getattr(p, "max_attempts", 3),
            wait_initial=getattr(p, "initial_wait", 0.1),
            wait_max=getattr(p, "max_wait", 5.0),
            wait_jitter=getattr(p, "jitter", 1.0),
            wait_exp_base=getattr(p, "multiplier", 2.0),
        )
        self._on = getattr(p, "retryable", (Exception,))

    async def get(self, url: str, **kwargs: Any) -> Any:
        return await self._caller(self._on, self._client.get, url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> Any:
        return await self._caller(self._on, self._client.post, url, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()


def with_retry(client: HTTPClient, policy: RetryPolicy) -> HTTPClient:
    """Wrap *client* with retry behaviour governed by *policy*."""
    return _RetryWrappedClient(client, policy)  # type: ignore[return-value]


__all__ = ["exponential_backoff", "with_retry"]
