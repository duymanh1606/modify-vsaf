from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from confluence_orchestrator.content import ContentClient


class RecordingClient:
    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}

    def get_page(self, page_id: str, expand: Any = None) -> dict[str, Any]:
        return {
            "id": page_id,
            "title": "Original",
            "space": {"key": "TTTC"},
            "version": {"number": 2},
            "body": {"storage": {"value": "<p>old</p>", "representation": "storage"}},
        }

    def create_page(
        self, space_key: str, title: str, body: str, parent_id: Any = None, **kwargs: Any
    ) -> dict[str, Any]:
        payload = {"space_key": space_key, "title": title, "body": body, "parent_id": parent_id, **kwargs}
        self.calls["create_page"] = payload
        return {"id": "999", **payload}

    def update_page(self, page_id: str, title: str, body: Any = None, **kwargs: Any) -> dict[str, Any]:
        payload = {"page_id": page_id, "title": title, "body": body, **kwargs}
        self.calls["update_page"] = payload
        return payload

    def delete_page(self, page_id: str) -> None:
        self.calls["delete_page"] = {"page_id": page_id}

    # Attachment operations -------------------------------------------------
    def add_attachment(self, page_id: str, filename: str, content: bytes, **kwargs: Any) -> dict[str, Any]:
        self.calls["add_attachment"] = {
            "page_id": page_id,
            "filename": filename,
            "size": len(content),
            **kwargs,
        }
        return {"id": "att-1"}

    def update_attachment_data(
        self, page_id: str, attachment_id: str, filename: str, content: bytes, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls["update_attachment"] = {
            "page_id": page_id,
            "attachment_id": attachment_id,
            "filename": filename,
            "size": len(content),
            **kwargs,
        }
        return {"id": attachment_id}

    def delete_attachment_by_id(self, page_id: str, attachment_id: str, version: Any = None) -> None:
        self.calls["delete_attachment_by_id"] = {"page_id": page_id, "attachment_id": attachment_id, "version": version}

    def delete_attachment(self, page_id: str, filename: str, version: Any = None) -> None:
        self.calls["delete_attachment"] = {"page_id": page_id, "filename": filename, "version": version}

    def get_attachments(self, page_id: str) -> dict[str, Any]:
        return {"results": [{"id": "att-1", "title": "doc.txt"}]}

    def get_attachment_content(self, attachment_id: str) -> bytes:
        return b"file"

    # Template operations ---------------------------------------------------
    def request(self, method: str, path: str, **kwargs: Any):
        self.calls.setdefault("requests", []).append({"method": method, "path": path, **kwargs})

        class _Resp:
            def __init__(self, payload: dict[str, Any]) -> None:
                self._payload = payload

            def json(self) -> dict[str, Any]:
                return self._payload

        if method == "GET" and path.startswith("/rest/api/template/"):
            return _Resp(
                {
                    "id": path.rsplit("/", 1)[-1],
                    "name": "Template",
                    "templateType": "page",
                    "description": "desc",
                    "body": {"storage": {"value": "<p>template</p>", "representation": "storage"}},
                }
            )
        if method == "GET":
            return _Resp({"results": [{"id": "tmpl-1"}]})
        return _Resp({"id": "tmpl-1", **kwargs.get("json", {})})


@pytest.fixture()
def content_client() -> tuple[ContentClient, RecordingClient]:
    recording = RecordingClient()
    return ContentClient(recording), recording


def test_create_page_passes_sdk_fields(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.create_page(
        space_key="TTTC", title="New Page", body="<p>hello</p>", parent_id="321", representation="storage"
    )

    payload = recording.calls["create_page"]
    assert payload["space_key"] == "TTTC"
    assert payload["title"] == "New Page"
    assert payload["body"] == "<p>hello</p>"
    assert payload["parent_id"] == "321"


def test_update_page_uses_existing_title(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.update_page("123", body="<p>updated</p>", minor_edit=True, message="Updated")

    payload = recording.calls["update_page"]
    assert payload["page_id"] == "123"
    assert payload["body"] == "<p>updated</p>"
    assert payload["minor_edit"] is True
    assert payload["version_comment"] == "Updated"


def test_delete_page(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.delete_page("123")
    assert recording.calls["delete_page"] == {"page_id": "123"}


def test_upload_attachment_records_args(tmp_path: Path, content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    file_path = tmp_path / "attachment.txt"
    file_path.write_text("data", encoding="utf-8")

    client.upload_attachment("123", str(file_path), content_type="text/plain", comment="note")

    payload = recording.calls["add_attachment"]
    assert payload["page_id"] == "123"
    assert payload["filename"].endswith("attachment.txt")
    assert payload["comment"] == "note"


def test_list_attachments_returns_dict(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, _ = content_client
    payload = client.list_attachments("123")
    assert "results" in payload
    assert payload["results"][0]["title"] == "doc.txt"


def test_update_attachment(content_client: tuple[ContentClient, RecordingClient], tmp_path: Path) -> None:
    client, recording = content_client
    file_path = tmp_path / "attachment.txt"
    file_path.write_text("new", encoding="utf-8")

    client.update_attachment("123", "att-1", str(file_path), comment="reupload")
    payload = recording.calls["update_attachment"]
    assert payload["attachment_id"] == "att-1"
    assert payload["comment"] == "reupload"


def test_delete_attachment(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.delete_attachment("123", "att-1", version=2)
    assert recording.calls["delete_attachment_by_id"] == {"page_id": "123", "attachment_id": "att-1", "version": 2}


def test_delete_attachment_by_filename(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.delete_attachment("123", filename="diagram.pdf")
    assert recording.calls["delete_attachment"] == {"page_id": "123", "filename": "diagram.pdf", "version": None}


def test_delete_attachment_requires_identifier(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, _ = content_client
    with pytest.raises(ValueError):
        client.delete_attachment("123")


def test_template_operations(content_client: tuple[ContentClient, RecordingClient]) -> None:
    client, recording = content_client
    client.create_template(name="My Template", body="<p>body</p>", space_key="TTTC")
    client.update_template("tmpl-1", name="Renamed")
    client.delete_template("tmpl-1")

    assert recording.calls["requests"][0]["method"] == "POST"
    assert recording.calls["requests"][1]["method"] == "GET"
    assert recording.calls["requests"][2]["method"] == "PUT"
    assert recording.calls["requests"][3]["path"].endswith("tmpl-1")
