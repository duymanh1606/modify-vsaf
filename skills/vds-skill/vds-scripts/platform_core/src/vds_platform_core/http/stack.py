"""HTTP stack assembly — platform_core.http.stack (TSK-7.18)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import httpx

from vds_platform_core.credentials import HeaderAuthResolver
from vds_platform_core.http.auth import with_auth
from vds_platform_core.http.retry import with_retry

if TYPE_CHECKING:
    from vds_platform_core.config import HTTPClientSettings
    from vds_platform_core.protocols import HTTPClient, RetryPolicy


def vds_default_stack(
    client: HTTPClient,
    *,
    resolver: HeaderAuthResolver,
    retry_policy: RetryPolicy,
    service: str,
) -> HTTPClient:
    """Standard VDS middleware stack: retry (innermost) → auth (outermost)."""
    return with_auth(with_retry(client, retry_policy), resolver, header_name=resolver.header_name)


def build_client(
    *,
    settings: HTTPClientSettings,
    service: str,
    base_url: str,
    token_field: str,
    header_name: str = "Authorization",
    rate_limit_aware: bool = True,
    extra_middleware: Sequence[Callable[[HTTPClient], HTTPClient]] = (),
) -> HTTPClient:
    """Build a fully-wired HTTPClient from *settings*.

    Composes: httpx.AsyncClient → vds_default_stack (retry + auth) →
    extra_middleware (FIFO: first entry wraps innermost).
    """
    raw: HTTPClient = httpx.AsyncClient(  # type: ignore[assignment]
        base_url=base_url,
        timeout=httpx.Timeout(
            connect=settings.connect_timeout,
            read=settings.read_timeout,
            write=settings.write_timeout,
            pool=settings.pool_timeout,
        ),
    )
    resolver = HeaderAuthResolver(token_field=token_field, header_name=header_name)
    client = vds_default_stack(raw, resolver=resolver, retry_policy=settings.to_retry_policy(), service=service)
    for mw in extra_middleware:
        client = mw(client)
    return client


__all__ = ["build_client", "vds_default_stack"]
