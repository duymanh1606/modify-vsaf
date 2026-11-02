"""Batch polling and webhook management utilities for Confluence Server/DC."""

from __future__ import annotations

import builtins
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .http import ConfluenceClient


@dataclass(slots=True)
class BatchMetrics:
    """Execution metrics captured during a batch scan."""

    scanned: int = 0
    pages_processed: int = 0
    requests: int = 0
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def mark_request(self) -> None:
        self.requests += 1

    def mark_processed(self, count: int) -> None:
        self.pages_processed += count

    def mark_finished(self) -> None:
        self.finished_at = time.time()

    @property
    def duration_seconds(self) -> float | None:
        if self.finished_at is None:
            return None
        return round(self.finished_at - self.started_at, 3)


class BatchRunner:
    """Polling utilities for change detection using REST v1 CQL queries."""

    def __init__(
        self,
        http_client: ConfluenceClient,
        *,
        expand: Sequence[str] | None = None,
    ) -> None:
        self._http = http_client
        self._expand = expand
        self._last_metrics: BatchMetrics | None = None

    def scan(
        self,
        cql: str,
        *,
        limit: int = 25,
        max_results: int | None = None,
        start: int = 0,
        expand: Sequence[str] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield individual content results for the given CQL query."""

        metrics = BatchMetrics()
        self._last_metrics = metrics
        applied_expand = expand if expand is not None else self._expand
        fetched = 0
        current_start = start

        while True:
            remaining = None if max_results is None else max_results - fetched
            page_limit = limit if remaining is None else min(limit, remaining)
            params = {
                "cql": cql,
                "limit": page_limit,
                "start": current_start,
            }
            if applied_expand:
                params["expand"] = ",".join(applied_expand)

            metrics.mark_request()
            # Use SDK's cql method instead of raw request
            payload = self._http.search_cql(cql, limit=page_limit, expand=applied_expand, start=current_start)
            results = payload.get("results", [])
            count = len(results)
            if not results:
                break
            metrics.mark_processed(count)
            metrics.scanned += count
            for item in results:
                fetched += 1
                yield item

            current_start = payload.get("start", current_start) + count
            if max_results is not None and fetched >= max_results:
                break

        metrics.mark_finished()
        self._last_metrics = metrics

    def snapshot(
        self,
        cql: str,
        *,
        limit: int = 25,
        max_results: int | None = None,
        expand: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Return an aggregated snapshot for reporting pipelines."""

        results: list[dict[str, Any]] = []
        for item in self.scan(cql, limit=limit, max_results=max_results, expand=expand):
            results.append(item)
        return {
            "cql": cql,
            "limit": limit,
            "maxResults": max_results,
            "count": len(results),
            "results": results,
        }

    @property
    def last_metrics(self) -> BatchMetrics | None:
        return self._last_metrics


class WebhookClient:
    """Manage Confluence Server/DC webhooks via REST v1."""

    _BASE_PATH = "/rest/webhooks/1.0/webhook"

    def __init__(self, http_client: ConfluenceClient) -> None:
        self._http = http_client

    def create(
        self,
        *,
        name: str,
        url: str,
        events: Iterable[str],
        active: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "name": name,
            "url": url,
            "events": list(events),
            "excludeBody": False,
            "active": active,
        }
        if filters:
            payload["filters"] = filters
        response = self._http.request("POST", self._BASE_PATH, json=payload)
        return response.json()

    def list(self) -> builtins.list[dict[str, Any]]:
        response = self._http.request("GET", self._BASE_PATH)
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("results", [])

    def delete(self, webhook_id: str) -> None:
        self._http.request("DELETE", f"{self._BASE_PATH}/{webhook_id}")


__all__ = ["BatchMetrics", "BatchRunner", "WebhookClient"]
