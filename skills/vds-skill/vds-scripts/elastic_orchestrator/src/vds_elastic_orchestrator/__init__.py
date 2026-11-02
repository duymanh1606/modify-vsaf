"""VDS Elastic Orchestrator - Elasticsearch client via Kibana Console Proxy.

This package provides CLI and programmatic access to the VDS Elasticsearch cluster
through Kibana's Console Proxy API, since direct ES access (port 9200) is not available.

Architecture:
    Client -> Kibana (nginx proxy) -> Kibana Console API -> Elasticsearch

Usage:
    # CLI
    uv run vds-elastic ping
    uv run vds-elastic search --index "logs-*" --size 10

    # Python
    from vds_elastic_orchestrator import load_settings, KibanaElasticsearchClient

    settings = load_settings()
    with KibanaElasticsearchClient(settings) as client:
        result = client.search("logs-*", {"query": {"match_all": {}}})
"""

from __future__ import annotations

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

__version__ = "0.1.0"

from .errors import SERVICE_NAME as _SERVICE_NAME

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
    # Version
    "__version__",
    # Config
    "ElasticSettings",
    "SettingsError",
    "load_settings",
    # Client
    "KibanaElasticsearchClient",
]


def __getattr__(name: str):
    """Lazy import public API members."""
    if name == "ElasticSettings":
        from vds_elastic_orchestrator.config import ElasticSettings

        return ElasticSettings

    if name == "SettingsError":
        from vds_elastic_orchestrator.config import SettingsError

        return SettingsError

    if name == "load_settings":
        from vds_elastic_orchestrator.config import load_settings

        return load_settings

    if name == "KibanaElasticsearchClient":
        from vds_elastic_orchestrator.client import KibanaElasticsearchClient

        return KibanaElasticsearchClient

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
