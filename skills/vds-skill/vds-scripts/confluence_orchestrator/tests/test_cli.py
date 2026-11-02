from __future__ import annotations

import builtins
import json
from pathlib import Path
from typing import Any

import pytest
from confluence_orchestrator.cli import _build_content_client, app
from confluence_orchestrator.config import ConfluenceSettings
from confluence_orchestrator.errors import VDSClientError
from typer.testing import CliRunner

from confluence_orchestrator import config as config_module

runner = CliRunner()


@pytest.fixture(autouse=True)
def restore_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load_settings(strict: bool = False) -> ConfluenceSettings:
        return ConfluenceSettings.model_validate(
            {
                "VDS_USERNAME": "user",
                "VDS_PASSWORD": "pass",
                "INTERNAL_CONFLUENCE_TOKEN": "token-int",
                "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
            }
        )

    monkeypatch.setattr(config_module, "load_settings", fake_load_settings)
    monkeypatch.setattr("confluence_orchestrator.cli.load_settings", fake_load_settings)


def test_templates_command_lists_blueprints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def list_templates(self, space_key: str | None = None) -> dict[str, Any]:
            assert space_key is None
            return {"blueprints": [{"name": "Doc", "templateId": "123"}]}

    monkeypatch.setattr(
        "confluence_orchestrator.cli._build_content_client",
        lambda settings, server, api_version: DummyClient(),
    )
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app, ["--report-dir", str(tmp_path), "--api-version", "v2", "templates", "--server", "external"]
    )

    assert result.exit_code == 0
    assert "Doc" in result.stdout
    assert "ID: 123" in result.stdout


def test_missing_token_triggers_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_load(strict: bool = False) -> ConfluenceSettings:
        return ConfluenceSettings.model_validate(
            {
                "VDS_USERNAME": "user",
                "VDS_PASSWORD": "pass",
                "INTERNAL_CONFLUENCE_TOKEN": None,
                "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
            }
        )

    monkeypatch.setattr("confluence_orchestrator.cli.load_settings", fake_load)

    def fake_builder(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise VDSClientError("Missing token")

    monkeypatch.setattr("confluence_orchestrator.cli._build_content_client", lambda *args, **kwargs: fake_builder())

    result = runner.invoke(app, ["--report-dir", str(tmp_path), "templates", "--server", "internal"])
    assert result.exit_code == 1
    assert "Missing token" in result.stderr or "Missing token" in result.output


def test_get_command_fetches_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def get_content(
            self, page_id: str, expand: list[str] | None = None, format: str | None = None
        ) -> dict[str, Any]:
            assert page_id == "99647801"
            assert expand == ["body.storage"]
            assert format == "storage"
            return {"id": page_id, "title": "Sample"}

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClientV2", DummyClient)
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "get",
            "99647801",
            "--server",
            "external",
            "--expand",
            "body.storage",
            "--format",
            "storage",
        ],
    )

    assert result.exit_code == 0
    assert "Sample" in result.stdout


def test_content_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:  # type: ignore[override]
            assert page_id == "996"
            assert expand == ["body.storage", "version"]
            return {"id": page_id}

    monkeypatch.setattr(
        "confluence_orchestrator.cli._build_content_client", lambda settings, server, api_version: DummyClient()
    )
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "page",
            "996",
            "--server",
            "internal",
            "--expand",
            "body.storage,version",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["id"] == "996"
    assert list(tmp_path.rglob("*.json"))


def test_content_child_pages_with_expand(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def get_child_pages(self, page_id: str, expand: list[str] | None = None) -> list[dict[str, Any]]:  # type: ignore[override]
            assert page_id == "996"
            assert expand == ["body.storage"]
            return [{"id": "997", "title": "Child"}]

    monkeypatch.setattr(
        "confluence_orchestrator.cli._build_content_client", lambda settings, server, api_version: DummyClient()
    )
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "child-pages",
            "996",
            "--server",
            "internal",
            "--expand",
            "body.storage",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["id"] == "997"


def test_content_search(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def search_cql(self, cql: str, limit: int, start: int, expand: list[str] | None = None) -> dict[str, Any]:  # type: ignore[override]
            assert cql == "title ~ 'foo'"
            assert limit == 10
            assert start == 5
            assert expand is None
            return {"results": ["ok"]}

    monkeypatch.setattr(
        "confluence_orchestrator.cli._build_content_client", lambda settings, server, api_version: DummyClient()
    )
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        ["--report-dir", str(tmp_path), "content", "search", "title ~ 'foo'", "--limit", "10", "--start", "5"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["results"] == ["ok"]


def test_content_templates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def list_templates(self, space_key: str | None = None) -> dict[str, Any]:  # type: ignore[override]
            assert space_key == "TTTC"
            return {"templates": [1, 2]}

    monkeypatch.setattr(
        "confluence_orchestrator.cli._build_content_client", lambda settings, server, api_version: DummyClient()
    )
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        ["--report-dir", str(tmp_path), "content", "templates", "--space", "TTTC"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["templates"] == [1, 2]


def test_build_content_client_blocks_v2_when_not_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyHttp:
        def supports_api_version(self, version: str) -> bool:
            return version == "v1"

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: DummyHttp())

    settings = ConfluenceSettings.model_validate(
        {
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
            "INTERNAL_CONFLUENCE_TOKEN": "token-int",
            "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
        }
    )

    with pytest.raises(VDSClientError) as excinfo:
        _build_content_client(settings, "internal", "v2")
    assert "not supported" in str(excinfo.value)


def test_build_content_client_allows_v2_when_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyHttp:
        def supports_api_version(self, version: str) -> bool:
            return True

    class DummyClient:
        pass

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: DummyHttp())
    monkeypatch.setattr("confluence_orchestrator.cli.ContentClientV2", lambda http_client: DummyClient())

    settings = ConfluenceSettings.model_validate(
        {
            "VDS_USERNAME": "user",
            "VDS_PASSWORD": "pass",
            "INTERNAL_CONFLUENCE_TOKEN": "token-int",
            "EXTERNAL_CONFLUENCE_TOKEN": "token-ext",
        }
    )

    client = _build_content_client(settings, "external", "v2")
    assert isinstance(client, DummyClient)


def test_content_create_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>body</p>", encoding="utf-8")

    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def create_page(self, **kwargs: Any) -> dict[str, Any]:
            captured["args"] = kwargs
            return {"id": "456"}

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: DummyClient())
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "create-page",
            "--space",
            "TTTC",
            "--title",
            "My Page",
            "--body-file",
            str(body_file),
        ],
    )

    assert result.exit_code == 0
    assert captured["args"]["space_key"] == "TTTC"
    assert captured["args"]["title"] == "My Page"
    assert captured["args"]["body"] == "<p>body</p>"


def test_content_update_page_requires_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())
    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: object())

    result = runner.invoke(
        app,
        ["--report-dir", str(tmp_path), "content", "update-page", "123"],
    )

    assert result.exit_code != 0
    assert "Provide at least one" in result.stderr or "Provide at least one" in result.output


def test_content_update_page_calls_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body_file = tmp_path / "body.html"
    body_file.write_text("<p>body</p>", encoding="utf-8")

    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def update_page(self, page_id: str, **kwargs: Any) -> dict[str, Any]:
            captured["page_id"] = page_id
            captured["kwargs"] = kwargs
            return {"id": page_id, **kwargs}

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: DummyClient())
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "update-page",
            "123",
            "--body-file",
            str(body_file),
            "--minor-edit",
        ],
    )

    assert result.exit_code == 0
    assert captured["page_id"] == "123"
    assert captured["kwargs"]["body"] == "<p>body</p>"
    assert captured["kwargs"]["minor_edit"] is True


def test_content_add_attachment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    attachment = tmp_path / "file.txt"
    attachment.write_text("content", encoding="utf-8")

    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def upload_attachment(self, page_id: str, file: str, **kwargs: Any) -> dict[str, Any]:
            captured["page_id"] = page_id
            captured["file"] = file
            captured["kwargs"] = kwargs
            return {"id": "att-1"}

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: DummyClient())
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "add-attachment",
            "123",
            "--file",
            str(attachment),
            "--comment",
            "upload",
            "--content-type",
            "text/plain",
        ],
    )

    assert result.exit_code == 0
    assert captured["page_id"] == "123"
    assert captured["file"].endswith("file.txt")
    assert captured["kwargs"]["comment"] == "upload"


def test_content_download_attachment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def download_attachment(self, attachment_id: str, output_path: Path, **kwargs: Any) -> Path:
            captured["attachment_id"] = attachment_id
            captured["output_path"] = output_path
            captured["kwargs"] = kwargs
            output_path.mkdir(parents=True, exist_ok=True)
            if output_path.suffix:
                out = output_path
            elif kwargs.get("filename"):
                out = output_path / kwargs["filename"]
            else:
                out = output_path / "attachment.bin"
            out.write_bytes(b"content")
            return out

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: DummyClient())
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    output_dir = tmp_path / "downloads"
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "download-attachment",
            "att-123",
            "--out",
            str(output_dir),
            "--filename",
            "download.txt",
        ],
    )

    assert result.exit_code == 0
    assert captured["attachment_id"] == "att-123"
    assert str(captured["output_path"]).endswith("downloads")
    assert captured["kwargs"]["filename"] == "download.txt"
    assert (output_dir / "download.txt").exists()


def test_content_update_template(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    body_file = tmp_path / "template.html"
    body_file.write_text("<p>template</p>", encoding="utf-8")

    captured: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def update_template(self, template_id: str, **kwargs: Any) -> dict[str, Any]:
            captured["template_id"] = template_id
            captured["kwargs"] = kwargs
            return {"id": template_id}

    monkeypatch.setattr("confluence_orchestrator.cli.ContentClient", lambda client: DummyClient())
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "content",
            "update-template",
            "tmpl-1",
            "--body-file",
            str(body_file),
            "--type",
            "page",
        ],
    )

    assert result.exit_code == 0
    assert captured["template_id"] == "tmpl-1"
    assert captured["kwargs"]["body"] == "<p>template</p>"
    assert captured["kwargs"]["template_type"] == "page"


def test_batch_command_is_deprecated(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--report-dir", str(tmp_path), "batch", "--server", "internal", "--", "--dry-run"],
    )

    assert result.exit_code == 1
    assert "deprecated" in result.stderr or "deprecated" in result.stdout


def test_batch_scan_uses_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from confluence_orchestrator.orchestration import BatchMetrics

    class DummyRunner:
        def __init__(self, *_: Any, **__: Any) -> None:
            metrics = BatchMetrics()
            metrics.mark_request()
            metrics.mark_processed(1)
            metrics.mark_finished()
            metrics.scanned = 1
            self._metrics = metrics

        def scan(self, cql: str, limit: int, max_results: int | None, start: int):  # type: ignore[override]
            assert cql == "space = TTTC"
            assert limit == 1
            assert max_results == 2
            assert start == 0
            yield {"id": "123"}

        @property
        def last_metrics(self) -> BatchMetrics:
            return self._metrics

    monkeypatch.setattr("confluence_orchestrator.cli.BatchRunner", DummyRunner)

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "batch-native",
            "scan",
            "--cql",
            "space = TTTC",
            "--limit",
            "1",
            "--max-results",
            "2",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["metrics"]["requests"] == 1


def test_webhook_create_invokes_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def create(self, **kwargs: Any) -> dict[str, Any]:  # type: ignore[override]
            calls["kwargs"] = kwargs
            return {"id": "1", **kwargs}

    monkeypatch.setattr("confluence_orchestrator.cli.WebhookClient", lambda http_client: DummyClient())

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "webhook-native",
            "create",
            "--name",
            "Notify",
            "--url",
            "https://example.com/hook",
            "--event",
            "page_created",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert calls["kwargs"]["name"] == "Notify"
    assert json.loads(result.stdout)["id"] == "1"


def test_webhook_list_outputs_count(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def list(self) -> builtins.list[dict[str, Any]]:  # type: ignore[override]
            return [{"id": "1"}]

    monkeypatch.setattr("confluence_orchestrator.cli.WebhookClient", lambda http_client: DummyClient())

    result = runner.invoke(app, ["--report-dir", str(tmp_path), "webhook-native", "list"])

    assert result.exit_code == 0
    assert "1 webhooks" in result.stdout


def test_webhook_delete_invokes_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, Any] = {}

    class DummyClient:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def delete(self, webhook_id: str) -> None:  # type: ignore[override]
            calls["id"] = webhook_id

    monkeypatch.setattr("confluence_orchestrator.cli.WebhookClient", lambda http_client: DummyClient())

    result = runner.invoke(app, ["--report-dir", str(tmp_path), "webhook-native", "delete", "123"])

    assert result.exit_code == 0
    assert calls["id"] == "123"


def test_crawl_tree_passes_incremental_window_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    expected_sync_ts = "2026-02-24T00:00:00+00:00"
    expected_full_ts = "2026-02-20T00:00:00+00:00"

    def fake_crawl_tree_to_disk(
        *, http: Any, root_ref: str, output_dir: Path, options: Any, manifest_path: Path | None
    ) -> dict[str, Any]:
        captured["root_ref"] = root_ref
        captured["output_dir"] = output_dir
        captured["options"] = options
        captured["manifest_path"] = manifest_path
        return {
            "status": "ok",
            "resume_state": {
                "last_sync_timestamp": expected_sync_ts,
                "last_full_reconciliation_timestamp": expected_full_ts,
            },
        }

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())
    monkeypatch.setattr("confluence_orchestrator.cli.crawl_tree_to_disk", fake_crawl_tree_to_disk)

    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "crawl-tree",
            "1",
            "--out",
            str(out_dir),
            "--depth",
            "0",
            "--no-include-attachments",
            "--incremental-overlap-minutes",
            "11",
            "--full-reconciliation-interval-days",
            "21",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["root_ref"] == "1"
    assert captured["output_dir"] == out_dir
    assert captured["options"].incremental_overlap_minutes == 11
    assert captured["options"].full_reconciliation_interval_days == 21
    payload = json.loads(result.stdout)
    assert payload["cache"]["incremental_overlap_minutes"] == 11
    assert payload["cache"]["full_reconciliation_interval_days"] == 21
    assert payload["resume_state"]["last_sync_timestamp"] == expected_sync_ts
    assert payload["resume_state"]["last_full_reconciliation_timestamp"] == expected_full_ts


def test_crawl_tree_default_incremental_window_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def fake_crawl_tree_to_disk(
        *, http: Any, root_ref: str, output_dir: Path, options: Any, manifest_path: Path | None
    ) -> dict[str, Any]:
        captured["options"] = options
        return {"status": "ok"}

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: object())
    monkeypatch.setattr("confluence_orchestrator.cli.crawl_tree_to_disk", fake_crawl_tree_to_disk)

    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "crawl-tree",
            "1",
            "--out",
            str(tmp_path / "out"),
            "--depth",
            "0",
            "--no-include-attachments",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["options"].incremental_overlap_minutes == 5
    assert captured["options"].full_reconciliation_interval_days == 7
    payload = json.loads(result.stdout)
    assert payload["cache"]["incremental_overlap_minutes"] == 5
    assert payload["cache"]["full_reconciliation_interval_days"] == 7
