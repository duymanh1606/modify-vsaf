from __future__ import annotations

import pytest
from confluence_orchestrator.content import ContentClient


class DummyHttp:
    def create_page(self, *args, **kwargs):
        return {"args": args, "kwargs": kwargs}

    def update_page(self, *args, **kwargs):
        return {"args": args, "kwargs": kwargs}


@pytest.fixture()
def content_client() -> ContentClient:
    return ContentClient(DummyHttp())


def test_notify_watchers_rejected_on_create(content_client: ContentClient) -> None:
    with pytest.raises(ValueError):
        content_client.create_page(space_key="TTTC", title="A", body="B", notify_watchers=True)


def test_notify_watchers_rejected_on_update(content_client: ContentClient) -> None:
    with pytest.raises(ValueError):
        content_client.update_page("123", title="A", notify_watchers=True)
