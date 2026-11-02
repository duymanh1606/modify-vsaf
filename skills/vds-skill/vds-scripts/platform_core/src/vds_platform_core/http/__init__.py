"""platform_core.http — HTTP middleware (retry, auth, errors, pagination, stack)."""

from vds_platform_core.http.auth import with_auth
from vds_platform_core.http.errors import map_http_error, register_http_error_mapping
from vds_platform_core.http.pagination import paginate
from vds_platform_core.http.retry import exponential_backoff, with_retry
from vds_platform_core.http.stack import build_client, vds_default_stack

__all__ = [
    "build_client",
    "exponential_backoff",
    "map_http_error",
    "paginate",
    "register_http_error_mapping",
    "vds_default_stack",
    "with_auth",
    "with_retry",
]
