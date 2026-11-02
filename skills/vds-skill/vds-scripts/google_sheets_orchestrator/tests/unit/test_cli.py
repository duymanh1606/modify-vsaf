from pathlib import Path

from typer.testing import CliRunner
from vds_google_sheets_orchestrator import cli

runner = CliRunner()


def test_help_lists_commands():
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "read" in result.stdout
    assert "list-worksheets" in result.stdout


def test_write_requires_values():
    result = runner.invoke(
        cli.app,
        [
            "write",
            "--spreadsheet-url",
            "https://example.com",
            "--sheet-name",
            "Sheet1",
            "--range",
            "A1:A1",
        ],
    )
    assert result.exit_code != 0
    output = result.output
    assert "values-json" in output or "values-file" in output


def test_update_requires_values():
    result = runner.invoke(
        cli.app,
        [
            "update",
            "--spreadsheet-url",
            "https://example.com",
            "--sheet-name",
            "Sheet1",
            "--range",
            "A1:A1",
        ],
    )
    assert result.exit_code != 0
    output = result.output
    assert "values-json" in output or "values-file" in output


def test_version_flag():
    """Test --version flag shows version info."""
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "vds-google-sheets-orchestrator" in result.stdout


def test_help_shows_global_options():
    """Test that global options are shown in help."""
    result = runner.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "--version" in result.stdout
    assert "--json-only" in result.stdout
    assert "--reports" in result.stdout
    assert "--structured-logs" in result.stdout


def test_json_only_flag_accepted():
    """Test that --json-only flag is accepted."""
    result = runner.invoke(cli.app, ["--json-only", "--help"])
    assert result.exit_code == 0


def test_no_reports_flag_accepted():
    """Test that --no-reports flag is accepted."""
    result = runner.invoke(cli.app, ["--no-reports", "--help"])
    assert result.exit_code == 0


def test_structured_logs_flag_accepted():
    """Test that --structured-logs flag is accepted."""
    result = runner.invoke(cli.app, ["--structured-logs", "--help"])
    assert result.exit_code == 0


def test_reports_written_for_list_worksheets(tmp_path, monkeypatch):
    class DummyClient:
        def list_worksheets(self, spreadsheet_url: str) -> list[str]:
            return ["Sheet1"]

    monkeypatch.setattr(cli, "_build_client", lambda **_: DummyClient())

    result = runner.invoke(
        cli.app,
        [
            "--report-dir",
            str(tmp_path),
            "list-worksheets",
            "--spreadsheet-url",
            "https://example.com",
        ],
    )
    assert result.exit_code == 0

    json_reports = list(Path(tmp_path).glob("list_worksheets_*.json"))
    md_reports = list(Path(tmp_path).glob("list_worksheets_*.md"))

    assert json_reports
    assert md_reports


def test_clear_calls_client(monkeypatch):
    called: dict[str, tuple[str, str, str]] = {}

    class DummyClient:
        def clear_range(self, spreadsheet_url: str, sheet_name: str, target_range: str) -> None:
            called["args"] = (spreadsheet_url, sheet_name, target_range)

    monkeypatch.setattr(cli, "_build_client", lambda **_: DummyClient())

    result = runner.invoke(
        cli.app,
        [
            "--json-only",
            "clear",
            "--spreadsheet-url",
            "https://example.com",
            "--sheet-name",
            "Sheet1",
            "--range",
            "A1:B2",
        ],
    )
    assert result.exit_code == 0
    assert called["args"] == ("https://example.com", "Sheet1", "A1:B2")
    assert '"status": "success"' in result.stdout


def test_create_spreadsheet_json_only(monkeypatch):
    class DummyClient:
        def create_spreadsheet(self, title: str) -> str:
            return f"https://example.com/{title}"

    monkeypatch.setattr(cli, "_build_client", lambda **_: DummyClient())

    result = runner.invoke(
        cli.app,
        [
            "--json-only",
            "create-spreadsheet",
            "--title",
            "MySheet",
        ],
    )
    assert result.exit_code == 0
    assert "https://example.com/MySheet" in result.stdout


def test_export_csv_writes_file(tmp_path, monkeypatch):
    class DummyClient:
        def read_sheet(self, spreadsheet_url: str, sheet_name: str) -> list[list[str]]:
            return [["A", "B"], ["1", "2"]]

    monkeypatch.setattr(cli, "_build_client", lambda **_: DummyClient())
    output_path = tmp_path / "data.csv"

    result = runner.invoke(
        cli.app,
        [
            "--json-only",
            "export",
            "--spreadsheet-url",
            "https://example.com",
            "--sheet-name",
            "Sheet1",
            "--output",
            str(output_path),
            "--format",
            "csv",
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").strip() == "A,B\n1,2"


def test_read_range_calls_client(monkeypatch):
    called: dict[str, tuple[str, str, str]] = {}

    class DummyClient:
        def read_range(self, spreadsheet_url: str, sheet_name: str, range_name: str) -> list[list[str]]:
            called["args"] = (spreadsheet_url, sheet_name, range_name)
            return [["A1", "B1"]]

    monkeypatch.setattr(cli, "_build_client", lambda **_: DummyClient())

    result = runner.invoke(
        cli.app,
        [
            "--json-only",
            "read",
            "--spreadsheet-url",
            "https://example.com",
            "--sheet-name",
            "Sheet1",
            "--range",
            "A1:B1",
        ],
    )
    assert result.exit_code == 0
    assert called["args"] == ("https://example.com", "Sheet1", "A1:B1")
