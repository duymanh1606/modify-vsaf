# Google Sheets Orchestrator

VDS standalone orchestrator for Google Sheets automation. Use `vds-cli google-sheets` for normal workflows;
`vds-cli google-sheets` is available for development and direct debugging.

## Requirements

- Python 3.14+
- Google Sheets API + Google Drive API enabled in your Google Cloud project

## Installation

```bash
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh sync --project google_sheets_orchestrator
```

## Authentication

### Service account (recommended)

1. Create a service account JSON key and save it under the shared VDS config root (for example `<config-root>/google_credentials.json`, with `~/.vds/google_credentials.json` as the active Unix-like default).
2. Share the target spreadsheet with the service account email (for private sheets).

CLI usage:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets read --spreadsheet-url <url> --sheet-name Sheet1 \
  --auth-method service_account --credentials-path "$HOME/.vds/google_credentials.json"
```

### OAuth (user consent)

1. Create OAuth credentials JSON and save it under the shared VDS config root (for example `<config-root>/gspread_oauth.json`, with `~/.vds/gspread_oauth.json` as the active Unix-like default).
2. The first run will open a browser to authorize and cache credentials under that same config root.

CLI usage:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets read --spreadsheet-url <url> --sheet-name Sheet1 \
  --auth-method oauth --oauth-credentials-path /path/to/shared-config/gspread_oauth.json
```

### API key (public sheets only)

Set `VDS_GOOGLE_API_KEY` in the shared VDS env file, place the key under the shared VDS config root,
or pass `--api-key`.

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets read --spreadsheet-url <url> --sheet-name Sheet1 \
  --auth-method api_key --api-key "$VDS_GOOGLE_API_KEY"
```

> API key auth can only read public sheets via `open_by_key` / `open_by_url`.

## Environment Variables

```bash
VDS_GOOGLE_CREDENTIALS_PATH=/path/to/shared-config/google_credentials.json
VDS_GOOGLE_OAUTH_CREDENTIALS_PATH=/path/to/shared-config/gspread_oauth.json
VDS_GOOGLE_API_KEY_PATH=/path/to/shared-config/google_api_key.txt
VDS_GOOGLE_API_KEY=...your_api_key...
VDS_GOOGLE_DEFAULT_AUTH_METHOD=service_account
```

## Global CLI Options

All commands support the following global options:

| Option | Description |
|--------|-------------|
| `--version` | Show CLI version and exit |
| `--json-only` | Emit JSON output only (no Rich tables) |
| `--reports/--no-reports` | Enable/disable report file generation |
| `--structured-logs/--no-structured-logs` | Output structured JSON logs to stderr |
| `--report-dir PATH` | Directory for run reports |
| `--help` | Show help message |

## Reports

When `--reports` is enabled (default), each command writes a JSON report to the report directory
(default: `~/.cache/vds-google-sheets-reports`). If `--markdown` is enabled (default), a companion
Markdown summary is also written alongside the JSON file.

## CLI Commands

### Read data

```bash
# Read with Rich table output (default)
vds-cli google-sheets read --spreadsheet-url <url> --sheet-name Sheet1

# Read a limited range
vds-cli google-sheets read --spreadsheet-url <url> --sheet-name Sheet1 --range A1:F10

# Read with JSON output (for scripting)
vds-cli google-sheets --json-only read --spreadsheet-url <url> --sheet-name Sheet1
```

### List worksheets

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets list-worksheets --spreadsheet-url <url>

# JSON output
vds-cli google-sheets --json-only list-worksheets --spreadsheet-url <url> | jq '.worksheets'
```

### Write values

```bash
# Write JSON array of arrays to a range
vds-cli google-sheets write --spreadsheet-url <url> --sheet-name Sheet1 --range A1:B2 \
  --values-json '[["A1","B1"],["A2","B2"]]'

# Write from file
vds-cli google-sheets write --spreadsheet-url <url> --sheet-name Sheet1 --range A1:B2 \
  --values-file data.json
```

### Append rows

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets append --spreadsheet-url <url> --sheet-name Sheet1 \
  --values-json '[["New","Row"]]'
```

### Update values (alias of write)

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets update --spreadsheet-url <url> --sheet-name Sheet1 --range A1:B2 \
  --values-json '[["Updated","Values"]]'
```

### Clear range

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets clear --spreadsheet-url <url> --sheet-name Sheet1 --range A1:B10
```

### Create spreadsheet

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets create-spreadsheet --title "My New Spreadsheet"
```

### Create worksheet

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets create-worksheet --spreadsheet-url <url> --title "New Sheet" \
  --rows 100 --cols 26
```

### Delete worksheet

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets delete-worksheet --spreadsheet-url <url> --sheet-name "Old Sheet"
```

### Export to file

```bash
# Export to CSV
vds-cli google-sheets export --spreadsheet-url <url> --sheet-name Sheet1 --output data.csv

# Export to Excel
vds-cli google-sheets export --spreadsheet-url <url> --sheet-name Sheet1 --output data.xlsx --format xlsx
```

## JSON Output Mode

Use `--json-only` for machine-readable output (ideal for scripting):

```bash
# Get worksheet list as JSON
vds-cli google-sheets --json-only list-worksheets --spreadsheet-url <url> | jq '.worksheets'

# Read sheet data as JSON
vds-cli google-sheets --json-only read --spreadsheet-url <url> --sheet-name Sheet1 > data.json

# Parse row count
vds-cli google-sheets --json-only read --spreadsheet-url <url> --sheet-name Sheet1 | jq '.count'
```

## Structured Logging

Enable JSON logs for monitoring/debugging:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets --structured-logs read --spreadsheet-url <url> 2> logs.json
```

## VDS CLI Integration

Access via the unified `vds-cli` interface:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets read \
  --spreadsheet-url <url> --sheet-name Sheet1

# Pass-through global options
./scripts/worktree_uv.sh run --project vds_cli vds-cli google-sheets -- --json-only read \
  --spreadsheet-url <url> --sheet-name Sheet1 --range A1:F10
```

## Troubleshooting

If `vds-cli google-sheets` reports `ModuleNotFoundError`, install the package:

```bash
cd WHO-project/vds-scripts/google_sheets_orchestrator
uv pip install -e .
```

## API Reference

### Python Usage

```python
from vds_google_sheets_orchestrator import GoogleSheetsClient, GoogleSheetsSettings

# Using settings from the shared VDS env/config layer
client = GoogleSheetsClient()

# Read data
data = client.read_sheet("https://docs.google.com/spreadsheets/d/...", "Sheet1")

# Write data
client.write_range("https://...", "Sheet1", "A1:B2", [["A1", "B1"], ["A2", "B2"]])

# List worksheets
sheets = client.list_worksheets("https://...")
```
.")
```
"A1", "B1"], ["A2", "B2"]])

# List worksheets
sheets = client.list_worksheets("https://...")
```
.")
```
