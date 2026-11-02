"""Grafana and Quickwit clients via Grafana Datasource Proxy using HTTPX.

This module provides clients that communicate with Quickwit through
Grafana's Datasource Proxy API.

Architecture:
    Client -> Grafana API -> Datasource Proxy -> Quickwit REST API
                                              -> Quickwit ES-compatible API

The clients use:
- HTTPX for HTTP communication (matches elastic_orchestrator, confluence_orchestrator)
- Connection pooling for performance
"""

from __future__ import annotations

import json
import time
import warnings
from typing import TYPE_CHECKING, Any

import httpx
from vds_platform_core.http.errors import map_http_error

from vds_grafana_orchestrator.errors import (
    ClientTimeoutError,
    NotFoundError,
    TransportError,
    VDSClientError,
)

if TYPE_CHECKING:
    from vds_grafana_orchestrator.config import GrafanaSettings

# Suppress InsecureRequestWarning for self-signed certs
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Quickwit datasource type identifier
QUICKWIT_DATASOURCE_TYPE = "quickwit-quickwit-datasource"


class GrafanaClient:
    """Low-level Grafana API client using HTTPX.

    This client provides access to Grafana API endpoints including
    health checks, datasource discovery, and datasource proxy operations.

    Example:
        >>> from vds_grafana_orchestrator import GrafanaClient, load_settings
        >>> settings = load_settings()
        >>> with GrafanaClient(settings) as client:
        ...     health = client.health()
        ...     print(health)
    """

    def __init__(self, config: GrafanaSettings) -> None:
        """Initialize the client with configuration.

        Args:
            config: GrafanaSettings instance with connection parameters.
        """
        self.config = config
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTPX client (lazy initialization)."""
        if self._client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                **self.config.auth_header,
            }

            self._client = httpx.Client(
                base_url=self.config.base_url,
                headers=headers,
                verify=self.config.verify_certs,
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.request_timeout,
                    write=self.config.request_timeout,
                    pool=self.config.connect_timeout,
                ),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                ),
            )
        return self._client

    @property
    def client(self) -> httpx.Client:
        """Access the HTTPX client instance."""
        return self._get_client()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any] | list[Any]:
        """Raise a platform_core error on non-2xx; return parsed JSON body otherwise."""
        try:
            data: dict[str, Any] | list[Any] = response.json()
        except Exception:
            data = {"raw_response": response.text, "status_code": response.status_code}  # type: ignore[assignment]
        if not response.is_success:
            raise map_http_error(response.status_code, data, service="grafana")
        return data

    def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        content: bytes | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue an HTTP request with transport-level retry governed by config.max_retries."""
        attempts = max(1, self.config.max_retries)
        last_exc: httpx.TransportError | None = None
        for attempt in range(attempts):
            try:
                return self.client.request(
                    method,
                    url=path,
                    json=json_body,
                    params=params,
                    content=content,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise ClientTimeoutError(f"Request timed out: {method} {path}") from exc
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt >= attempts - 1:
                    break
        raise TransportError(
            f"Transport failed after {attempts} attempt(s): {method} {path}",
        ) from last_exc

    # -------------------------------------------------------------------------
    # Grafana Health and Info
    # -------------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Check Grafana health via /api/health.

        Returns:
            Grafana health response with commit, database, version.
        """
        response = self._request("GET", "/api/health")
        result = self._handle_response(response)
        return result if isinstance(result, dict) else {"data": result}

    # -------------------------------------------------------------------------
    # Datasource Operations
    # -------------------------------------------------------------------------

    def datasources(self) -> list[dict[str, Any]]:
        """List all datasources.

        Returns:
            List of datasource configurations.
        """
        response = self._request("GET", "/api/datasources")
        result = self._handle_response(response)
        return result if isinstance(result, list) else []

    def quickwit_datasources(self) -> list[dict[str, Any]]:
        """List Quickwit datasources only.

        Returns:
            List of datasources with type 'quickwit-quickwit-datasource'.
        """
        all_datasources = self.datasources()
        return [ds for ds in all_datasources if ds.get("type") == QUICKWIT_DATASOURCE_TYPE]

    def resolve_datasource(
        self,
        uid: str | None = None,
        datasource_id: int | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a datasource by UID, ID, or name.

        Args:
            uid: Datasource UID (preferred).
            datasource_id: Datasource ID (legacy).
            name: Datasource name.

        Returns:
            Datasource configuration dict.

        Raises:
            NotFoundError: If datasource not found.
            ValueError: If no lookup parameter provided.
        """
        if uid:
            response = self._request("GET", f"/api/datasources/uid/{uid}")
            result = self._handle_response(response)
            return result if isinstance(result, dict) else {}

        if datasource_id:
            response = self._request("GET", f"/api/datasources/{datasource_id}")
            result = self._handle_response(response)
            return result if isinstance(result, dict) else {}

        if name:
            response = self._request("GET", f"/api/datasources/name/{name}")
            result = self._handle_response(response)
            return result if isinstance(result, dict) else {}

        raise ValueError("At least one of uid, datasource_id, or name must be provided")

    def get_default_datasource(self) -> dict[str, Any] | None:
        """Get the default datasource from config or first Quickwit datasource.

        Returns:
            Datasource configuration dict or None if not found.
        """
        # Try config-specified datasource first
        if self.config.datasource_uid:
            try:
                return self.resolve_datasource(uid=self.config.datasource_uid)
            except NotFoundError:
                pass

        if self.config.datasource_id:
            try:
                return self.resolve_datasource(datasource_id=self.config.datasource_id)
            except NotFoundError:
                pass

        if self.config.datasource_name:
            try:
                return self.resolve_datasource(name=self.config.datasource_name)
            except NotFoundError:
                pass

        # Fall back to first Quickwit datasource
        quickwit_ds = self.quickwit_datasources()
        return quickwit_ds[0] if quickwit_ds else None

    # -------------------------------------------------------------------------
    # Datasource Proxy Operations
    # -------------------------------------------------------------------------

    def proxy_get(
        self,
        datasource_uid: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a GET request through the datasource proxy.

        Args:
            datasource_uid: Datasource UID.
            path: Path to append after proxy base (e.g., "/otel-logs-v0_7/search").
            params: Optional query parameters.

        Returns:
            Response data from the backend.
        """
        # Normalize path - remove leading slash if present
        path = path.lstrip("/")
        proxy_path = f"/api/datasources/proxy/uid/{datasource_uid}/{path}"

        response = self._request("GET", proxy_path, params=params)
        return self._handle_response(response)

    def proxy_post(
        self,
        datasource_uid: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a POST request through the datasource proxy.

        Args:
            datasource_uid: Datasource UID.
            path: Path to append after proxy base.
            body: Request body.
            params: Optional query parameters.

        Returns:
            Response data from the backend.
        """
        # Normalize path
        path = path.lstrip("/")
        proxy_path = f"/api/datasources/proxy/uid/{datasource_uid}/{path}"

        response = self._request("POST", proxy_path, json_body=body, params=params)
        return self._handle_response(response)

    # -------------------------------------------------------------------------
    # Context Manager and Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client and release connections."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> GrafanaClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close client."""
        self.close()


class QuickwitClient:
    """High-level Quickwit client via Grafana Datasource Proxy.

    This client provides Quickwit-specific operations including
    REST API search and ES-compatible API queries.

    Example:
        >>> from vds_grafana_orchestrator import QuickwitClient, load_settings
        >>> settings = load_settings()
        >>> with QuickwitClient(settings) as client:
        ...     results = client.search("otel-logs-v0_7", query="level:ERROR")
        ...     print(results)
    """

    def __init__(
        self,
        config: GrafanaSettings,
        datasource_uid: str | None = None,
        datasource_id: int | None = None,
        datasource_name: str | None = None,
    ) -> None:
        """Initialize the Quickwit client.

        Args:
            config: GrafanaSettings instance.
            datasource_uid: Override datasource UID (optional).
            datasource_id: Override datasource ID (optional).
            datasource_name: Override datasource name (optional).
        """
        self.config = config
        self._grafana = GrafanaClient(config)
        self._datasource_uid = datasource_uid
        self._datasource_id = datasource_id
        self._datasource_name = datasource_name
        self._resolved_datasource: dict[str, Any] | None = None

    @property
    def grafana(self) -> GrafanaClient:
        """Access the underlying GrafanaClient."""
        return self._grafana

    def _get_datasource_uid(self) -> str:
        """Get the datasource UID, resolving if necessary.

        Returns:
            Datasource UID string.

        Raises:
            NotFoundError: If no datasource can be resolved.
        """
        # Use explicit override first
        if self._datasource_uid:
            return self._datasource_uid

        # Try to resolve from other identifiers
        if self._datasource_id or self._datasource_name:
            ds = self._grafana.resolve_datasource(
                datasource_id=self._datasource_id,
                name=self._datasource_name,
            )
            self._resolved_datasource = ds
            return ds["uid"]

        # Use config defaults
        if self.config.datasource_uid:
            return self.config.datasource_uid

        # Try to resolve from config ID or name
        if self.config.datasource_id or self.config.datasource_name:
            ds = self._grafana.resolve_datasource(
                datasource_id=self.config.datasource_id,
                name=self.config.datasource_name,
            )
            self._resolved_datasource = ds
            return ds["uid"]

        # Fall back to first Quickwit datasource
        ds = self._grafana.get_default_datasource()
        if ds:
            self._resolved_datasource = ds
            return ds["uid"]

        raise NotFoundError(
            "No Quickwit datasource found. Please configure VDS_GRAFANA_DATASOURCE_UID "
            "or ensure a Quickwit datasource exists in Grafana."
        )

    # -------------------------------------------------------------------------
    # Quickwit REST API Operations
    # -------------------------------------------------------------------------

    def search(
        self,
        index: str | None = None,
        query: str = "*",
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        max_hits: int = 100,
        start_offset: int = 0,
        sort_by_field: str | None = None,
        sort_order: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search logs using Quickwit REST API.

        Args:
            index: Index pattern (default from config).
            query: Quickwit query string (default: "*").
            start_timestamp: Start time in Unix seconds (optional).
            end_timestamp: End time in Unix seconds (optional).
            max_hits: Maximum number of results (default: 100, max: 1000).
            start_offset: Pagination offset (default: 0).
            sort_by_field: Field to sort by (optional).
            sort_order: Sort order - "asc" or "desc" (optional).
            **kwargs: Additional Quickwit parameters.

        Returns:
            Quickwit search response with hits, num_hits, elapsed_time_micros.
        """
        index = index or self.config.default_index
        if not index:
            raise ValueError("Index is required. Set VDS_QUICKWIT_INDEX or pass index parameter.")

        # Enforce safe defaults
        max_hits = min(max_hits, 1000)

        # Build search parameters
        params: dict[str, Any] = {
            "query": query,
            "max_hits": max_hits,
            "start_offset": start_offset,
        }

        if start_timestamp is not None:
            params["start_timestamp"] = start_timestamp
        if end_timestamp is not None:
            params["end_timestamp"] = end_timestamp
        if sort_by_field:
            params["sort_by_field"] = sort_by_field
        if sort_order:
            params["sort_order"] = sort_order

        # Add any extra parameters
        params.update(kwargs)

        datasource_uid = self._get_datasource_uid()
        path = f"{index}/search"

        start_time = time.time()
        result = self._grafana.proxy_get(datasource_uid, path, params=params)
        elapsed_ms = (time.time() - start_time) * 1000

        # Add metadata for LLM traceability
        if isinstance(result, dict):
            result["_metadata"] = {
                "query": query,
                "index": index,
                "backend": "quickwit",
                "elapsed_ms": round(elapsed_ms, 2),
                "datasource_uid": datasource_uid,
            }

        return result if isinstance(result, dict) else {"data": result}

    def search_with_context(
        self,
        index: str | None = None,
        query: str = "*",
        at_timestamp: int | None = None,
        before_seconds: int = 60,
        after_seconds: int = 60,
        max_hits: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search logs with expanded time window around a timestamp.

        This is an LLM helper that expands the time window before and after
        a given timestamp to provide context.

        Args:
            index: Index pattern.
            query: Quickwit query string.
            at_timestamp: Center timestamp in Unix seconds.
            before_seconds: Seconds to look back (default: 60).
            after_seconds: Seconds to look forward (default: 60).
            max_hits: Maximum results (default: 100).
            **kwargs: Additional parameters.

        Returns:
            Search results with expanded time context.
        """
        if at_timestamp is None:
            at_timestamp = int(time.time())

        start_timestamp = at_timestamp - before_seconds
        end_timestamp = at_timestamp + after_seconds

        return self.search(
            index=index,
            query=query,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            max_hits=max_hits,
            **kwargs,
        )

    # -------------------------------------------------------------------------
    # Quickwit ES-Compatible API Operations
    # -------------------------------------------------------------------------

    def es_search(
        self,
        index: str | None = None,
        body: dict[str, Any] | None = None,
        size: int = 10,
        from_: int = 0,
        sort: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Search using ES-compatible Query DSL.

        Args:
            index: Index pattern.
            body: Elasticsearch Query DSL body.
            size: Number of results (default: 10).
            from_: Pagination offset (default: 0).
            sort: Sort specification.

        Returns:
            ES-compatible search response.
        """
        index = index or self.config.default_index
        if not index:
            raise ValueError("Index is required.")

        # Build request body
        request_body: dict[str, Any] = {
            "size": min(size, 1000),
            "from": from_,
        }

        if body:
            request_body.update(body)
        else:
            request_body["query"] = {"match_all": {}}

        if sort:
            request_body["sort"] = sort

        datasource_uid = self._get_datasource_uid()
        # ES-compatible endpoint path
        path = f"_elastic/{index}/_search"

        start_time = time.time()
        result = self._grafana.proxy_post(datasource_uid, path, body=request_body)
        elapsed_ms = (time.time() - start_time) * 1000

        if isinstance(result, dict):
            result["_metadata"] = {
                "index": index,
                "backend": "quickwit-es",
                "elapsed_ms": round(elapsed_ms, 2),
                "datasource_uid": datasource_uid,
            }

        return result if isinstance(result, dict) else {"data": result}

    def es_msearch(
        self,
        searches: list[tuple[dict[str, Any], dict[str, Any]]],
    ) -> dict[str, Any]:
        """Execute multiple ES-compatible searches.

        Args:
            searches: List of (header, body) tuples.

        Returns:
            ES-compatible msearch response with "responses" array.
        """
        datasource_uid = self._get_datasource_uid()
        ndjson = "\n".join(json.dumps(part) for search in searches for part in search) + "\n"
        path = f"/api/datasources/proxy/uid/{datasource_uid}/_elastic/_msearch"
        response = self._grafana._request(
            "POST",
            path,
            content=ndjson,
            headers={"Content-Type": "application/x-ndjson"},
        )
        result = self._grafana._handle_response(response)
        return result if isinstance(result, dict) else {"responses": result}

    # -------------------------------------------------------------------------
    # Index Discovery
    # -------------------------------------------------------------------------

    def indexes(self) -> list[dict[str, Any]]:
        """List available indexes via ES-compatible _cat/indices.

        Returns:
            List of index information dicts.
        """
        datasource_uid = self._get_datasource_uid()
        path = "_elastic/_cat/indices"
        params = {"format": "json"}

        result = self._grafana.proxy_get(datasource_uid, path, params=params)
        return result if isinstance(result, list) else []

    def fields(self, index: str | None = None) -> list[str]:
        """Get field names for an index (best-effort via sampling).

        This samples a single document and returns the _source keys.

        Args:
            index: Index to inspect.

        Returns:
            List of field names found in sample document.
        """
        index = index or self.config.default_index
        if not index:
            raise ValueError("Index is required.")

        try:
            # Search for a single document to sample fields
            result = self.es_search(index=index, size=1)
            hits = result.get("hits", {}).get("hits", [])
            if hits:
                source = hits[0].get("_source", {})
                return list(source.keys())
            return []
        except VDSClientError:
            return []

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Check connectivity to Grafana and Quickwit datasource.

        Returns:
            Health status dict with grafana_ok, datasource_ok, details.
        """
        result: dict[str, Any] = {
            "grafana_ok": False,
            "datasource_ok": False,
            "details": {},
        }

        # Check Grafana health
        try:
            grafana_health = self._grafana.health()
            result["grafana_ok"] = True
            result["details"]["grafana"] = grafana_health
        except VDSClientError as e:
            result["details"]["grafana_error"] = str(e)

        # Check datasource reachability
        if result["grafana_ok"]:
            try:
                datasource_uid = self._get_datasource_uid()
                # Try to list indexes as a connectivity check
                indexes = self.indexes()
                result["datasource_ok"] = True
                result["details"]["datasource_uid"] = datasource_uid
                result["details"]["index_count"] = len(indexes)
            except VDSClientError as e:
                result["details"]["datasource_error"] = str(e)

        return result

    # -------------------------------------------------------------------------
    # Context Manager and Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying Grafana client."""
        self._grafana.close()

    def __enter__(self) -> QuickwitClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close client."""
        self.close()


__all__ = ["GrafanaClient", "QuickwitClient", "QUICKWIT_DATASOURCE_TYPE"]
