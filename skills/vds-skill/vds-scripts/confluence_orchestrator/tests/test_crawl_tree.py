from __future__ import annotations

import hashlib
import json
import threading
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from confluence_orchestrator.cli import app
from confluence_orchestrator.crawl_tree import CrawlOptions, CrawlState, _create_bundle_zip, crawl_tree_to_disk
from typer.testing import CliRunner

if TYPE_CHECKING:
    import pytest

runner = CliRunner()


def test_crawl_options_phase80_defaults() -> None:
    options = CrawlOptions()
    assert options.max_depth == 3
    assert options.max_nodes == 500
    assert options.page_concurrency == 5


def test_crawl_tree_downloads_pages_and_attachments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError(f"search_cql should not be called for numeric root (got {cql})")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            assert expand is not None
            return {
                "id": page_id,
                "title": "Root",
                "body": {
                    "view": {
                        "value": (
                            "<h1>Intro</h1>"
                            "<p>Hello</p>"
                            '<a class="confluence-userlink" data-username="john.doe" href="/display/~john.doe">@John Doe</a>'
                            "<table><tr><th>H1</th><th>H2</th></tr><tr><td>A</td><td>B</td></tr></table>"
                            '<a href="/display/X/Y">Y</a>'
                            '<a href="/pages/viewpage.action?pageId=777">P777</a>'
                            '<a href="/pages/888/Test">P888</a>'
                        )
                    },
                    "storage": {"value": "<p>fallback</p>"},
                },
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
                "space": {"key": "SPACE"},
                "version": {"number": 1, "when": "2026-01-01T00:00:00.000+00:00"},
                "ancestors": [{"id": "10", "title": "Ancestor"}],
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            assert page_id == "1"
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            assert page_id == "1"
            return [
                {
                    "id": "a1",
                    "title": "file.txt",
                    "version": {"number": 2},
                    "extensions": {"fileSize": 3},
                }
            ]

        def get_attachment_content(self, attachment_id: str) -> bytes:
            assert attachment_id == "a1"
            return b"abc"

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--emit-corpus",
            "--emit-link-graph",
            "--emit-tables",
            "--emit-mentions",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)

    assert payload["root_page_id"] == "1"
    assert (out_dir / "1_Root.html").exists()
    assert (out_dir / "attachments" / "a1_file.txt").exists()
    assert payload["corpus_path"]
    assert payload["link_graph_path"]
    assert payload["tables_path"]
    assert payload["mentions_path"]

    corpus_records = [
        json.loads(line)
        for line in Path(payload["corpus_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert corpus_records
    assert corpus_records[0]["depth"] == 0
    assert corpus_records[0]["parent_id"] is None
    assert corpus_records[0]["ancestors"] == ["10"]
    assert corpus_records[0]["ancestor_titles"] == ["Ancestor"]

    tables_path = Path(payload["tables_path"])
    mentions_path = Path(payload["mentions_path"])
    assert tables_path.exists()
    assert mentions_path.exists()

    table_record = json.loads(tables_path.read_text(encoding="utf-8").splitlines()[0])
    assert table_record["page_id"] == "1"
    assert table_record["table_index"] == 0
    assert table_record["headers"] == ["H1", "H2"]
    assert table_record["rows"] == [["A", "B"]]

    mention_records = [
        json.loads(line) for line in mentions_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert mention_records
    assert all(record["page_id"] == "1" for record in mention_records)
    assert any(record.get("type") == "confluence_page" and record.get("value") == "777" for record in mention_records)

    link_graph = json.loads(Path(payload["link_graph_path"]).read_text(encoding="utf-8"))
    edges = link_graph["edges"]
    enriched = {edge.get("target_page_id"): edge for edge in edges if edge.get("target_page_id")}
    assert enriched["777"]["target_type"] == "confluence_page"
    assert enriched["888"]["target_type"] == "confluence_page"


def test_crawl_tree_appends_attachment_suffix_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError(f"search_cql should not be called for numeric root (got {cql})")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            return {
                "id": page_id,
                "title": "Root",
                "body": {"view": {"value": "<p>ok</p>"}, "storage": {"value": ""}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return [
                {
                    "id": "a2",
                    "title": "diagram",
                    "extensions": {"fileSize": 3, "mediaType": "application/pdf"},
                }
            ]

        def get_attachment_content(self, attachment_id: str) -> bytes:
            assert attachment_id == "a2"
            return b"abc"

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--emit-corpus",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (out_dir / "attachments" / "a2_diagram.pdf").exists()


def test_crawl_tree_infers_server_from_root_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called for pageId URL root")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            return {
                "id": page_id,
                "title": "Root",
                "body": {"view": {"value": "<p>ok</p>"}, "storage": {"value": ""}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            raise AssertionError("no attachments expected")

    dummy = DummyClient()
    observed: dict[str, str] = {}

    def _build_http_client(settings, server: str):
        observed["server"] = server
        return dummy

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", _build_http_client)

    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "crawl-tree",
            "http://10.254.136.35:8090/pages/viewpage.action?pageId=1",
            "--out",
            str(out_dir),
            "--depth",
            "0",
            "--no-include-attachments",
        ],
    )

    assert result.exit_code == 0, result.output
    # 10.254.136.35 is one of the two old external Confluence servers — both map to "external"
    assert observed["server"] == "external"


def test_crawl_tree_does_not_emit_tables_or_mentions_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError(f"search_cql should not be called for numeric root (got {cql})")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            return {
                "id": page_id,
                "title": "Root",
                "body": {
                    "view": {
                        "value": (
                            '<a class="confluence-userlink" data-username="john.doe">@John Doe</a>'
                            "<table><tr><td>only</td></tr></table>"
                        )
                    },
                    "storage": {"value": ""},
                },
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            raise AssertionError("no attachments expected")

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["tables_path"] is None
    assert payload["mentions_path"] is None
    assert not (out_dir / "tables.jsonl").exists()
    assert not (out_dir / "mentions.jsonl").exists()


def test_crawl_tree_resolves_display_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            assert 'space="TDOV"' in cql
            assert 'title="My Page"' in cql
            return {"results": [{"id": "42"}]}

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "42"
            return {
                "id": page_id,
                "title": "My Page",
                "body": {"storage": {"value": "<p>ok</p>"}, "view": {"value": ""}},
                "_links": {"base": "http://example", "webui": "/display/TDOV/My+Page"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            raise AssertionError("no attachments expected")

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "--report-dir",
            str(tmp_path),
            "crawl-tree",
            "http://example/display/TDOV/My+Page",
            "--out",
            str(out_dir),
            "--depth",
            "0",
            "--no-include-attachments",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["root_page_id"] == "42"
    assert (out_dir / "42_My Page.html").exists()


def test_crawl_tree_splits_corpus_chunks_by_max_chars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    long_text = "word " * 200  # > 50 chars

    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError(f"search_cql should not be called for numeric root (got {cql})")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            return {
                "id": page_id,
                "title": "Root",
                "body": {"view": {"value": f"<h1>Intro</h1><p>{long_text}</p>"}, "storage": {"value": ""}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            raise AssertionError("no attachments expected")

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--emit-corpus",
            "--chunk-max-chars",
            "50",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    corpus_path = Path(payload["corpus_path"])
    corpus = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(corpus) > 1
    assert all(len(entry.get("text") or "") <= 50 for entry in corpus)
    assert {entry.get("chunk_ordinal") for entry in corpus} == set(range(len(corpus)))
    assert corpus[0]["source_type"] == "confluence"
    assert corpus[0]["doc_class"] == "canonical_doc"
    assert corpus[0]["generated_flag"] is False
    assert corpus[0]["historical_flag"] is False
    assert corpus[0]["discovery"] == "confluence_crawl_page"

    base_key = "1|Intro"
    expected_first = hashlib.sha256(base_key.encode("utf-8")).hexdigest()[:16]
    expected_second = hashlib.sha256(f"{base_key}|1".encode()).hexdigest()[:16]
    assert corpus[0]["chunk_id"] == expected_first
    assert corpus[1]["chunk_id"] == expected_second


def test_crawl_tree_uses_export_view_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, limit: int = 25, expand: list[str] | None = None, **_: Any) -> dict[str, Any]:
            raise AssertionError(f"search_cql should not be called for numeric root (got {cql})")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            assert page_id == "1"
            assert expand is not None
            assert "body.export_view" in expand
            return {
                "id": page_id,
                "title": "Root",
                "body": {
                    "view": {"value": "<p>view</p>"},
                    "export_view": {"value": "<p>export</p>"},
                    "storage": {"value": "<p>storage</p>"},
                },
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            raise AssertionError("no attachments expected")

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--body-format",
            "export_view",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    html_path = Path(payload["page"]["html_path"])
    assert "export" in html_path.read_text(encoding="utf-8")
    assert payload["page"]["source_format"] == "html-export-view"


def test_crawl_tree_concurrency_preserves_deterministic_order(tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            # Force non-deterministic completion order when concurrency > 1.
            if page_id == "2":
                time.sleep(0.04)
            if page_id == "3":
                time.sleep(0.01)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<h1>{page_id}</h1><p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": int(page_id)},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    client = DummyClient()
    sequential = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=tmp_path / "seq",
        options=CrawlOptions(max_depth=1, include_attachments=False, emit_corpus=True, page_concurrency=1),
    )
    concurrent = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=tmp_path / "concurrent",
        options=CrawlOptions(max_depth=1, include_attachments=False, emit_corpus=True, page_concurrency=4),
    )

    assert [p["page_id"] for p in sequential["child_pages"]] == ["2", "3"]
    assert [p["page_id"] for p in concurrent["child_pages"]] == ["2", "3"]

    seq_corpus = Path(sequential["corpus_path"]).read_text(encoding="utf-8").splitlines()
    conc_corpus = Path(concurrent["corpus_path"]).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["page_id"] for line in seq_corpus] == [json.loads(line)["page_id"] for line in conc_corpus]


def test_crawl_tree_parallelizes_child_discovery_with_page_fetch(tmp_path: Path) -> None:
    lock = threading.Lock()
    overlap_counter = 0
    active_page_calls = 0
    active_children_calls = 0

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            nonlocal overlap_counter, active_page_calls, active_children_calls
            with lock:
                active_page_calls += 1
                if active_children_calls > 0:
                    overlap_counter += 1
            time.sleep(0.03)
            with lock:
                active_page_calls -= 1
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": int(page_id)},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            nonlocal overlap_counter, active_page_calls, active_children_calls
            with lock:
                active_children_calls += 1
                if active_page_calls > 0:
                    overlap_counter += 1
            time.sleep(0.03)
            with lock:
                active_children_calls -= 1
            if page_id == "1":
                return [{"id": "2"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=tmp_path / "out",
        options=CrawlOptions(max_depth=1, include_attachments=False, page_concurrency=1),
    )

    assert result["child_pages"][0]["page_id"] == "2"
    assert overlap_counter > 0


def test_crawl_tree_concurrent_throughput_exceeds_2x_sequential(tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            time.sleep(0.08)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": int(page_id)},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": str(i)} for i in range(2, 8)]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    client = DummyClient()
    start = time.perf_counter()
    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=tmp_path / "seq",
        options=CrawlOptions(max_depth=1, include_attachments=False, page_concurrency=1),
    )
    sequential_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=tmp_path / "concurrent",
        options=CrawlOptions(max_depth=1, include_attachments=False, page_concurrency=5),
    )
    concurrent_elapsed = time.perf_counter() - start

    assert concurrent_elapsed * 2 <= sequential_elapsed


def test_crawl_tree_structure_first_mode_pre_discovers_before_fetch(tmp_path: Path) -> None:
    call_log: list[tuple[str, str]] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            call_log.append(("page", page_id))
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": int(page_id)},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            call_log.append(("children", page_id))
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}]
            if page_id == "2":
                return [{"id": "4"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=tmp_path / "out",
        options=CrawlOptions(
            max_depth=2,
            include_attachments=False,
            page_concurrency=2,
            staged_mode="structure_first",
            max_nodes=2,
        ),
    )

    first_page_call_index = next(index for index, event in enumerate(call_log) if event[0] == "page")
    assert all(event[0] == "children" for event in call_log[:first_page_call_index])
    assert call_log[0] == ("children", "1")
    assert [page["page_id"] for page in result["child_pages"]] == ["2"]
    assert result["resume_state"]["termination_reason"] == "max_nodes_reached"
    assert result["resume_state"]["pending_queue_size"] > 0
    assert result["crawl_mode"]["staged_mode"] == "structure_first"
    assert result["crawl_mode"]["page_concurrency"] == 2


# =============================================================================
# TSK-188: Resume/Incremental Crawling Tests
# =============================================================================


def test_crawl_state_serialization() -> None:
    """Test CrawlState can serialize and deserialize correctly."""
    state = CrawlState(
        root_page_id="123",
        body_format="view",
        visited_pages={
            "123": {"version": 5, "html_sha256": "abc123", "visited_at": "2026-01-01T00:00:00Z"},
            "456": {"version": 3, "html_sha256": "def456", "visited_at": "2026-01-01T00:01:00Z"},
        },
        pending_queue=[("789", "123", 1), ("101", "123", 1)],
        started_at="2026-01-01T00:00:00Z",
        last_updated_at="2026-01-01T00:05:00Z",
        completed=False,
        last_sync_timestamp="2026-01-01T00:05:00Z",
        last_full_reconciliation_timestamp="2026-01-01T00:00:00Z",
    )

    # Serialize
    data = state.to_dict()
    assert data["root_page_id"] == "123"
    assert len(data["visited_pages"]) == 2
    assert len(data["pending_queue"]) == 2
    assert data["completed"] is False
    assert data["last_sync_timestamp"] == "2026-01-01T00:05:00Z"
    assert data["last_full_reconciliation_timestamp"] == "2026-01-01T00:00:00Z"

    # Deserialize
    restored = CrawlState.from_dict(data)
    assert restored.root_page_id == "123"
    assert restored.body_format == "view"
    assert len(restored.visited_pages) == 2
    assert restored.visited_pages["123"]["version"] == 5
    assert len(restored.pending_queue) == 2
    assert restored.pending_queue[0] == ("789", "123", 1)
    assert restored.last_sync_timestamp == "2026-01-01T00:05:00Z"
    assert restored.last_full_reconciliation_timestamp == "2026-01-01T00:00:00Z"


def test_crawl_state_is_page_unchanged_by_version() -> None:
    """Test page unchanged detection by version number."""
    state = CrawlState(
        root_page_id="1",
        body_format="view",
        visited_pages={"1": {"version": 5, "html_sha256": "abc", "visited_at": "2026-01-01T00:00:00Z"}},
        pending_queue=[],
        started_at="2026-01-01T00:00:00Z",
        last_updated_at="2026-01-01T00:00:00Z",
    )

    # Same version = unchanged
    assert state.is_page_unchanged("1", 5, None) is True
    # Different version = changed
    assert state.is_page_unchanged("1", 6, None) is False
    # Unknown page = changed
    assert state.is_page_unchanged("2", 5, None) is False


def test_crawl_state_is_page_unchanged_by_hash() -> None:
    """Test page unchanged detection by content hash."""
    state = CrawlState(
        root_page_id="1",
        body_format="view",
        visited_pages={"1": {"version": None, "html_sha256": "abc123", "visited_at": "2026-01-01T00:00:00Z"}},
        pending_queue=[],
        started_at="2026-01-01T00:00:00Z",
        last_updated_at="2026-01-01T00:00:00Z",
    )

    # Same hash = unchanged
    assert state.is_page_unchanged("1", None, "abc123") is True
    # Different hash = changed
    assert state.is_page_unchanged("1", None, "xyz789") is False


def test_crawl_tree_max_nodes_limits_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test --max-nodes stops crawl after N pages."""
    pages_fetched: list[str] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            pages_fetched.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            # Root has 5 children
            if page_id == "1":
                return [{"id": str(i)} for i in range(2, 7)]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "2",
            "--no-include-attachments",
            "--max-nodes",
            "3",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)

    # Should have processed exactly 3 nodes
    assert payload["resume_state"]["nodes_processed"] == 3
    assert payload["resume_state"]["completed"] is False
    assert payload["resume_state"]["termination_reason"] == "max_nodes_reached"
    assert payload["resume_state"]["pending_queue_size"] > 0
    assert len(pages_fetched) == 3


def test_crawl_tree_cli_accepts_crawl_max_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": "<p>Content</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return [{"id": "2"}] if page_id == "1" else []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: DummyClient())

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
            "--crawl-max-depth",
            "0",
            "--crawl-max-nodes",
            "10",
            "--no-include-attachments",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["resume_state"]["nodes_processed"] == 1
    assert payload["crawl_mode"]["page_concurrency"] == 5


def test_crawl_tree_rejects_depth_out_of_range(tmp_path: Path) -> None:
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
            "-1",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--depth'" in result.output


def test_crawl_tree_resume_saves_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that crawl saves state file for resume."""

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--resume",
        ],
    )

    assert result.exit_code == 0, result.output

    # State file should exist
    state_path = out_dir / "crawl_state.json"
    assert state_path.exists()

    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_data["root_page_id"] == "1"
    assert state_data["completed"] is True
    assert "1" in state_data["visited_pages"]
    assert state_data["run_diagnostics"]["termination_reason"] == "queue_exhausted"
    assert state_data["run_diagnostics"]["pending_queue_size"] == 0


def test_crawl_tree_resume_skips_unchanged_pages(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that resume mode skips pages that haven't changed."""
    pages_fetched: list[str] = []
    call_count: dict[str, int] = {"1": 0}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            call_count["1"] = call_count.get("1", 0) + 1
            pages_fetched.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},  # Version stays at 1
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    out_dir = tmp_path / "out"

    # First crawl
    result1 = crawl_tree_to_disk(
        http=dummy,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    assert result1["resume_state"]["nodes_processed"] == 1
    pages_fetched.clear()

    # Second crawl with resume - should skip unchanged page
    result2 = crawl_tree_to_disk(
        http=dummy,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    # Page should be skipped (only version check, not full fetch)
    assert result2["resume_state"]["skipped_unchanged"] == 1
    assert result2["progress_event"]["pages_skipped_unchanged"] == 1


def test_crawl_tree_resume_avoids_full_fetch_for_unchanged_pages(tmp_path: Path) -> None:
    """Phase 27 TSK-275.1: unchanged pages should only use version checks on warm runs."""
    full_fetch_calls: list[str] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand and "version" in expand and len(expand) == 1:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": 1},
                }
            full_fetch_calls.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "88716667":
                return [{"id": "100"}, {"id": "200"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )
    assert len(full_fetch_calls) == 3

    full_fetch_calls.clear()
    result = crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )
    assert result["resume_state"]["skipped_unchanged"] == 3
    assert full_fetch_calls == []


def test_crawl_tree_resume_runs_version_pass_before_full_fetch(tmp_path: Path) -> None:
    call_log: list[tuple[str, str]] = []
    versions = {"1": 1, "2": 1}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand == ["version"]:
                call_log.append(("version", page_id))
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": versions[page_id]},
                }

            call_log.append(("full", page_id))
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "space": {"key": "SPACE"},
                "version": {"number": versions[page_id]},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    call_log.clear()
    versions["2"] = 2
    result = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    assert result["resume_state"]["skipped_unchanged"] == 1
    assert ("version", "1") in call_log
    assert ("full", "1") not in call_log
    assert call_log.index(("version", "2")) < call_log.index(("full", "2"))


def test_crawl_tree_resume_refreshes_only_changed_page(tmp_path: Path) -> None:
    """Phase 27 TSK-275.2: changed-only refresh should fetch only the mutated page."""
    full_fetch_calls: list[str] = []
    versions = {"88716667": 1, "100": 1, "200": 1}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand and "version" in expand and len(expand) == 1:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": versions[page_id]},
                }
            full_fetch_calls.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id} v{versions[page_id]}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": versions[page_id]},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "88716667":
                return [{"id": "100"}, {"id": "200"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    full_fetch_calls.clear()
    versions["200"] = 2
    result = crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )
    assert result["resume_state"]["skipped_unchanged"] == 2
    assert full_fetch_calls == ["200"]


def test_crawl_tree_resume_emit_corpus_preserves_unchanged_pages_on_partial_refresh(tmp_path: Path) -> None:
    versions = {"1": 1, "2": 1, "3": 1}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand and "version" in expand and len(expand) == 1:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": versions[page_id]},
                }
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id} v{versions[page_id]}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": versions[page_id]},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    initial = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True, emit_corpus=True),
    )
    assert initial["corpus_path"]

    versions["3"] = 2
    refreshed = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True, emit_corpus=True),
    )
    assert refreshed["resume_state"]["skipped_unchanged"] == 2

    corpus_path = Path(str(refreshed["corpus_path"]))
    corpus_rows = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    page_ids = {str(row.get("page_id") or "") for row in corpus_rows if isinstance(row, dict)}
    assert page_ids == {"1", "2", "3"}

    page_three_text = [str(row.get("text") or "") for row in corpus_rows if str(row.get("page_id") or "") == "3"]
    assert any("v2" in text for text in page_three_text)


def test_crawl_tree_cold_vs_warm_call_profile_for_root_88716667(tmp_path: Path) -> None:
    """Phase 27 TSK-275.3 benchmark proxy: warm run should reduce full fetch calls."""
    full_fetch_calls: list[str] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand and "version" in expand and len(expand) == 1:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": 1},
                }
            full_fetch_calls.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "88716667":
                return [{"id": "100"}, {"id": "200"}, {"id": "300"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )
    cold_full_fetch = len(full_fetch_calls)
    assert cold_full_fetch == 4

    full_fetch_calls.clear()
    crawl_tree_to_disk(
        http=client,
        root_ref="88716667",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )
    warm_full_fetch = len(full_fetch_calls)
    assert warm_full_fetch < cold_full_fetch


def test_crawl_tree_resume_state_reports_queue_exhausted(tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=tmp_path / "out",
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    assert result["resume_state"]["completed"] is True
    assert result["resume_state"]["termination_reason"] == "queue_exhausted"
    assert result["resume_state"]["pending_queue_size"] == 0


def test_crawl_tree_resume_skip_unchanged_with_concurrency(tmp_path: Path) -> None:
    full_fetch_calls: list[str] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand and "version" in expand and len(expand) == 1:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "body": {"view": {"value": ""}},
                    "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                    "version": {"number": 1},
                }
            full_fetch_calls.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}, {"id": "4"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    out_dir = tmp_path / "out"
    client = DummyClient()
    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True, page_concurrency=3),
    )
    cold_full_fetch = len(full_fetch_calls)
    assert cold_full_fetch == 4

    full_fetch_calls.clear()
    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True, page_concurrency=3),
    )
    assert len(full_fetch_calls) < cold_full_fetch


def test_crawl_tree_resume_supports_incremental_high_water_mark_and_reconciliation(tmp_path: Path) -> None:
    search_calls: list[dict[str, Any]] = []
    deleted = {"value": False}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            version_num = 1
            if expand == ["version"]:
                return {
                    "id": page_id,
                    "title": f"Page {page_id}",
                    "version": {"number": version_num},
                }
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "space": {"key": "SPACE"},
                "version": {"number": version_num},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1" and not deleted["value"]:
                return [{"id": "2"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

        def search_by_space_and_type(
            self,
            space_key: str | None = None,
            content_type: str | None = None,
            *,
            limit: int = 25,
            start: int = 0,
            expand: list[str] | None = None,
            last_modified_after: Any = None,
            overlap_minutes: int = 0,
            **_: Any,
        ) -> dict[str, Any]:
            search_calls.append(
                {
                    "space_key": space_key,
                    "content_type": content_type,
                    "limit": limit,
                    "start": start,
                    "last_modified_after": last_modified_after,
                    "overlap_minutes": overlap_minutes,
                }
            )
            if last_modified_after is not None:
                return {"results": []}
            if deleted["value"]:
                return {"results": [{"id": "1"}]}
            return {"results": [{"id": "1"}, {"id": "2"}]}

    out_dir = tmp_path / "out"
    client = DummyClient()

    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    deleted["value"] = True
    search_calls.clear()
    result = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    state_data = json.loads((out_dir / "crawl_state.json").read_text(encoding="utf-8"))
    assert "2" not in state_data["visited_pages"]
    assert state_data["last_sync_timestamp"] is not None
    assert state_data["last_full_reconciliation_timestamp"] is not None
    assert state_data["run_diagnostics"]["full_reconciliation_ran"] is True
    assert state_data["run_diagnostics"]["full_reconciliation_deleted_ids"] == ["2"]
    assert state_data["run_diagnostics"]["full_reconciliation_skipped"] is False
    assert state_data["run_diagnostics"]["full_reconciliation_skip_reason"] is None
    assert state_data["run_diagnostics"]["incremental_known_page_count"] == 2
    assert state_data["run_diagnostics"]["incremental_high_water_mark_ran"] is True
    assert state_data["run_diagnostics"]["incremental_high_water_mark_skipped"] is False
    assert state_data["run_diagnostics"]["incremental_high_water_mark_skip_reason"] is None

    incremental_calls = [call for call in search_calls if call["last_modified_after"] is not None]
    assert incremental_calls
    assert all(call["overlap_minutes"] == 5 for call in incremental_calls)
    full_calls = [call for call in search_calls if call["last_modified_after"] is None]
    assert full_calls

    assert result["resume_state"]["last_sync_timestamp"] is not None
    assert result["resume_state"]["last_full_reconciliation_timestamp"] is not None


def test_crawl_tree_resume_skips_full_reconciliation_for_root_only_state(tmp_path: Path) -> None:
    search_calls: list[dict[str, Any]] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand == ["version"]:
                return {"id": page_id, "title": f"Page {page_id}", "version": {"number": 1}}
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "space": {"key": "SPACE"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

        def search_by_space_and_type(
            self,
            space_key: str | None = None,
            content_type: str | None = None,
            *,
            limit: int = 25,
            start: int = 0,
            expand: list[str] | None = None,
            last_modified_after: Any = None,
            overlap_minutes: int = 0,
            **_: Any,
        ) -> dict[str, Any]:
            search_calls.append(
                {
                    "space_key": space_key,
                    "content_type": content_type,
                    "limit": limit,
                    "start": start,
                    "last_modified_after": last_modified_after,
                    "overlap_minutes": overlap_minutes,
                }
            )
            if last_modified_after is not None:
                return {"results": []}
            return {"results": [{"id": "1"}]}

    out_dir = tmp_path / "out"
    client = DummyClient()

    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    search_calls.clear()
    result = crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    state_data = json.loads((out_dir / "crawl_state.json").read_text(encoding="utf-8"))
    assert state_data["last_full_reconciliation_timestamp"] is not None
    assert state_data["run_diagnostics"]["full_reconciliation_ran"] is False
    assert state_data["run_diagnostics"]["full_reconciliation_skipped"] is True
    assert state_data["run_diagnostics"]["full_reconciliation_skip_reason"] == "known_pages_lte_1"
    assert state_data["run_diagnostics"]["incremental_known_page_count"] == 1
    assert state_data["run_diagnostics"]["incremental_high_water_mark_ran"] is False
    assert state_data["run_diagnostics"]["incremental_high_water_mark_skipped"] is True
    assert state_data["run_diagnostics"]["incremental_high_water_mark_skip_reason"] == "known_pages_lte_1"

    incremental_calls = [call for call in search_calls if call["last_modified_after"] is not None]
    assert not incremental_calls
    full_calls = [call for call in search_calls if call["last_modified_after"] is None]
    assert not full_calls

    assert result["resume_state"]["last_full_reconciliation_timestamp"] is not None


def test_crawl_tree_exposes_http_telemetry_in_manifest_and_state(tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

        def get_runtime_telemetry(self) -> dict[str, Any]:
            return {
                "retries_total": 2,
                "rate_limit_total": 1,
                "timeout_total": 1,
                "adaptive_throttle": {"effective_concurrency_signal": 0.73, "pressure_score": 0.27},
                "recent_retry_events": [{"reason": "http_429"}, {"reason": "timeout"}],
            }

    out_dir = tmp_path / "out"
    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, resume=True),
    )

    assert result["http_telemetry"]["retries_total"] == 2
    assert result["telemetry"]["retries_total"] == 2
    assert result["http_telemetry"]["adaptive_throttle"]["effective_concurrency_signal"] == 0.73
    assert result["resume_state"]["completed"] is True

    state_data = json.loads((out_dir / "crawl_state.json").read_text(encoding="utf-8"))
    assert state_data["run_diagnostics"]["http_telemetry"]["timeout_total"] == 1
    assert state_data["run_diagnostics"]["telemetry"]["timeout_total"] == 1
    assert state_data["run_diagnostics"]["progress_event"]["pages_discovered"] == 1


def test_crawl_tree_emits_crawl_progress_runtime_events(tmp_path: Path) -> None:
    emitted_events: list[tuple[str, dict[str, Any]]] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    def _capture_runtime_event(event: str, payload: dict[str, Any]) -> None:
        emitted_events.append((event, payload))

    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=tmp_path / "out",
        options=CrawlOptions(
            max_depth=1,
            include_attachments=False,
            page_concurrency=2,
            runtime_event_sink=_capture_runtime_event,
        ),
    )

    progress_events = [payload for name, payload in emitted_events if name == "crawl_progress"]
    assert progress_events
    assert progress_events[-1]["pages_discovered"] == result["progress_event"]["pages_discovered"]
    assert progress_events[-1]["pages_fetched"] == result["progress_event"]["pages_fetched"]
    assert progress_events[-1]["pages_failed"] == result["progress_event"]["pages_failed"]
    assert progress_events[-1]["pages_skipped_unchanged"] == result["progress_event"]["pages_skipped_unchanged"]


def test_crawl_tree_emits_pages_deleted_event(tmp_path: Path) -> None:
    emitted_events: list[tuple[str, dict[str, Any]]] = []
    search_calls: list[dict[str, Any]] = []
    deleted = {"value": False}

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            if expand == ["version"]:
                return {"id": page_id, "title": f"Page {page_id}", "version": {"number": 1}}
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "space": {"key": "SPACE"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1" and not deleted["value"]:
                return [{"id": "2"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

        def search_by_space_and_type(
            self,
            space_key: str | None = None,
            content_type: str | None = None,
            *,
            limit: int = 25,
            start: int = 0,
            expand: list[str] | None = None,
            last_modified_after: Any = None,
            overlap_minutes: int = 0,
            **_: Any,
        ) -> dict[str, Any]:
            search_calls.append(
                {
                    "space_key": space_key,
                    "content_type": content_type,
                    "limit": limit,
                    "start": start,
                    "last_modified_after": last_modified_after,
                    "overlap_minutes": overlap_minutes,
                }
            )
            if last_modified_after is not None:
                return {"results": []}
            if deleted["value"]:
                return {"results": [{"id": "1"}]}
            return {"results": [{"id": "1"}, {"id": "2"}]}

    def _capture_runtime_event(event: str, payload: dict[str, Any]) -> None:
        emitted_events.append((event, payload))

    out_dir = tmp_path / "out"
    client = DummyClient()

    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(
            max_depth=1,
            include_attachments=False,
            resume=True,
            runtime_event_sink=_capture_runtime_event,
        ),
    )
    deleted["value"] = True
    emitted_events.clear()
    search_calls.clear()

    crawl_tree_to_disk(
        http=client,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(
            max_depth=1,
            include_attachments=False,
            resume=True,
            runtime_event_sink=_capture_runtime_event,
        ),
    )

    pages_deleted_events = [payload for name, payload in emitted_events if name == "pages_deleted"]
    assert pages_deleted_events
    assert pages_deleted_events[-1]["deleted_count"] == 1
    assert pages_deleted_events[-1]["page_ids"] == ["2"]


def test_crawl_tree_throughput_metrics_and_adaptive_signal(tmp_path: Path) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

        def get_runtime_telemetry(self) -> dict[str, Any]:
            return {
                "adaptive_throttle": {"effective_concurrency_signal": 0.2, "pressure_score": 0.8},
                "latency_ms": {"operation": {"p95": 123.4}},
                "recent_retry_events": [{"reason": "http_429"}, {"reason": "timeout"}],
            }

    result = crawl_tree_to_disk(
        http=DummyClient(),
        root_ref="1",
        output_dir=tmp_path / "out",
        options=CrawlOptions(max_depth=1, include_attachments=False, page_concurrency=4),
    )

    telemetry = result["http_telemetry"]
    assert telemetry["inflight_workers"] == 1
    assert telemetry["queue_depth"] == 0
    assert telemetry["pages_per_second"] > 0
    assert telemetry["retry_events"] == 2
    assert telemetry["p95_page_latency_ms"] == 123.4

    progress_event = result["progress_event"]
    assert progress_event == {
        "pages_discovered": 3,
        "pages_fetched": 3,
        "pages_failed": 0,
        "pages_skipped": 0,
        "pages_skipped_unchanged": 0,
        "throttle": {
            "configured_page_concurrency": 4,
            "effective_page_concurrency": 1,
            "effective_concurrency_signal": 0.2,
            "pressure_score": 0.8,
        },
    }


def test_crawl_tree_resume_continues_from_pending_queue(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that resume continues from where it left off."""
    pages_fetched: list[str] = []

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            pages_fetched.append(page_id)
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": int(page_id)},  # Different versions
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            if page_id == "1":
                return [{"id": "2"}, {"id": "3"}, {"id": "4"}]
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    out_dir = tmp_path / "out"

    # First crawl with max_nodes=2 (will process 1 and 2, leave 3,4 pending)
    result1 = crawl_tree_to_disk(
        http=dummy,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True, max_nodes=2),
    )

    assert result1["resume_state"]["nodes_processed"] == 2
    assert result1["resume_state"]["completed"] is False

    pages_fetched.clear()

    # Resume crawl - should continue with remaining pages
    result2 = crawl_tree_to_disk(
        http=dummy,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=1, include_attachments=False, resume=True),
    )

    # Should have processed pages 3 and 4 (plus version checks for 1, 2)
    assert result2["resume_state"]["completed"] is True


def test_crawl_tree_cli_resume_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test CLI --resume flag works."""

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": "<p>Content</p>"}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Page"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

    out_dir = tmp_path / "out"

    # Run with --resume
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
            "--resume",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert "resume_state" in payload
    assert payload["resume_state"]["state_path"] == str(out_dir / "crawl_state.json")


def test_crawl_tree_cli_accepts_phase27_compat_flags(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Phase 27 compatibility: crawl-tree should accept cache/content root flags from audit orchestrator."""

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": "<p>Content</p>"}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Page"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: DummyClient())

    out_dir = tmp_path / "out"
    content_root = tmp_path / "content-root"
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
            "--cache-mode",
            "refresh",
            "--cache-ttl-hours",
            "48",
            "--incremental",
            "--content-root",
            str(content_root),
            "--project-storage-key",
            "project-x",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["cache"]["mode"] == "refresh"
    assert payload["cache"]["ttl_hours"] == 48
    assert payload["cache"]["incremental"] is True
    assert payload["cache"]["effective_resume"] is True
    assert payload["cache"]["content_root"] == str(content_root)
    assert payload["cache"]["project_storage_key"] == "project-x"


def test_crawl_tree_cli_accepts_concurrency_and_staged_mode_flags(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": "<p>Content</p>"}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Page"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: DummyClient())

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
            "--page-concurrency",
            "3",
            "--staged-mode",
            "structure-first",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["crawl_mode"]["page_concurrency"] == 3
    assert payload["crawl_mode"]["staged_mode"] == "structure_first"


# =============================================================================
# TSK-189: Bundle Zip Tests
# =============================================================================


def test_create_bundle_zip_contains_all_artifacts(tmp_path: Path) -> None:
    """Test that bundle zip contains all expected files."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    attachments_dir = out_dir / "attachments"
    attachments_dir.mkdir()

    # Create mock files
    (out_dir / "123_Root.html").write_text("<p>Root page</p>")
    (out_dir / "456_Child.html").write_text("<p>Child page</p>")
    (attachments_dir / "a1_file.txt").write_text("attachment content")
    (out_dir / "corpus.jsonl").write_text('{"chunk_id": "abc"}\n')
    (out_dir / "link-graph.json").write_text('{"edges": []}')
    (out_dir / "tables.jsonl").write_text('{"table_id": "t1"}\n')
    (out_dir / "mentions.jsonl").write_text('{"mention_id": "m1"}\n')
    (out_dir / "crawl_state.json").write_text('{"completed": true}')
    manifest_path = out_dir / "crawl_manifest.json"
    manifest_path.write_text('{"root_page_id": "123"}')

    # Create bundle
    bundle_path = _create_bundle_zip(out_dir, "123", manifest_path)

    assert bundle_path.exists()
    assert bundle_path.suffix == ".zip"
    assert "crawl_bundle_123_" in bundle_path.name

    # Verify contents
    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        assert "123_Root.html" in names
        assert "456_Child.html" in names
        assert "attachments/a1_file.txt" in names
        assert "corpus.jsonl" in names
        assert "link-graph.json" in names
        assert "tables.jsonl" in names
        assert "mentions.jsonl" in names
        assert "crawl_state.json" in names
        assert "crawl_manifest.json" in names


def test_crawl_tree_bundle_option(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test --bundle flag creates zip archive."""

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": f"Page {page_id}",
                "body": {"view": {"value": f"<p>Content {page_id}</p>"}},
                "_links": {"base": "http://example", "webui": f"/display/SPACE/Page{page_id}"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return [{"id": "a1", "title": "file.txt", "version": {"number": 1}}]

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b"attachment content"

    dummy = DummyClient()
    monkeypatch.setattr("confluence_orchestrator.cli._build_http_client", lambda settings, server: dummy)

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
            "--emit-corpus",
            "--emit-link-graph",
            "--bundle",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)

    # Bundle should be created
    assert "bundle_path" in payload
    bundle_path = Path(payload["bundle_path"])
    assert bundle_path.exists()

    # Verify bundle contents
    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        assert any(name.endswith(".html") for name in names)
        assert "corpus.jsonl" in names
        assert "link-graph.json" in names
        assert "crawl_manifest.json" in names


def test_crawl_tree_bundle_with_no_attachments(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test bundle works even without attachments."""

    class DummyClient:
        def search_cql(self, cql: str, **_: Any) -> dict[str, Any]:
            raise AssertionError("search_cql should not be called")

        def get_page(self, page_id: str, expand: list[str] | None = None) -> dict[str, Any]:
            return {
                "id": page_id,
                "title": "Root",
                "body": {"view": {"value": "<p>Content</p>"}},
                "_links": {"base": "http://example", "webui": "/display/SPACE/Root"},
                "version": {"number": 1},
            }

        def get_child_pages(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachments(self, page_id: str) -> list[dict[str, Any]]:
            return []

        def get_attachment_content(self, attachment_id: str) -> bytes:
            return b""

    dummy = DummyClient()
    out_dir = tmp_path / "out"

    result = crawl_tree_to_disk(
        http=dummy,
        root_ref="1",
        output_dir=out_dir,
        options=CrawlOptions(max_depth=0, include_attachments=False, bundle=True),
    )

    assert "bundle_path" in result
    bundle_path = Path(result["bundle_path"])
    assert bundle_path.exists()

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        assert "1_Root.html" in names
        assert "crawl_manifest.json" in names
