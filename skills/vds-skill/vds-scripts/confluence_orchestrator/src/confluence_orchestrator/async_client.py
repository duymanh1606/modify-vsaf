"""Async Confluence HTTP client composed with the VDS platform_core middleware stack.

Replaces the bespoke retry/auth layer in http.py with the standard
``build_client()`` factory from platform_core.  Error mappings are registered
once at import time so ``map_http_error(status, body, service=_SERVICE_NAME)``
returns typed VDSClientError subclasses for all callers.

TSK-7.9 step 7 — compose async_client with vds_default_stack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping
from vds_platform_core.http.stack import build_client

if TYPE_CHECKING:
    from vds_platform_core.protocols import HTTPClient

    from .config import ConfluenceSettings

# ---------------------------------------------------------------------------
# Service identifier — used as the key in the platform_core error registry
# and as the ``service`` label passed to build_client().
# ---------------------------------------------------------------------------
SERVICE_NAME = "confluence"

# Register Confluence HTTP-status → VDSClientError mappings once at module
# import time.  Consumers calling map_http_error with service=SERVICE_NAME
# get typed platform_core exceptions for 401/403/404/409/429.
for _status, _error_cls in (
    (401, AuthError),
    (403, ClientPermissionError),
    (404, NotFoundError),
    (409, ConflictError),
    (429, RateLimitError),
):
    register_http_error_mapping(SERVICE_NAME, _status, _error_cls)
del _status, _error_cls

# Environment-variable names that HeaderAuthResolver reads per server type.
# These match the ConfluenceSettings field aliases so the same env vars
# drive both the pydantic model and the async middleware stack.
_TOKEN_ENV: dict[str, str] = {
    "internal": "INTERNAL_CONFLUENCE_TOKEN",
    "int": "INTERNAL_CONFLUENCE_TOKEN",
    "main": "INTERNAL_CONFLUENCE_TOKEN",
    "external": "EXTERNAL_CONFLUENCE_TOKEN",
    "ext": "EXTERNAL_CONFLUENCE_TOKEN",
    "outsource": "EXTERNAL_CONFLUENCE_TOKEN",
}


def build_confluence_client(
    settings: ConfluenceSettings,
    *,
    server: str | None = None,
) -> HTTPClient:
    """Build a fully-wired async HTTPClient for the given Confluence server.

    Composes: ``httpx.AsyncClient`` → ``vds_default_stack`` (retry + auth)
    using ``settings`` for timeouts, retry policy, base URL, and the correct
    bearer-token environment variable.

    Args:
        settings: Loaded ``ConfluenceSettings`` (or any ``HTTPClientSettings``
            subclass that also provides ``url_for``).
        server: Server alias — ``"internal"``, ``"external"``, etc.  Defaults
            to ``settings.default_server``.

    Returns:
        A fully-wired ``HTTPClient`` ready for async REST calls.

    Raises:
        ValueError: If *server* is not a recognised alias.
    """
    effective_server = (server or settings.default_server).lower()
    token_env = _TOKEN_ENV.get(effective_server)
    if token_env is None:
        raise ValueError(
            f"Unknown Confluence server alias '{effective_server}'. Valid aliases: {', '.join(sorted({*_TOKEN_ENV}))}"
        )
    base_url = str(settings.url_for(effective_server))
    return build_client(
        settings=settings,
        service=SERVICE_NAME,
        base_url=base_url,
        token_field=token_env,
    )


__all__ = ["SERVICE_NAME", "build_confluence_client"]
