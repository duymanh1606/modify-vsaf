from __future__ import annotations

from typing import Any

from confluence_orchestrator.orchestration import BatchRunner, WebhookClient


class FakeClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls = 0

    def search_cql(self, *_, **kwargs) -> dict[str, Any]:
        limit = kwargs.get("limit")
        if self.calls < len(self.responses):
            payload = dict(self.responses[self.calls])
            if limit is not None:
                payload["results"] = payload["results"][:limit]
        else:
            payload = {"results": [], "start": 0, "limit": 0}
        self.calls += 1
        return payload

    def request(self, method: str, path: str, **kwargs: Any):
        return FakeResponse({"method": method, "path": path, **kwargs})


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


def test_batch_runner_scan_returns_results() -> None:
    client = FakeClient(
        [
            {
                "results": [
                    {"id": "10"},
                    {"id": "11"},
                ],
                "start": 0,
                "limit": 2,
            }
        ]
    )

    runner = BatchRunner(client)  # type: ignore[arg-type]
    results = list(runner.scan("type=page", limit=2))

    assert len(results) == 2
    assert runner.last_metrics is not None
    assert runner.last_metrics.pages_processed == 2


def test_batch_runner_snapshot() -> None:
    client = FakeClient(
        [
            {
                "results": [{"id": "10"}],
                "start": 0,
                "limit": 1,
            }
        ]
    )

    runner = BatchRunner(client)  # type: ignore[arg-type]
    payload = runner.snapshot("type=page", limit=1)

    assert payload["count"] == 1
    assert payload["results"][0]["id"] == "10"


def test_webhook_client_creates_lists_and_deletes() -> None:
    events: list[dict[str, Any]] = []

    class RecordingHttp:
        def request(self, method: str, path: str, **kwargs: Any):
            events.append({"method": method, "path": path, **kwargs})
            if method == "GET":
                return FakeResponse([{"id": "1"}])
            return FakeResponse({"id": "1"})

    client = WebhookClient(RecordingHttp())  # type: ignore[arg-type]
    client.create(name="Notify", url="https://example", events=["page_created"])
    client.list()
    client.delete("1")

    assert events[0]["method"] == "POST"
    assert events[1]["method"] == "GET"
    assert events[2]["path"].endswith("/1")
