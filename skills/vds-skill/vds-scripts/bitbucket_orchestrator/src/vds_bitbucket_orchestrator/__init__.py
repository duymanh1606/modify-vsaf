"""Bitbucket automation orchestrator for VDS."""

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

from .async_client import AsyncBitbucketClient
from .client import BitbucketClient
from .config import BitbucketSettings, load_settings
from .errors import SERVICE_NAME as _SERVICE_NAME
from .factory import create_async_client, create_client
from .protocols import (
    BitbucketBranchClient,
    BitbucketCodeClient,
    BitbucketFullClient,
    BitbucketRepositoryClient,
)

for _status, _error_cls in (
    (401, AuthError),
    (403, ClientPermissionError),
    (404, NotFoundError),
    (409, ConflictError),
    (429, RateLimitError),
):
    register_http_error_mapping(_SERVICE_NAME, _status, _error_cls)
del _status, _error_cls

__all__ = [
    # Async Client (FR-21.2.3, TSK-225)
    "AsyncBitbucketClient",
    "BitbucketBranchClient",
    # Client
    "BitbucketClient",
    "BitbucketCodeClient",
    "BitbucketFullClient",
    # Protocols (FR-21.2.1)
    "BitbucketRepositoryClient",
    # Settings
    "BitbucketSettings",
    "create_async_client",
    # Factory functions (FR-21.2.2)
    "create_client",
    "load_settings",
]
