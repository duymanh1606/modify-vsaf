"""VDS Platform Core — shared error hierarchy, severity registry, and logging factory."""

from __future__ import annotations

__version__ = "0.1.0"

from vds_platform_core.config import HTTPClientSettings
from vds_platform_core.protocols import CredentialResolver, HTTPClient, RetryPolicy

__all__ = [
    "CredentialResolver",
    "HTTPClient",
    "HTTPClientSettings",
    "RetryPolicy",
    "__version__",
]
