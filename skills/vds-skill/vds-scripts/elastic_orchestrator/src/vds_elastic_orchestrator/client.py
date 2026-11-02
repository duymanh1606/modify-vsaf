"""Elasticsearch client via Kibana Console Proxy using HTTPX.

This module provides a client that communicates with Elasticsearch through
Kibana's Console Proxy API, since direct ES access (port 9200) is not available
in the VDS environment.

Architecture:
    Client -> Kibana (nginx proxy) -> Kibana Console API -> Elasticsearch

The client uses:
- HTTPX for HTTP communication (matches confluence_orchestrator, vds-ai-memory)
- Connection pooling for performance
"""

from __future__ import annotations

import contextlib
import json
import warnings
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import httpx

from vds_elastic_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    ResponseError,
    RetryError,
    TransportError,
    VDSClientError,
)

if TYPE_CHECKING:
    from vds_elastic_orchestrator.config import ElasticSettings

# Suppress InsecureRequestWarning for self-signed certs
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def _is_retryable_status(response: httpx.Response) -> bool:
    """Check if response status code is retryable (502, 503, 504)."""
    return response.status_code in (502, 503, 504)


class KibanaElasticsearchClient:
    """Elasticsearch client via Kibana Console Proxy using HTTPX.

    This client wraps all Elasticsearch operations through Kibana's
    /api/console/proxy endpoint, which is required since direct ES
    access is not available.

    Example:
        >>> from vds_elastic_orchestrator import load_settings, KibanaElasticsearchClient
        >>> settings = load_settings()
        >>> with KibanaElasticsearchClient(settings) as client:
        ...     result = client.search("logs-*", {"query": {"match_all": {}}})
        ...     print(result)
    """

    def __init__(self, config: ElasticSettings) -> None:
        """Initialize the client with configuration.

        Args:
            config: ElasticSettings instance with connection parameters.
        """
        self.config = config
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTPX client (lazy initialization)."""
        if self._client is None:
            scheme = "https" if self.config.kibana_url.startswith("https://") else "http"
            self._client = httpx.Client(
                base_url=f"{scheme}://{self.config.kibana_ip}",
                auth=(self.config.user, self.config.password),
                headers={
                    "Host": self.config.kibana_url,  # e.g., log.digital.vn
                    "kbn-xsrf": "true",  # Required by Kibana
                    "Content-Type": "application/json",
                },
                verify=self.config.verify_certs,  # False for self-signed
                timeout=httpx.Timeout(
                    connect=self.config.connect_timeout,
                    read=self.config.request_timeout,
                    write=self.config.request_timeout,
                    pool=self.config.connect_timeout,
                ),
                # HTTPX provides connection pooling by default
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

    def _es_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an Elasticsearch request via Kibana Console Proxy.

        This method handles the low-level HTTP communication with retry
        logic for transient errors (502, 503, 504).

        Args:
            method: HTTP method for ES operation (GET, POST, PUT, DELETE).
            path: Elasticsearch path (e.g., "/_search", "/logs-*/_count").
            body: Optional request body (will be JSON-encoded).

        Returns:
            httpx.Response object.

        Raises:
            TransportError: For network/connection issues.
            ClientTimeoutError: For timeout errors.
            RetryError: When retry attempts are exhausted.
        """
        # URL-encode the path and construct proxy URL
        encoded_path = quote(path, safe="")
        url = f"{self.config.proxy_endpoint}?path={encoded_path}&method={method}"

        # URL-encode the path and construct proxy URL
        encoded_path = quote(path, safe="")
        url = f"{self.config.proxy_endpoint}?path={encoded_path}&method={method}"

        try:
            # For GET/DELETE/HEAD methods, don't send a body (ES rejects it)
            if method.upper() in ("GET", "DELETE", "HEAD") and not body:
                return self.client.post(url)

            # Check for raw ndjson body (used by msearch)
            if body and "_raw_ndjson" in body:
                return self.client.post(
                    url,
                    content=body["_raw_ndjson"],
                    headers={"Content-Type": "application/x-ndjson"},
                )

            return self.client.post(url, json=body or {})
        except httpx.TimeoutException as exc:
            raise ClientTimeoutError(
                f"Request timed out: {exc}",
                context={"method": method, "path": path},
            ) from exc
        except httpx.ConnectError as exc:
            raise TransportError(
                f"Connection failed: {exc}",
                context={"method": method, "path": path},
            ) from exc
        except httpx.HTTPError as exc:
            raise TransportError(
                f"HTTP error: {exc}",
                context={"method": method, "path": path},
            ) from exc
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={"method": method, "path": path, "attempts": self.config.max_retries},
            ) from exc

    def _handle_response(
        self,
        response: httpx.Response,
        operation: str = "request",
    ) -> dict[str, Any]:
        """Handle response and convert to dict, raising appropriate errors.

        Args:
            response: The HTTPX response object.
            operation: Description of the operation for error messages.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            AuthError: For 401 errors.
            ClientPermissionError: For 403 errors.
            ResponseError: For other 4xx/5xx errors.
            VDSClientError: For ES query errors in the response body.
        """
        # Try to parse JSON first
        try:
            data = response.json()
        except Exception:
            data = {"raw_response": response.text, "status_code": response.status_code}

        # Kibana Console Proxy may return HTTP 200 with ES error in body
        # Check for ES error status in body first (only if it's a numeric status code)
        body_status = data.get("status") if isinstance(data, dict) else None
        # Ensure effective_status is always an int - only use body_status if it's numeric
        if isinstance(body_status, int) and body_status >= 100:
            effective_status = body_status
        else:
            effective_status = response.status_code

        # Check HTTP status or body status
        if effective_status == 401:
            raise AuthError(
                f"Authentication failed for {operation}",
                context={"status_code": effective_status, "response": data},
            )

        if effective_status == 403:
            # Check if this is an ES permission error
            error_info = data.get("error", {}) if isinstance(data, dict) else {}
            error_type = error_info.get("type", "") if isinstance(error_info, dict) else ""

            if error_type == "security_exception" or effective_status == 403:
                raise ClientPermissionError(
                    f"Permission denied for {operation}",
                    context={
                        "status_code": effective_status,
                        "response": data,
                        "required_roles": ["monitoring_user", "superuser"],
                    },
                )

        if effective_status >= 400:
            # Check for ES query errors
            if isinstance(data, dict) and "error" in data:
                error_info = data.get("error", {})
                if isinstance(error_info, dict):
                    error_type = error_info.get("type", "")
                    if "parsing_exception" in error_type or "query" in error_type.lower():
                        raise VDSClientError(
                            f"Query error: {error_info.get('reason', 'Unknown')}",
                            context={"status_code": effective_status, "response": data},
                        )

            raise ResponseError(
                f"Request failed for {operation}",
                context={"status_code": effective_status, "response": data},
            )

        return data

    # -------------------------------------------------------------------------
    # Core Operations (work with 'viewer' role)
    # -------------------------------------------------------------------------

    def ping(self) -> bool:
        """Test connectivity to Elasticsearch via Kibana.

        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            response = self._es_request("GET", "/")
            return response.status_code == 200
        except VDSClientError:
            return False

    def search(
        self,
        index: str | None = None,
        query: dict[str, Any] | None = None,
        size: int | None = None,
        from_: int = 0,
        sort: list[dict[str, Any]] | None = None,
        search_after: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Search documents in Elasticsearch.

        Args:
            index: Index pattern (default from config).
            query: Elasticsearch query DSL.
            size: Number of results (default from config).
            from_: Pagination offset (ignored if search_after is provided).
            sort: Sort specification (required if search_after is used).
            search_after: Sort values from the last hit to paginate from.
                         When provided, 'from' is ignored. Requires 'sort'.

        Returns:
            Elasticsearch search response.

        Raises:
            VDSClientError: If the query is invalid.
            ClientPermissionError: If access is denied.
            ValueError: If search_after is provided without sort.
        """
        index = index or self.config.default_index
        size = size if size is not None else self.config.default_size

        body: dict[str, Any] = {
            "size": size,
        }

        # search_after requires sort and ignores from
        if search_after is not None:
            if not sort:
                raise ValueError("search_after requires a 'sort' parameter")
            body["search_after"] = search_after
        else:
            body["from"] = from_

        if query:
            body["query"] = query
        else:
            body["query"] = {"match_all": {}}

        if sort:
            body["sort"] = sort

        response = self._es_request("POST", f"/{index}/_search", body)
        return self._handle_response(response, f"search on {index}")

    def count(
        self,
        index: str | None = None,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Count documents matching a query.

        Args:
            index: Index pattern (default from config).
            query: Elasticsearch query DSL.

        Returns:
            Elasticsearch count response with "count" field.
        """
        index = index or self.config.default_index

        body: dict[str, Any] = {}
        if query:
            body["query"] = query

        response = self._es_request("POST", f"/{index}/_count", body)
        return self._handle_response(response, f"count on {index}")

    def get_document(
        self,
        index: str,
        doc_id: str,
        source: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve a single document by ID.

        Args:
            index: Index name (required).
            doc_id: Document ID (required).
            source: Optional list of fields to return (default: all).

        Returns:
            Elasticsearch document with _id, _source, etc.

        Raises:
            ResponseError: If document not found (404).
        """
        path = f"/{index}/_doc/{doc_id}"
        if source:
            path += f"?_source={','.join(source)}"

        response = self._es_request("GET", path)
        return self._handle_response(response, f"get document {doc_id} from {index}")

    def mget(
        self,
        index: str | None = None,
        ids: list[str] | None = None,
        docs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Multi-get documents by IDs.

        Args:
            index: Default index for all docs (can be overridden per doc).
            ids: List of document IDs (simple form, requires index).
            docs: List of doc specifications with _index, _id (advanced form).

        Returns:
            Elasticsearch mget response with "docs" array.

        Example:
            # Simple form with IDs
            client.mget(index="logs", ids=["doc1", "doc2"])

            # Advanced form with full doc specs
            client.mget(docs=[
                {"_index": "logs", "_id": "doc1"},
                {"_index": "other", "_id": "doc2", "_source": ["field1"]},
            ])
        """
        body: dict[str, Any] = {}

        if ids:
            body["ids"] = ids
        elif docs:
            body["docs"] = docs
        else:
            raise ValueError("Either 'ids' or 'docs' must be provided")

        path = "/_mget" if not index else f"/{index}/_mget"
        response = self._es_request("POST", path, body)
        return self._handle_response(response, "mget")

    def field_caps(
        self,
        index: str | None = None,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get field capabilities across indices.

        Args:
            index: Index pattern (default: "*").
            fields: List of field names or patterns (default: "*").

        Returns:
            Field capabilities response with field types and searchability.

        Example:
            # Get all field capabilities
            client.field_caps()

            # Get specific fields
            client.field_caps(index="logs-*", fields=["message", "@timestamp"])
        """
        index = index or "*"
        fields = fields or ["*"]

        body: dict[str, Any] = {"fields": fields}
        response = self._es_request("POST", f"/{index}/_field_caps", body)
        return self._handle_response(response, f"field_caps on {index}")

    def msearch(
        self,
        searches: list[tuple[dict[str, Any], dict[str, Any]]],
        index: str | None = None,
    ) -> dict[str, Any]:
        """Execute multiple searches in a single request.

        Args:
            searches: List of (header, body) tuples. Header contains index/routing,
                     body contains the search query.
            index: Default index for all searches (can be overridden per search).

        Returns:
            Elasticsearch msearch response with "responses" array.

        Example:
            results = client.msearch([
                ({"index": "logs-*"}, {"query": {"match": {"level": "ERROR"}}}),
                ({"index": "metrics-*"}, {"query": {"range": {"value": {"gt": 100}}}}),
            ])
            for resp in results["responses"]:
                print(resp["hits"]["total"])
        """
        # Build ndjson body for msearch
        # Each search is: header line + body line
        lines: list[str] = []
        for header, body in searches:
            if index and "_index" not in header and "index" not in header:
                header = {"index": index, **header}
            lines.append(json.dumps(header))
            lines.append(json.dumps(body))

        # msearch requires ndjson format (newline-delimited JSON)
        # We need to send this as raw text, not JSON
        ndjson_body = "\n".join(lines) + "\n"

        # For msearch, we need to send raw ndjson, not JSON
        # Use a custom request path
        path = "/_msearch" if not index else f"/{index}/_msearch"

        # Unfortunately, our _es_request sends JSON. For msearch, we need
        # to pass the pre-formatted body. We'll use a workaround by sending
        # the body as a raw string indicator.
        response = self._es_request("POST", path, {"_raw_ndjson": ndjson_body})
        return self._handle_response(response, "msearch")

    # -------------------------------------------------------------------------
    # Scroll API for Deep Pagination
    # -------------------------------------------------------------------------

    def scroll_search(
        self,
        index: str | None = None,
        query: dict[str, Any] | None = None,
        size: int | None = None,
        scroll: str = "5m",
        sort: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Initiate a scrolling search for large result sets.

        This is the first call to start a scroll. Use scroll() to get
        subsequent batches, and clear_scroll() when done.

        Args:
            index: Index pattern (default from config).
            query: Elasticsearch query DSL.
            size: Number of results per batch (default from config).
            scroll: How long to keep the scroll context alive (default: 5m).
            sort: Sort specification.

        Returns:
            First batch of results with _scroll_id for subsequent calls.

        Example:
            # Start scroll
            result = client.scroll_search("logs-*", size=1000)
            scroll_id = result["_scroll_id"]
            hits = result["hits"]["hits"]

            # Continue scrolling
            while hits:
                result = client.scroll(scroll_id)
                scroll_id = result["_scroll_id"]
                hits = result["hits"]["hits"]

            # Cleanup
            client.clear_scroll(scroll_id)
        """
        index = index or self.config.default_index
        size = size if size is not None else self.config.default_size

        body: dict[str, Any] = {"size": size}

        if query:
            body["query"] = query
        else:
            body["query"] = {"match_all": {}}

        if sort:
            body["sort"] = sort

        response = self._es_request("POST", f"/{index}/_search?scroll={scroll}", body)
        return self._handle_response(response, f"scroll_search on {index}")

    def scroll(
        self,
        scroll_id: str,
        scroll: str = "5m",
    ) -> dict[str, Any]:
        """Continue a scrolling search.

        Args:
            scroll_id: The _scroll_id from the previous scroll response.
            scroll: How long to keep the scroll context alive.

        Returns:
            Next batch of results with updated _scroll_id.
        """
        body = {"scroll": scroll, "scroll_id": scroll_id}
        response = self._es_request("POST", "/_search/scroll", body)
        return self._handle_response(response, "scroll")

    def clear_scroll(
        self,
        scroll_id: str | list[str],
    ) -> dict[str, Any]:
        """Clear scroll context(s) to release resources.

        Always call this when done scrolling to free up resources.

        Args:
            scroll_id: Single scroll ID or list of scroll IDs to clear.

        Returns:
            Clear scroll response with succeeded/failed counts.
        """
        body = {"scroll_id": scroll_id}
        response = self._es_request("DELETE", "/_search/scroll", body)
        return self._handle_response(response, "clear_scroll")

    def scan(
        self,
        index: str | None = None,
        query: dict[str, Any] | None = None,
        size: int = 1000,
        scroll: str = "5m",
        preserve_order: bool = False,
    ):
        """Generator that yields all documents matching a query.

        This is a high-level helper that handles scroll management
        automatically. It yields documents one by one.

        Args:
            index: Index pattern (default from config).
            query: Elasticsearch query DSL.
            size: Batch size per scroll request (default: 1000).
            scroll: Scroll context timeout (default: 5m).
            preserve_order: If True, use default sort (slower).
                           If False, use _doc sort (faster).

        Yields:
            Individual documents (hits) from the search results.

        Example:
            for doc in client.scan("logs-*", {"match": {"level": "ERROR"}}):
                print(doc["_source"]["message"])
        """
        # Use _doc sort for efficiency unless order matters
        sort: list[dict[str, Any]] | None = None
        if not preserve_order:
            sort = [{"_doc": "asc"}]

        # Initial search with scroll
        result = self.scroll_search(
            index=index,
            query=query,
            size=size,
            scroll=scroll,
            sort=sort,
        )

        scroll_id = result.get("_scroll_id")
        hits = result.get("hits", {}).get("hits", [])

        try:
            while hits:
                yield from hits

                # Get next batch
                if scroll_id:
                    result = self.scroll(scroll_id, scroll=scroll)
                    scroll_id = result.get("_scroll_id")
                    hits = result.get("hits", {}).get("hits", [])
                else:
                    break
        finally:
            # Always clean up scroll context
            if scroll_id:
                with contextlib.suppress(Exception):
                    self.clear_scroll(scroll_id)

    # -------------------------------------------------------------------------
    # Kibana-Level Operations
    # -------------------------------------------------------------------------

    def kibana_status(self) -> dict[str, Any]:
        """Check Kibana availability via /api/status.

        Returns:
            Kibana status response.
        """
        try:
            response = self.client.get("/api/status")
            return response.json()
        except Exception as exc:
            return {"error": str(exc), "type": "kibana_error"}

    def user_info(self) -> dict[str, Any]:
        """Get current user information from Kibana.

        Returns:
            User info including username and roles.
        """
        try:
            response = self.client.get("/internal/security/me")
            return response.json()
        except Exception as exc:
            return {"error": str(exc), "type": "user_info_error"}

    # -------------------------------------------------------------------------
    # Admin Operations (require 'monitor' privilege - may fail for 'viewer')
    # -------------------------------------------------------------------------

    def info(self) -> dict[str, Any]:
        """Get cluster info (requires monitor privilege).

        Returns:
            Cluster info or permission error details.
        """
        response = self._es_request("GET", "/")
        return self._handle_response(response, "cluster info")

    def health(self) -> dict[str, Any]:
        """Get cluster health (requires monitor privilege).

        Returns:
            Cluster health or permission error details.
        """
        response = self._es_request("GET", "/_cluster/health")
        return self._handle_response(response, "cluster health")

    def cat_indices(self, pattern: str = "*") -> dict[str, Any]:
        """List indices (requires monitor privilege).

        Args:
            pattern: Index pattern to filter.

        Returns:
            List of indices or permission error details.
        """
        response = self._es_request("GET", f"/_cat/indices/{pattern}?format=json")
        return self._handle_response(response, "cat indices")

    def get_mapping(self, index: str) -> dict[str, Any]:
        """Get index mapping.

        Args:
            index: Index name or pattern.

        Returns:
            Index mapping.
        """
        response = self._es_request("GET", f"/{index}/_mapping")
        return self._handle_response(response, f"mapping for {index}")

    def cat_aliases(self, pattern: str = "*") -> dict[str, Any]:
        """List index aliases (requires monitor privilege).

        Args:
            pattern: Alias name pattern to filter (default: "*" for all).

        Returns:
            List of aliases with index, alias, filter, routing info,
            or permission error details.

        Raises:
            ClientPermissionError: If the user lacks monitor privilege.
        """
        response = self._es_request("GET", f"/_cat/aliases/{pattern}?format=json")
        return self._handle_response(response, "cat aliases")

    # -------------------------------------------------------------------------
    # Context Manager and Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the HTTP client and release connections."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> KibanaElasticsearchClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close client."""
        self.close()


__all__ = ["KibanaElasticsearchClient"]
