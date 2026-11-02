"""Confluence client wrapper using atlassian-python-api for consistency."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar
from urllib.parse import parse_qs, urlparse

import httpx
import structlog
from vds_platform_core.credentials import resolve_secret

try:  # Prefer new-style Atlassian clients when available
    from atlassian.confluence import ConfluenceCloud as AtlassianConfluenceCloud  # type: ignore[attr-defined]
    from atlassian.confluence import ConfluenceServer as AtlassianConfluenceServer  # type: ignore[attr-defined]
except ImportError:  # Fall back to legacy class
    from atlassian import Confluence as AtlassianConfluenceCloud  # type: ignore

    AtlassianConfluenceServer = AtlassianConfluenceCloud

from .errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    ConfluenceDegradedWriteError,
    RateLimitError,
    ResponseError,
    RetryError,
    TransportError,
    VDSClientError,
)

if TYPE_CHECKING:
    from .config import ConfluenceSettings

T = TypeVar("T")

# Write operations blocked when the client is in degraded mode.
_WRITE_OPS: frozenset[str] = frozenset(
    {
        "create_page",
        "update_page",
        "delete_page",
        "upload_attachment",
        "update_attachment",
        "delete_attachment",
        "add_attachment",
        "add_comment",
    }
)


def _escape_cql_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _coerce_utc_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        dt_value = value
    else:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            dt_value = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise VDSClientError(
                "Invalid incremental high-water-mark timestamp",
                context={"value": value},
            ) from exc
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _build_lastmodified_cql_clause(
    last_modified_after: datetime | str | None,
    *,
    overlap_minutes: int = 0,
) -> str | None:
    if last_modified_after is None:
        return None
    overlap = max(int(overlap_minutes), 0)
    cursor = _coerce_utc_datetime(last_modified_after)
    if overlap:
        cursor = cursor - timedelta(minutes=overlap)
    return f'lastmodified >= "{cursor.strftime("%Y-%m-%d %H:%M")}"'


def _build_space_type_lastmodified_cql(
    *,
    space_key: str | None = None,
    content_type: str | None = None,
    last_modified_after: datetime | str | None = None,
    overlap_minutes: int = 0,
) -> str:
    cql_parts: list[str] = []
    if space_key:
        cql_parts.append(f'space = "{_escape_cql_literal(space_key)}"')
    if content_type:
        cql_parts.append(f'type = "{_escape_cql_literal(content_type)}"')
    last_modified_clause = _build_lastmodified_cql_clause(
        last_modified_after,
        overlap_minutes=overlap_minutes,
    )
    if last_modified_clause:
        cql_parts.append(last_modified_clause)
    if not cql_parts:
        raise VDSClientError(
            "At least one of space_key, content_type, or last_modified_after must be provided",
            context={},
        )
    query = " AND ".join(cql_parts)
    if last_modified_clause:
        query = f"{query} ORDER BY lastmodified ASC"
    return query


class ConfluenceHttpClient:
    def __init__(
        self,
        settings: ConfluenceSettings,
        *,
        server: str = "internal",
        client: httpx.Client | None = None,
    ) -> None:
        token = settings.token_for(server)
        if not token:
            raise AuthError(
                f"Token for server '{server}' is missing.",
                context={"server": server},
            )

        self._settings = settings
        self._server = server
        self._token = token
        if client is None:
            base_url = str(settings.url_for(server))
            client = httpx.Client(
                base_url=base_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        self._client = client

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ConfluenceHttpClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.close()

    def get_runtime_telemetry(self) -> dict[str, Any]:
        """Return telemetry snapshot (stub for crawl_tree compatibility).

        ConfluenceClient operates in degraded-mode (read-only) or normal mode.
        This stub provides a compatible interface for telemetry consumers.
        Actual retry/telemetry instrumentation would require adopting
        platform_core.with_retry (httpx.AsyncClient), which is a larger
        refactor beyond Phase 7 scope.
        """
        return {
            "adaptive_throttle": None,
            "recent_retry_events": [],
            "latency_ms": None,
            "mode": "degraded" if self._degraded else "normal",
        }

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:  # pragma: no cover - network errors
            raise TransportError(f"HTTP transport error: {exc}") from exc

        if response.status_code < 400:
            return response

        if response.status_code in {401, 403}:
            raise AuthError(
                "Authentication failed",
                context={"status_code": response.status_code},
            )
        if response.status_code == 409:
            raise ConflictError(
                "Request conflicted with existing state",
                context={"status_code": response.status_code},
            )
        raise ResponseError(
            f"Unexpected status {response.status_code}",
            status_code=response.status_code,
            context={"status_code": response.status_code, "body": response.text[:256]},
        )


class ConfluenceClient:
    """Confluence client wrapper using atlassian-python-api SDK."""

    def __init__(
        self,
        settings: ConfluenceSettings,
        *,
        server: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._settings = settings
        self._server = server or settings.default_server
        self._timeout = timeout or settings.http_timeout

        base_url = str(settings.url_for(self._server))
        token = settings.token_for(self._server)

        # Decide whether this endpoint should be treated as Cloud (v2) or Server (v1)
        self._is_cloud = self._looks_like_cloud(base_url)
        client_cls = AtlassianConfluenceCloud if self._is_cloud else AtlassianConfluenceServer

        # Configure authentication based on available credentials
        # Token (Bearer/PAT) takes priority over username+password to avoid 401s
        # when Basic auth is disabled on the server.
        auth_kwargs: dict[str, Any] = {"url": base_url, "timeout": self._timeout}
        if self._is_cloud:
            if token:
                auth_kwargs["token"] = token
            elif settings.username and settings.password:
                auth_kwargs["username"] = settings.username
                auth_kwargs["password"] = resolve_secret(settings.password)
            else:
                raise AuthError(
                    f"No credentials available for cloud server '{self._server}'. "
                    "Provide an API token or VDS_USERNAME+VDS_PASSWORD.",
                    context={"server": self._server},
                )
        elif token:
            # PATs supported on Confluence Server/Data Center
            auth_kwargs["token"] = token
        elif settings.username and settings.password:
            auth_kwargs["username"] = settings.username
            auth_kwargs["password"] = resolve_secret(settings.password)
        else:
            raise AuthError(
                f"No credentials available for server '{self._server}'. "
                "Provide a CONFLUENCE token or VDS_USERNAME+VDS_PASSWORD.",
                context={"server": self._server},
            )
        client_params = set(self._safe_signature_params(client_cls))
        supports_kwargs = False
        try:
            signature = inspect.signature(client_cls)
            supports_kwargs = any(
                param.kind is inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()
            )
        except (TypeError, ValueError):
            supports_kwargs = False
        if "cloud" in client_params or supports_kwargs:
            # Legacy Confluence() requires explicit cloud flag when URL already includes /wiki.
            auth_kwargs["cloud"] = self._is_cloud

        try:
            self._client = client_cls(**auth_kwargs)
        except Exception as exc:
            raise TransportError(
                f"Failed to initialize Confluence client: {exc}", context={"server": self._server, "base_url": base_url}
            ) from exc

        self._log = structlog.get_logger(__name__).bind(server=self._server, base_url=base_url)

        # Store retry settings
        self._max_retries = settings.max_retries
        self._retry_backoff_factor = settings.retry_backoff_factor
        self._retry_max_wait = 30.0
        self._create_params = set(self._safe_signature_params(self._client.create_page))
        self._update_params = set(self._safe_signature_params(self._client.update_page))
        # FR-172: degraded mode — set True on transport errors to block writes.
        self._degraded: bool = False

    # ------------------------------------------------------------------
    # FR-172: Degraded mode API
    # ------------------------------------------------------------------

    @property
    def is_degraded(self) -> bool:
        """True when the client has been marked degraded due to transport errors."""
        return self._degraded

    def mark_degraded(self) -> None:
        """Mark the client as degraded, blocking all subsequent write operations."""
        self._degraded = True

    def get_runtime_telemetry(self) -> dict[str, Any]:
        """Return telemetry snapshot (stub for crawl_tree compatibility).

        ConfluenceClient operates in degraded-mode (read-only) or normal mode.
        This stub provides a compatible interface for telemetry consumers.
        Actual retry/telemetry instrumentation would require adopting
        platform_core.with_retry (httpx.AsyncClient), which is a larger
        refactor beyond Phase 7 scope.
        """
        return {
            "adaptive_throttle": None,
            "recent_retry_events": [],
            "latency_ms": None,
            "mode": "degraded" if self._degraded else "normal",
        }

    def supports_api_version(self, version: str) -> bool:
        version = (version or "v1").lower()
        if version == "v1":
            return True
        if version == "v2":
            return self._is_cloud
        return False

    @staticmethod
    def _looks_like_cloud(base_url: str) -> bool:
        lowered = base_url.lower()
        return any(indicator in lowered for indicator in ("atlassian.net", "atlassian.com"))

    @staticmethod
    def _safe_signature_params(method) -> list[str]:
        try:
            return list(inspect.signature(method).parameters.keys())
        except (TypeError, ValueError):
            return []

    @staticmethod
    def _extract_pagination_marker(payload: dict[str, Any]) -> tuple[int | None, str | None]:
        """Extract pagination start/token markers from SDK payloads."""
        next_start: int | None = None
        next_token: str | None = None

        links = payload.get("_links")
        next_link: str | None = None
        if isinstance(links, dict) and isinstance(links.get("next"), str):
            next_link = links["next"]
        elif isinstance(payload.get("next"), str):
            next_link = payload["next"]

        if next_link:
            next_token = next_link
            query = urlparse(next_link).query
            if not query and "=" in next_link and "?" not in next_link:
                query = next_link
            params = parse_qs(query)
            start_values = params.get("start")
            if start_values:
                try:
                    next_start = int(start_values[0])
                except (TypeError, ValueError):
                    next_start = None
            cursor_values = params.get("cursor")
            if cursor_values and cursor_values[0]:
                next_token = cursor_values[0]

        for key in ("nextCursor", "next_cursor", "cursor"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                next_token = value.strip()
                break

        raw_start = payload.get("start")
        if next_start is None and isinstance(raw_start, int):
            next_start = raw_start

        return next_start, next_token

    @staticmethod
    def _require_dict(value: Any, operation: str) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        raise VDSClientError(
            f"{operation} returned unexpected payload type",
            context={"operation": operation, "payload_type": type(value).__name__},
        )

    @staticmethod
    def _coerce_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {"value": value}

    @staticmethod
    def _coerce_list_of_dicts(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []

    @staticmethod
    def _coerce_bytes(value: Any) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode("utf-8")
        raise VDSClientError(
            "Unexpected binary payload type",
            context={"payload_type": type(value).__name__},
        )

    @staticmethod
    def _coerce_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        return str(value)

    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Convert atlassian-python-api errors to our standardized errors."""
        error_str = str(error).lower()

        if "unauthorized" in error_str or "authentication" in error_str or "401" in error_str:
            raise AuthError(f"Authentication failed during {operation}", context={"error": str(error)})
        elif "forbidden" in error_str or "403" in error_str:
            raise AuthError(f"Access forbidden during {operation}", context={"error": str(error)})
        elif "rate limit" in error_str or "429" in error_str:
            raise RateLimitError(
                f"Rate limited during {operation}",
                retry_after=None,
                context={"error": str(error)},
            )
        elif "conflict" in error_str or "409" in error_str:
            raise ConflictError(f"Conflict during {operation}", context={"error": str(error)})
        elif "server error" in error_str or "500" in error_str:
            raise ResponseError(
                f"Server error during {operation}",
                status_code=500,
                context={"error": str(error)},
            )
        else:
            raise VDSClientError(f"API error during {operation}: {error}", context={"error": str(error)})

    def _with_retry(self, operation: Callable[[], T], operation_name: str) -> T:
        """Execute an operation with retry logic using instance settings."""
        op_base = (operation_name or "").strip().lower().split(" ", 1)[0]
        if self._degraded and op_base in _WRITE_OPS:
            raise ConfluenceDegradedWriteError(operation_name)
        for attempt in range(self._max_retries + 1):
            try:
                return operation()
            except Exception as exc:
                try:
                    self._handle_api_error(exc, operation_name)
                except (TransportError, RateLimitError) as retry_exc:
                    if attempt == self._max_retries:
                        self._log.error(
                            "retry_attempts_exhausted",
                            operation=operation_name,
                            attempts=self._max_retries,
                            final_error=str(retry_exc),
                        )
                        raise RetryError(
                            f"Retry attempts exhausted: {retry_exc}",
                            attempts=self._max_retries,
                            context={"original_error": str(retry_exc), "operation": operation_name},
                        ) from retry_exc

                    wait_time = min(
                        max(self._retry_backoff_factor, 0.0) * (2**attempt),
                        self._retry_max_wait,
                    )
                    self._log.warning(
                        "retry_attempt",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_time=wait_time,
                        error=str(retry_exc),
                    )
                    time.sleep(wait_time)
                except VDSClientError:
                    raise
        raise VDSClientError(
            "Retry loop exited without returning result",
            context={"operation": operation_name},
        )

    def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
        """Get a page by ID."""

        def operation() -> dict[str, Any]:
            params = {}
            if expand:
                params["expand"] = ",".join(expand)
            result = self._client.get_page_by_id(page_id, expand=",".join(expand) if expand else None)
            self._log.debug("page_retrieved", page_id=page_id)
            return self._require_dict(result, "get_page")

        return self._with_retry(operation, f"get_page {page_id}")

    def search_cql(
        self, cql: str, limit: int = 25, start: int = 0, expand: list[str] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Search using CQL.

        Bypasses the ``atlassian`` SDK's ``cql()`` method entirely because it
        uses ``if start:`` which is falsy for ``start=0``, causing the param to
        be omitted.  Instead we call ``rest/api/search`` directly with an
        explicit ``params`` dict that always includes ``start``.

        Without ``start`` in the request, some Confluence Server versions respond
        with ``java.lang.IllegalArgumentException: parameters should not be empty``.
        """

        def operation() -> dict[str, Any]:
            params: dict[str, Any] = {"cql": cql, "start": int(start)}
            if limit is not None:
                params["limit"] = int(limit)
            if expand:
                params["expand"] = ",".join(expand)
            params.update(kwargs)
            result = self._client.get("rest/api/search", params=params)
            self._log.debug("cql_search_completed", cql=cql, limit=limit, start=start)
            return self._require_dict(result, "search_cql")

        return self._with_retry(operation, f"cql_search {cql}")

    def probe_reachable(self) -> dict[str, Any]:
        """Run a minimal SDK-backed reachability probe against the selected base URL.

        The probe intentionally uses the same REST search path as normal CQL
        reads so Phase 153's explicit ``start=0`` handling stays exercised.
        Callers should treat success as "the configured Confluence base URL
        answered an authenticated SDK request", not as a guarantee that every
        later content operation will be fast.
        """

        return self.search_cql("type=page", limit=1, start=0)

    def cql_advanced(
        self,
        cql: str,
        *,
        limit: int = 25,
        start: int = 0,
        expand: list[str] | None = None,
        excerpt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Advanced CQL search with additional options.

        Args:
            cql: CQL query string
            limit: Maximum number of results (default: 25)
            start: Start index for pagination (default: 0)
            expand: Optional list of fields to expand
            excerpt: Optional excerpt strategy (e.g., "highlighted", "indexed")
            **kwargs: Additional options passed to SDK cql() method
        """

        def operation() -> dict[str, Any]:
            # Bypass self._client.cql() which has `if start:` falsy check.
            params: dict[str, Any] = {"cql": cql, "start": int(start)}
            if limit is not None:
                params["limit"] = int(limit)
            expand_str = ",".join(expand) if expand else None
            if expand_str:
                params["expand"] = expand_str
            if excerpt:
                params["excerpt"] = excerpt
            params.update(kwargs)
            result = self._client.get("rest/api/search", params=params)
            self._log.debug("cql_advanced_search_completed", cql=cql, limit=limit, start=start)
            return self._require_dict(result, "cql_advanced")

        return self._with_retry(operation, f"cql_advanced_search {cql}")

    def search_by_space_and_type(
        self,
        space_key: str | None = None,
        content_type: str | None = None,
        *,
        limit: int = 25,
        start: int = 0,
        expand: list[str] | None = None,
        last_modified_after: datetime | str | None = None,
        overlap_minutes: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search by space and content type (helper method that builds CQL).

        Args:
            space_key: Optional space key to filter by
            content_type: Optional content type (e.g., "page", "blogpost", "comment")
            limit: Maximum number of results (default: 25)
            start: Start index for pagination (default: 0)
            expand: Optional list of fields to expand
            last_modified_after: Optional high-water-mark timestamp for incremental crawl
            overlap_minutes: Optional overlap buffer minutes for high-water-mark queries
            **kwargs: Additional options passed to CQL search
        """
        cql = _build_space_type_lastmodified_cql(
            space_key=space_key,
            content_type=content_type,
            last_modified_after=last_modified_after,
            overlap_minutes=overlap_minutes,
        )
        return self.cql_advanced(cql, limit=limit, start=start, expand=expand, **kwargs)

    def create_page(
        self, space_key: str, title: str, body: str, parent_id: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Create a new page."""

        def operation() -> dict[str, Any]:
            call_kwargs: dict[str, Any] = {}
            if parent_id is not None:
                call_kwargs["parent_id"] = parent_id
            for key, value in kwargs.items():
                if key in self._create_params and value is not None:
                    call_kwargs[key] = value
            result = self._client.create_page(space=space_key, title=title, body=body, **call_kwargs)
            payload = self._require_dict(result, "create_page")
            self._log.info("page_created", space_key=space_key, title=title, page_id=payload.get("id"))
            return payload

        return self._with_retry(operation, f"create_page {title}")

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str | None = None,
        version: int | None = None,
        parent_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an existing page."""

        def operation() -> dict[str, Any]:
            call_kwargs: dict[str, Any] = {}
            for key, value in kwargs.items():
                if key in self._update_params and value is not None:
                    call_kwargs[key] = value
            if version is not None and "version" in self._update_params:
                call_kwargs["version"] = version
            if parent_id is not None and "parent_id" in self._update_params:
                call_kwargs["parent_id"] = parent_id
            result = self._client.update_page(page_id, title, body, **call_kwargs)
            self._log.info("page_updated", page_id=page_id, title=title)
            return self._require_dict(result, "update_page")

        return self._with_retry(operation, f"update_page {page_id}")

    def delete_page(self, page_id: str) -> None:
        """Delete a page."""
        if self._degraded:
            raise ConfluenceDegradedWriteError(f"delete_page {page_id}")
        try:
            # Use remove_page method from atlassian library
            self._client.remove_page(page_id=page_id)
            self._log.info("page_deleted", page_id=page_id)

        except Exception as exc:
            # Check if it's a permission issue
            if "Unable to trash content" in str(exc) or "Unable to purge content" in str(exc):
                self._log.warning("page_delete_permission_denied", page_id=page_id, error=str(exc))
                raise ClientPermissionError(
                    f"Permission denied when deleting page {page_id}. The page may be restricted or you may not have delete permissions.",
                    context={"page_id": page_id, "original_error": str(exc)},
                ) from exc
            else:
                self._handle_api_error(exc, f"delete_page {page_id}")

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make a raw HTTP request using the atlassian client."""
        try:
            # Use the underlying request method from atlassian library
            response = self._client.request(method=method, path=path, **kwargs)
            self._log.debug("http_request", method=method, path=path)
            return response

        except Exception as exc:
            self._handle_api_error(exc, f"request {method} {path}")
            raise

    def add_attachment(
        self,
        page_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Add an attachment to a page.

        According to atlassian-python-api docs, attach_content automatically updates
        if the file exists, versioning the new file and keeping the old one.
        See: https://atlassian-python-api.readthedocs.io/confluence.html#
        """

        def operation() -> dict[str, Any]:
            # Use attach_content from the official SDK (handles create vs update internally)
            result = self._client.attach_content(
                content=content,
                name=filename,
                content_type=content_type or "application/octet-stream",
                page_id=page_id,
                comment=comment,
            )
            self._log.info("attachment_added", page_id=page_id, filename=filename)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"add_attachment {filename}")

    def get_space(self, space_key: str) -> dict[str, Any]:
        """Get space information."""
        try:
            result = self._client.get_space(space_key)
            self._log.debug("space_retrieved", space_key=space_key)
            return self._require_dict(result, "get_space")

        except Exception as exc:
            self._handle_api_error(exc, f"get_space {space_key}")
            raise

    def get_space_permissions(self, space_key: str) -> dict[str, Any]:
        """Get all permissions configured for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.get_space_permissions(space_key)
            count = len(result) if isinstance(result, (list, tuple)) else len(result or {})
            self._log.debug("space_permissions_retrieved", space_key=space_key, count=count)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"get_space_permissions {space_key}")

    def set_permissions_to_user_for_space(
        self,
        space_key: str,
        user_key: str,
        *,
        operations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Grant permissions to a specific user for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.set_permissions_to_user_for_space(
                space_key,
                user_key,
                operations=operations,
            )
            self._log.info(
                "space_permissions_user_set",
                space_key=space_key,
                user_key=user_key,
                operations=operations or [],
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"set_permissions_to_user_for_space {space_key} {user_key}")

    def set_permissions_to_group_for_space(
        self,
        space_key: str,
        group_name: str,
        *,
        operations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Grant permissions to a group for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.set_permissions_to_group_for_space(
                space_key,
                group_name,
                operations=operations,
            )
            self._log.info(
                "space_permissions_group_set",
                space_key=space_key,
                group_name=group_name,
                operations=operations or [],
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"set_permissions_to_group_for_space {space_key} {group_name}")

    def set_permissions_to_anonymous_for_space(
        self,
        space_key: str,
        *,
        operations: list[str] | None = None,
    ) -> dict[str, Any]:
        """Grant permissions to anonymous users for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.set_permissions_to_anonymous_for_space(space_key, operations=operations)
            self._log.info(
                "space_permissions_anonymous_set",
                space_key=space_key,
                operations=operations or [],
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"set_permissions_to_anonymous_for_space {space_key}")

    def set_permissions_to_multiple_items_for_space(
        self,
        space_key: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Grant permissions to multiple users/groups in a single request."""

        if not items:
            raise VDSClientError(
                "Bulk permissions payload is empty",
                context={"space_key": space_key},
            )

        def _normalize_item(item: dict[str, Any], index: int) -> tuple[str, str | None, list[str]]:
            raw_operations = item.get("operations")
            if raw_operations is None:
                operations: list[str] = []
            elif isinstance(raw_operations, list) and all(isinstance(op, str) for op in raw_operations):
                operations = [op.strip() for op in raw_operations if op.strip()]
            else:
                raise VDSClientError(
                    "Invalid operations in bulk permissions item",
                    context={"space_key": space_key, "index": index},
                )

            target_type: str | None = None
            target_value: str | None = None

            target = item.get("target")
            if isinstance(target, dict):
                raw_type = target.get("type")
                if isinstance(raw_type, str):
                    target_type = raw_type.strip().lower()
                raw_value = target.get("value")
                if raw_value is None:
                    raw_value = target.get("key")
                if raw_value is None:
                    raw_value = target.get("name")
                if raw_value is not None:
                    target_value = str(raw_value).strip()

            if target_type is None and isinstance(item.get("target_type"), str):
                target_type = str(item["target_type"]).strip().lower()
            if target_type is None and isinstance(item.get("user_key"), str):
                target_type = "user"
                target_value = item["user_key"].strip()
            if target_type is None and isinstance(item.get("group_name"), str):
                target_type = "group"
                target_value = item["group_name"].strip()
            if target_type is None and item.get("anonymous") is True:
                target_type = "anonymous"

            if target_type not in {"user", "group", "anonymous"}:
                raise VDSClientError(
                    "Bulk permission item target is invalid",
                    context={"space_key": space_key, "index": index},
                )
            if target_type in {"user", "group"} and not target_value:
                raise VDSClientError(
                    "Bulk permission item requires target value for user/group",
                    context={"space_key": space_key, "index": index, "target_type": target_type},
                )

            return target_type, target_value, operations

        normalized_items = [_normalize_item(item, index) for index, item in enumerate(items)]

        def operation() -> dict[str, Any]:
            bulk_method = getattr(self._client, "set_permissions_to_multiple_items_for_space", None)
            bulk_params = set(self._safe_signature_params(bulk_method)) if callable(bulk_method) else set()

            mode: str
            if callable(bulk_method) and "items" in bulk_params:
                result = bulk_method(space_key, items=items)
                mode = "native-items"
            elif callable(bulk_method) and ("user_key" in bulk_params or "group_name" in bulk_params):
                compat_results: list[dict[str, Any]] = []
                for target_type, target_value, operations in normalized_items:
                    kwargs: dict[str, Any] = {"operations": operations}
                    if target_type == "user":
                        kwargs["user_key"] = target_value
                    elif target_type == "group":
                        kwargs["group_name"] = target_value
                    compat_results.append(self._coerce_dict(bulk_method(space_key, **kwargs)))
                result = {
                    "mode": "legacy-bulk",
                    "items_processed": len(normalized_items),
                    "results": compat_results,
                }
                mode = "legacy-bulk"
            else:
                compat_results = []
                for target_type, target_value, operations in normalized_items:
                    if target_type == "user":
                        compat_results.append(
                            self._coerce_dict(
                                self._client.set_permissions_to_user_for_space(  # type: ignore[attr-defined]
                                    space_key,
                                    target_value,
                                    operations=operations,
                                )
                            )
                        )
                    elif target_type == "group":
                        compat_results.append(
                            self._coerce_dict(
                                self._client.set_permissions_to_group_for_space(  # type: ignore[attr-defined]
                                    space_key,
                                    target_value,
                                    operations=operations,
                                )
                            )
                        )
                    else:
                        compat_results.append(
                            self._coerce_dict(
                                self._client.set_permissions_to_anonymous_for_space(  # type: ignore[attr-defined]
                                    space_key,
                                    operations=operations,
                                )
                            )
                        )
                result = {
                    "mode": "expanded-fallback",
                    "items_processed": len(normalized_items),
                    "results": compat_results,
                }
                mode = "expanded-fallback"

            self._log.info(
                "space_permissions_bulk_set",
                space_key=space_key,
                items=len(normalized_items),
                mode=mode,
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"set_permissions_to_multiple_items_for_space {space_key}")

    def remove_permissions_from_user_for_space(self, space_key: str, user_key: str) -> dict[str, Any]:
        """Remove all permissions granted to a user for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.remove_permissions_from_user_for_space(space_key, user_key)
            self._log.info("space_permissions_user_removed", space_key=space_key, user_key=user_key)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"remove_permissions_from_user_for_space {space_key} {user_key}")

    def remove_permissions_from_group_for_space(self, space_key: str, group_name: str) -> dict[str, Any]:
        """Remove all permissions granted to a group for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.remove_permissions_from_group_for_space(space_key, group_name)
            self._log.info("space_permissions_group_removed", space_key=space_key, group_name=group_name)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"remove_permissions_from_group_for_space {space_key} {group_name}")

    def remove_permissions_from_anonymous_for_space(self, space_key: str) -> dict[str, Any]:
        """Remove permissions granted to anonymous users for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.remove_permissions_from_anonymous_for_space(space_key)
            self._log.info("space_permissions_anonymous_removed", space_key=space_key)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"remove_permissions_from_anonymous_for_space {space_key}")

    # --- User & Group Management ---

    def get_all_groups(self, start: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        """Get all groups in Confluence."""

        def operation() -> list[dict[str, Any]]:
            result = self._client.get_all_groups(start=start, limit=limit)
            self._log.debug(
                "groups_retrieved", count=len(result) if isinstance(result, list) else 0, start=start, limit=limit
            )
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"get_all_groups start={start} limit={limit}")

    def get_group_members(self, group_name: str, start: int = 0, limit: int = 1000) -> list[dict[str, Any]]:
        """Get members of a group."""

        def operation() -> list[dict[str, Any]]:
            result = self._client.get_group_members(group_name, start=start, limit=limit)
            self._log.debug(
                "group_members_retrieved", group_name=group_name, count=len(result) if isinstance(result, list) else 0
            )
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"get_group_members {group_name} start={start} limit={limit}")

    def get_user_details_by_username(self, username: str, expand: str | None = None) -> dict[str, Any]:
        """Get user details by username."""

        def operation() -> dict[str, Any]:
            result = self._client.get_user_details_by_username(username, expand=expand)
            self._log.debug("user_retrieved_by_username", username=username)
            return self._require_dict(result, "get_user_details_by_username")

        return self._with_retry(operation, f"get_user_details_by_username {username}")

    def get_user_details_by_userkey(self, userkey: str, expand: str | None = None) -> dict[str, Any]:
        """Get user details by user key."""

        def operation() -> dict[str, Any]:
            result = self._client.get_user_details_by_userkey(userkey, expand=expand)
            self._log.debug("user_retrieved_by_userkey", userkey=userkey)
            return self._require_dict(result, "get_user_details_by_userkey")

        return self._with_retry(operation, f"get_user_details_by_userkey {userkey}")

    def change_user_password(self, username: str, password: str) -> None:
        """Change user password."""

        def operation() -> None:
            self._client.change_user_password(username, password)
            self._log.info("user_password_changed", username=username)

        return self._with_retry(operation, f"change_user_password {username}")

    def add_user_to_group(self, username: str, group_name: str) -> None:
        """Add user to group."""

        def operation() -> None:
            self._client.add_user_to_group(username, group_name)
            self._log.info("user_added_to_group", username=username, group_name=group_name)

        return self._with_retry(operation, f"add_user_to_group {username} {group_name}")

    def remove_user_from_group(self, username: str, group_name: str) -> None:
        """Remove user from group."""

        def operation():
            self._client.remove_user_from_group(username, group_name)
            self._log.info("user_removed_from_group", username=username, group_name=group_name)

        return self._with_retry(operation, f"remove_user_from_group {username} {group_name}")

    # --- Export Operations ---

    def export_page(self, page_id: str, api_version: str | None = None) -> bytes:
        """Export page as PDF.

        Note: The SDK auto-detects Cloud/Server mode based on client initialization.
        The api_version parameter is accepted for CLI compatibility but not passed to SDK.
        """

        def operation():
            # SDK auto-detects Cloud/Server mode, so we don't pass api_version
            # The parameter is kept for CLI compatibility but ignored here
            result = self._client.export_page(page_id)  # type: ignore[call-arg]
            detected_mode = "cloud" if self._is_cloud else "server"
            self._log.info("page_exported", page_id=page_id, detected_mode=detected_mode)
            # SDK returns bytes or file path; ensure we return bytes
            if isinstance(result, bytes):
                return self._coerce_bytes(result)
            elif isinstance(result, str):
                # If it's a file path, read it
                with open(result, "rb") as f:
                    return f.read()
            else:
                raise VDSClientError(
                    f"Unexpected export_page return type: {type(result)}", context={"page_id": page_id}
                )

        return self._with_retry(operation, f"export_page {page_id}")

    def get_space_export(self, space_key: str, export_type: str) -> str:
        """Get space export download URL."""

        def operation() -> str:
            result = self._client.get_space_export(space_key, export_type)
            self._log.info("space_export_url_retrieved", space_key=space_key, export_type=export_type)
            return result if isinstance(result, str) else str(result)

        return self._with_retry(operation, f"get_space_export {space_key} {export_type}")

    # --- Draft Management (Server-only) ---

    def get_draft_page_by_id(self, page_id: str) -> dict[str, Any]:
        """Get draft page by ID (Server-only)."""
        if self._is_cloud:
            raise VDSClientError(
                "get_draft_page_by_id is only available in Confluence Server/Data Center mode",
                context={"page_id": page_id},
            )

        def operation() -> dict[str, Any]:
            result = self._client.get_draft_page_by_id(page_id)  # type: ignore[attr-defined]
            self._log.debug("draft_page_retrieved", page_id=page_id)
            return self._require_dict(result, "get_draft_page_by_id")

        return self._with_retry(operation, f"get_draft_page_by_id {page_id}")

    def get_all_draft_pages_from_space(self, space_key: str, limit: int = 25) -> list[dict[str, Any]]:
        """Get all draft pages from a space (Server-only)."""
        if self._is_cloud:
            raise VDSClientError(
                "get_all_draft_pages_from_space is only available in Confluence Server/Data Center mode",
                context={"space_key": space_key},
            )

        def operation() -> list[dict[str, Any]]:
            result = self._client.get_all_draft_pages_from_space(space_key, limit=limit)  # type: ignore[attr-defined]
            self._log.debug(
                "draft_pages_retrieved", space_key=space_key, count=len(result) if isinstance(result, list) else 0
            )
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"get_all_draft_pages_from_space {space_key}")

    def remove_page_as_draft(self, page_id: str) -> None:
        """Remove page as draft (Server-only)."""
        if self._is_cloud:
            raise VDSClientError(
                "remove_page_as_draft is only available in Confluence Server/Data Center mode",
                context={"page_id": page_id},
            )

        def operation() -> None:
            self._client.remove_page_as_draft(page_id)  # type: ignore[attr-defined]
            self._log.info("draft_page_removed", page_id=page_id)

        return self._with_retry(operation, f"remove_page_as_draft {page_id}")

    # --- Cache Management (Server-only) ---

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get cache statistics (Server-only)."""
        if self._is_cloud:
            raise VDSClientError(
                "get_cache_statistics is only available in Confluence Server/Data Center mode",
                context={},
            )

        def operation():
            # SDK doesn't have get_cache_statistics, use REST API directly
            # Cache statistics endpoint: /rest/cache/1.0/stats
            response = self.request(method="GET", path="/rest/cache/1.0/stats")
            # SDK request method returns response object, extract JSON
            if hasattr(response, "json"):
                result = response.json()
            else:
                result = response  # Already JSON dict
            self._log.debug("cache_statistics_retrieved")
            return self._coerce_dict(result)

        return self._with_retry(operation, "get_cache_statistics")

    def flush_cache(self, cache_name: str | None = None) -> None:
        """Flush cache (Server-only).

        Args:
            cache_name: Optional cache name to flush specific cache. If None, flushes all caches.
        """
        if self._is_cloud:
            raise VDSClientError(
                "flush_cache is only available in Confluence Server/Data Center mode",
                context={"cache_name": cache_name},
            )

        def operation() -> None:
            if cache_name:
                # Flush specific cache package
                self._client.clean_package_cache(cache_name=cache_name)  # type: ignore[attr-defined]
                self._log.info("cache_flushed", cache_name=cache_name)
            else:
                # Flush all caches
                self._client.clean_all_caches()  # type: ignore[attr-defined]
                self._log.info("all_caches_flushed")

        return self._with_retry(operation, f"flush_cache {cache_name or 'all'}")

    def get_cache_size(self) -> dict[str, Any]:
        """Get cache size information (Server-only)."""
        if self._is_cloud:
            raise VDSClientError(
                "get_cache_size is only available in Confluence Server/Data Center mode",
                context={},
            )

        def operation():
            # SDK doesn't have get_cache_size, use REST API directly
            # Cache size endpoint: /rest/cache/1.0/size
            response = self.request(method="GET", path="/rest/cache/1.0/size")
            # SDK request method returns response object, extract JSON
            if hasattr(response, "json"):
                result = response.json()
            else:
                result = response  # Already JSON dict
            self._log.debug("cache_size_retrieved")
            return self._coerce_dict(result)

        return self._with_retry(operation, "get_cache_size")

    # --- Advanced Content Operations ---

    def get_page_ancestors(self, page_id: str) -> list[dict[str, Any]]:
        """Get page ancestors (parent pages)."""

        def operation() -> list[dict[str, Any]]:
            result = self._client.get_page_ancestors(page_id)  # type: ignore[attr-defined]
            self._log.debug(
                "page_ancestors_retrieved", page_id=page_id, count=len(result) if isinstance(result, list) else 0
            )
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"get_page_ancestors {page_id}")

    def move_page(
        self,
        page_id: str,
        target_title: str,
        position: str = "append",
        *,
        space_key: str | None = None,
    ) -> dict[str, Any]:
        """Move page to a new location."""

        def operation() -> dict[str, Any]:
            move_page_method = getattr(self._client, "move_page", None)
            if not callable(move_page_method):
                raise VDSClientError("SDK does not support move_page")

            move_params = set(self._safe_signature_params(move_page_method))
            if "space_key" in move_params and "page_id" in move_params:
                resolved_space_key = space_key
                if not resolved_space_key and hasattr(self._client, "get_page_space"):
                    raw_space_key = self._client.get_page_space(page_id)  # type: ignore[attr-defined]
                    if isinstance(raw_space_key, str) and raw_space_key.strip():
                        resolved_space_key = raw_space_key.strip()
                if not resolved_space_key:
                    page = self._client.get_page_by_id(page_id, expand="space")
                    if isinstance(page, dict):
                        page_space = page.get("space")
                        if isinstance(page_space, dict):
                            raw_space_key = page_space.get("key")
                            if raw_space_key:
                                resolved_space_key = str(raw_space_key).strip()
                if not resolved_space_key:
                    raise VDSClientError(
                        "Unable to resolve space key for move_page",
                        context={"page_id": page_id},
                    )

                legacy_position = {"before": "above", "after": "below"}.get(position, position)
                result = move_page_method(
                    resolved_space_key,
                    page_id,
                    target_title=target_title,
                    position=legacy_position,
                )
                self._log.info(
                    "page_moved",
                    page_id=page_id,
                    target_title=target_title,
                    position=position,
                    resolved_position=legacy_position,
                    space_key=resolved_space_key,
                    move_contract="legacy",
                )
                return self._coerce_dict(result)

            result = move_page_method(page_id, target_title, position=position)
            self._log.info(
                "page_moved",
                page_id=page_id,
                target_title=target_title,
                position=position,
                move_contract="modern",
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"move_page {page_id} {target_title}")

    def get_tables_from_page(self, page_id: str) -> list[dict[str, Any]]:
        """Extract tables from page."""

        def operation() -> list[dict[str, Any]]:
            result = self._client.get_tables_from_page(page_id)  # type: ignore[attr-defined]
            self._log.debug("tables_extracted", page_id=page_id, count=len(result) if isinstance(result, list) else 0)
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"get_tables_from_page {page_id}")

    def scrap_regex_from_page(self, page_id: str, regex: str) -> list[dict[str, Any]]:
        """Extract regex matches from page."""

        def operation() -> list[dict[str, Any]]:
            result = self._client.scrap_regex_from_page(page_id, regex)  # type: ignore[attr-defined]
            self._log.debug(
                "regex_matches_extracted",
                page_id=page_id,
                pattern=regex,
                count=len(result) if isinstance(result, list) else 0,
            )
            return result if isinstance(result, list) else []

        return self._with_retry(operation, f"scrap_regex_from_page {page_id} {regex}")

    def get_all_restrictions_for_content(self, content_id: str) -> dict[str, Any]:
        """Get all restrictions for content."""

        def operation() -> dict[str, Any]:
            result = self._client.get_all_restrictions_for_content(content_id)  # type: ignore[attr-defined]
            self._log.debug("content_restrictions_retrieved", content_id=content_id)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"get_all_restrictions_for_content {content_id}")

    # --- History & Versioning ---

    def history(self, page_id: str) -> dict[str, Any]:
        """Get page history."""

        def operation() -> dict[str, Any]:
            result = self._client.history(page_id)  # type: ignore[attr-defined]
            self._log.debug("page_history_retrieved", page_id=page_id)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"history {page_id}")

    def get_content_history_by_version_number(self, page_id: str, version: int) -> dict[str, Any]:
        """Get specific version of content."""

        def operation() -> dict[str, Any]:
            result = self._client.get_content_history_by_version_number(page_id, version)  # type: ignore[attr-defined]
            self._log.debug("content_version_retrieved", page_id=page_id, version=version)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"get_content_history_by_version_number {page_id} {version}")

    def remove_content_history(self, page_id: str, version: int) -> None:
        """Remove content history (experimental)."""

        def operation():
            self._client.remove_content_history(page_id, version)  # type: ignore[attr-defined]
            self._log.info("content_history_removed", page_id=page_id, version=version)

        return self._with_retry(operation, f"remove_content_history {page_id} {version}")

    def archive_space(self, space_key: str) -> dict[str, Any]:
        """Archive a Confluence space."""

        def operation() -> dict[str, Any]:
            result = self._client.archive_space(space_key)
            self._log.info("space_archived", space_key=space_key)
            return result or {"status": "archived"}

        return self._with_retry(operation, f"archive_space {space_key}")

    def get_trashed_contents_by_space(
        self,
        space_key: str,
        *,
        cursor: str | None = None,
        expand: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """List trashed content for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.get_trashed_contents_by_space(
                space_key,
                cursor=cursor,
                expand=expand,
                limit=limit,
            )
            count = len(result.get("results", [])) if isinstance(result, dict) else 0
            self._log.debug(
                "space_trash_listed",
                space_key=space_key,
                count=count,
                cursor=cursor,
                limit=limit,
            )
            return self._coerce_dict(result)

        return self._with_retry(operation, f"get_trashed_contents_by_space {space_key}")

    def remove_trashed_contents_by_space(self, space_key: str) -> dict[str, Any]:
        """Remove trashed content for a space."""

        def operation() -> dict[str, Any]:
            result = self._client.remove_trashed_contents_by_space(space_key)
            self._log.info("space_trash_cleared", space_key=space_key)
            return result or {"status": "removed"}

        return self._with_retry(operation, f"remove_trashed_contents_by_space {space_key}")

    def get_child_pages(self, page_id: str, expand: list[str] | None = None) -> list[dict[str, Any]]:
        """Get child pages of a page.

        Uses the official SDK `get_page_child_by_type()` when available so callers can:
        - control pagination reliably
        - request expanded fields (for example `body.storage`) in one round trip
        """

        def operation():
            expand_arg = ",".join(expand) if expand else None

            # `atlassian.Confluence.get_child_pages()` does not expose pagination controls.
            # Prefer `get_page_child_by_type()` so crawlers don't silently miss children.
            if hasattr(self._client, "get_page_child_by_type"):
                start = 0
                limit = 100
                collected: list[dict[str, Any]] = []
                seen_starts: set[int] = set()
                seen_tokens: set[str] = set()
                guard_reason: str | None = None

                while True:
                    if start in seen_starts:
                        guard_reason = "repeated_start"
                        break
                    seen_starts.add(start)

                    payload = self._client.get_page_child_by_type(
                        page_id,
                        type="page",
                        start=start,
                        limit=limit,
                        expand=expand_arg,
                    )
                    results: list[dict[str, Any]] = []
                    if isinstance(payload, dict):
                        raw = payload.get("results", [])
                        if isinstance(raw, list):
                            results = [item for item in raw if isinstance(item, dict)]
                    elif isinstance(payload, list):
                        results = [item for item in payload if isinstance(item, dict)]
                    else:
                        results = []

                    if not results:
                        break

                    collected.extend(results)

                    next_start: int | None = None
                    next_token: str | None = None
                    if isinstance(payload, dict):
                        next_start, next_token = self._extract_pagination_marker(payload)

                    if next_token:
                        if next_token in seen_tokens:
                            guard_reason = "repeated_token"
                            break
                        seen_tokens.add(next_token)

                    if next_start is not None:
                        if next_start <= start:
                            guard_reason = "no_progress_start"
                            break
                        start = next_start
                        continue

                    if len(results) < limit:
                        break
                    start += limit

                if guard_reason:
                    log_fn = self._log.info if guard_reason == "no_progress_start" else self._log.warning
                    log_fn(
                        "child_pages_pagination_guard_triggered",
                        page_id=page_id,
                        reason=guard_reason,
                        count=len(collected),
                        last_start=start,
                    )

                self._log.debug(
                    "child_pages_retrieved",
                    page_id=page_id,
                    count=len(collected),
                    expand=expand_arg,
                )
                return collected

            result = self._client.get_child_pages(page_id)
            # Convert generator to list if needed.
            if result is not None and hasattr(result, "__iter__") and not isinstance(result, (list, tuple, dict)):
                result = list(result)
            result_list: list[dict[str, Any]] = []
            if isinstance(result, list):
                result_list = [item for item in result if isinstance(item, dict)]
            self._log.debug(
                "child_pages_retrieved",
                page_id=page_id,
                count=len(result_list),
                expand=expand_arg,
            )
            return result_list

        return self._with_retry(operation, f"get_child_pages {page_id}")

    def get_page_by_title(self, space_key: str, title: str) -> dict[str, Any] | None:
        """Get a page by space and title."""
        try:
            result = self._client.get_page_by_title(space_key, title)
            self._log.debug("page_retrieved_by_title", space_key=space_key, title=title)
            if result is None:
                return None
            return self._require_dict(result, "get_page_by_title")

        except Exception as exc:
            self._handle_api_error(exc, f"get_page_by_title {space_key}/{title}")
            raise

    def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
        """Get attachments for a page."""
        try:
            start = 0
            limit = 50
            collected: list[dict[str, Any]] = []
            seen_starts: set[int] = set()
            seen_tokens: set[str] = set()
            guard_reason: str | None = None

            while True:
                if start in seen_starts:
                    guard_reason = "repeated_start"
                    break
                seen_starts.add(start)

                payload = self._client.get_attachments_from_content(page_id, start=start, limit=limit)
                results: list[dict[str, Any]] = []
                if isinstance(payload, dict):
                    raw = payload.get("results", [])
                    if isinstance(raw, list):
                        results = [item for item in raw if isinstance(item, dict)]
                elif isinstance(payload, list):
                    results = [item for item in payload if isinstance(item, dict)]
                else:
                    results = []

                if not results:
                    break

                collected.extend(results)

                next_start: int | None = None
                next_token: str | None = None
                if isinstance(payload, dict):
                    next_start, next_token = self._extract_pagination_marker(payload)

                if next_token:
                    if next_token in seen_tokens:
                        guard_reason = "repeated_token"
                        break
                    seen_tokens.add(next_token)

                if next_start is not None:
                    if next_start <= start:
                        guard_reason = "no_progress_start"
                        break
                    start = next_start
                    continue

                if len(results) < limit:
                    break
                start += limit

            if guard_reason:
                log_fn = self._log.info if guard_reason == "no_progress_start" else self._log.warning
                log_fn(
                    "attachments_pagination_guard_triggered",
                    page_id=page_id,
                    reason=guard_reason,
                    count=len(collected),
                    last_start=start,
                )

            self._log.debug("attachments_retrieved", page_id=page_id, count=len(collected))
            return collected

        except Exception as exc:
            self._handle_api_error(exc, f"get_attachments {page_id}")
            raise

    def get_attachment_content(self, attachment_id: str) -> bytes:
        """Get attachment content by ID."""
        try:
            # Cloud SDKs expose `get_attachment_data`, but Server variants may not.
            get_attachment_data = getattr(self._client, "get_attachment_data", None)
            if callable(get_attachment_data):
                result = get_attachment_data(attachment_id)
                self._log.debug("attachment_content_retrieved", attachment_id=attachment_id, source="sdk")
                return self._coerce_bytes(result)

            # Fallback for Confluence Server: resolve the attachment metadata, then download via `_links.download`.
            from urllib.parse import urlparse

            def _raise_for_status(response: Any) -> None:
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                    return
                status_code = getattr(response, "status_code", None)
                if isinstance(status_code, int) and status_code >= 400:
                    raise ResponseError(
                        f"Unexpected status {status_code}",
                        status_code=status_code,
                        context={"status_code": status_code},
                    )

            def _as_path(url_or_path: str) -> str:
                if url_or_path.startswith(("http://", "https://")):
                    parsed = urlparse(url_or_path)
                    path = parsed.path or "/"
                    if parsed.query:
                        path = f"{path}?{parsed.query}"
                    return path
                return url_or_path if url_or_path.startswith("/") else f"/{url_or_path}"

            meta_response = self.request(
                "GET",
                f"/rest/api/content/{attachment_id}",
                params={"expand": "version"},
            )
            _raise_for_status(meta_response)
            payload = meta_response.json()
            download_link = None
            if isinstance(payload, dict):
                links = payload.get("_links")
                if isinstance(links, dict):
                    download_link = links.get("download")
            if not download_link or not isinstance(download_link, str):
                raise VDSClientError(
                    "Attachment download link not found in response",
                    context={"attachment_id": attachment_id},
                )

            download_response = self.request(
                "GET",
                _as_path(download_link),
                headers={"Accept": "*/*"},
            )
            _raise_for_status(download_response)
            content = getattr(download_response, "content", None)
            if isinstance(content, bytes):
                self._log.debug("attachment_content_retrieved", attachment_id=attachment_id, source="download_link")
                return content
            # Fallback: some clients expose bytes via `read()` or `text`.
            if hasattr(download_response, "read"):
                data = download_response.read()
                if isinstance(data, bytes):
                    self._log.debug(
                        "attachment_content_retrieved", attachment_id=attachment_id, source="download_link_read"
                    )
                    return data
            text = getattr(download_response, "text", "")
            self._log.debug("attachment_content_retrieved", attachment_id=attachment_id, source="download_link_text")
            return (text or "").encode("utf-8")

        except Exception as exc:
            self._handle_api_error(exc, f"get_attachment_content {attachment_id}")
            raise

    def update_attachment_data(
        self,
        page_id: str,
        attachment_id: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing attachment.

        According to atlassian-python-api docs, attach_content automatically updates
        if the file exists, versioning the new file and keeping the old one.
        """

        def operation() -> dict[str, Any]:
            # Use attach_content - it automatically updates if file exists
            # See: https://atlassian-python-api.readthedocs.io/confluence.html#
            result = self._client.attach_content(
                content=content,
                name=filename,
                content_type=content_type or "application/octet-stream",
                page_id=page_id,
                comment=comment,
            )
            self._log.info("attachment_updated", page_id=page_id, attachment_id=attachment_id, filename=filename)
            return self._coerce_dict(result)

        return self._with_retry(operation, f"update_attachment {attachment_id}")

    def delete_attachment_by_id(self, page_id: str, attachment_id: str, version: int | None = None) -> None:
        """Delete an attachment by ID (historic versions only).

        The Atlassian SDK's ``delete_attachment_by_id`` endpoint only removes versions
        strictly lower than the current one, so callers should provide ``version`` when
        targeting a specific revision. Cloud docs:
        https://atlassian-python-api.readthedocs.io/confluence.html#confluence.Confluence.delete_attachment_by_id
        """
        try:
            versions_payload = self._client.get_attachment_history(attachment_id) or []
        except Exception:  # pragma: no cover - defensive
            versions_payload = []

        versions = []
        for item in versions_payload:
            if isinstance(item, dict):
                number = item.get("number")
                if isinstance(number, int):
                    versions.append(number)

        if version is not None:
            versions = [ver for ver in versions if ver == version]

        if not versions:
            if version is not None:
                versions = [version]
            else:
                raise VDSClientError(
                    f"No attachment versions found for {attachment_id}. Specify --version explicitly.",
                    context={"attachment_id": attachment_id, "page_id": page_id},
                )

        for ver in sorted(set(versions), reverse=True):
            try:
                self._client.delete_attachment_by_id(attachment_id, ver)
                self._log.info(
                    "attachment_version_deleted",
                    page_id=page_id,
                    attachment_id=attachment_id,
                    version=ver,
                )
            except Exception as exc:
                self._handle_api_error(exc, f"delete_attachment {attachment_id} (version {ver})")

    def delete_attachment(self, page_id: str, filename: str, version: int | None = None) -> None:
        """Delete the latest version of an attachment by filename.

        Mirrors :py:meth:`Confluence.delete_attachment` from the Atlassian SDK.
        """

        try:
            self._client.delete_attachment(page_id, filename, version=version)
            self._log.info(
                "attachment_deleted",
                page_id=page_id,
                filename=filename,
                version=version,
            )
        except Exception as exc:
            self._handle_api_error(exc, f"delete_attachment {filename}")

    def add_comment(self, page_id: str, body: str, parent_id: str | None = None) -> dict[str, Any]:
        """Add a comment to a page or reply to an existing comment.

        When ``parent_id`` is provided, the comment will be created as a reply
        to the specified parent comment (threaded reply), mirroring
        :py:meth:`Confluence.add_comment` from the Atlassian SDK.
        """

        comment_params = set(self._safe_signature_params(self._client.add_comment))
        supports_parent = "parent_id" in comment_params or len(comment_params) >= 4
        if parent_id is not None and not supports_parent:
            raise VDSClientError(
                "Installed atlassian-python-api build does not support parent comment replies",
                context={"page_id": page_id},
            )

        def _op() -> dict[str, Any]:
            if parent_id is not None:
                result = self._client.add_comment(page_id, body, parent_id)  # type: ignore[call-arg]
            else:
                result = self._client.add_comment(page_id, body)
            self._log.info("comment_added", page_id=page_id, parent_id=parent_id)
            return self._coerce_dict(result)

        return self._with_retry(_op, "add_comment")

    def get_page_history(self, page_id: str) -> dict[str, Any]:
        """Get page version history."""
        try:
            history_method = getattr(self._client, "get_history", None)
            if not callable(history_method):
                history_method = getattr(self._client, "history", None)
            if not callable(history_method):
                raise VDSClientError("SDK does not support page history retrieval")
            result = history_method(page_id)
            self._log.debug("page_history_retrieved", page_id=page_id)
            return self._coerce_dict(result)

        except Exception as exc:
            self._handle_api_error(exc, f"get_page_history {page_id}")
            raise

    @property
    def base_url(self) -> str:
        """Base URL of the Confluence server (no trailing slash)."""
        return str(self._settings.url_for(self._server)).rstrip("/")

    # --- Label Operations ---

    def get_page_labels(self, page_id: str) -> list[dict[str, Any]]:
        """Return raw label result list for a page."""

        def operation() -> list[dict[str, Any]]:
            method = getattr(self._client, "get_page_labels", None)
            if not callable(method):
                # Fallback: REST endpoint (older SDK versions)
                resp = self._client.request("GET", f"rest/api/content/{page_id}/label")
                payload = resp.json() if hasattr(resp, "json") else {}
                return payload.get("results", []) if isinstance(payload, dict) else []
            result = method(page_id)
            if isinstance(result, dict):
                return result.get("results", [])
            return list(result) if result else []

        return self._with_retry(operation, f"get_page_labels {page_id}")

    def set_page_label(self, page_id: str, label: str) -> None:
        """Add a label to a page."""

        def operation() -> None:
            method = getattr(self._client, "set_page_label", None)
            if not callable(method):
                # Fallback: REST endpoint (older SDK versions)
                self._client.request(
                    "POST",
                    f"rest/api/content/{page_id}/label",
                    data=[{"prefix": "global", "name": label}],
                )
                return
            method(page_id, label)

        return self._with_retry(operation, f"set_page_label {page_id}")

    def close(self) -> None:
        """Close the client (cleanup method for compatibility)."""
        # atlassian-python-api doesn't require explicit cleanup
        pass

    def __enter__(self) -> ConfluenceClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["ConfluenceClient"]
