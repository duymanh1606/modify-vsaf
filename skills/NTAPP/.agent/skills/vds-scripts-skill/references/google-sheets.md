# Google Sheets Commands — VDS Scripts Skill

Standalone package with 10 commands and full VDS CLI standards.

## Commands

```bash
# List worksheets
vds-cli google-sheets list-worksheets \
  --spreadsheet-url <url> --auth-method service_account

# Read a worksheet
vds-cli google-sheets read \
  --spreadsheet-url <url> --sheet-name "Sheet1" --auth-method service_account

# Read a limited range
vds-cli google-sheets read \
  --spreadsheet-url <url> --sheet-name "Sheet1" --range A1:F10

# Write values to a range
vds-cli google-sheets write \
  --spreadsheet-url <url> --sheet-name "Sheet1" --range "A1:B2" \
  --values-json '[["a","b"],["c","d"]]'

# Append rows
vds-cli google-sheets append \
  --spreadsheet-url <url> --sheet-name "Sheet1" --values-json '[["new","row"]]'

# Clear a range
vds-cli google-sheets clear \
  --spreadsheet-url <url> --sheet-name "Sheet1" --range "A1:Z100"

# Create spreadsheet
vds-cli google-sheets create-spreadsheet --title "New Spreadsheet"

# Create worksheet
vds-cli google-sheets create-worksheet \
  --spreadsheet-url <url> --title "NewSheet" --rows 100 --cols 26

# Delete worksheet
vds-cli google-sheets delete-worksheet \
  --spreadsheet-url <url> --sheet-name "SheetToDelete"

# Export to CSV/XLSX
vds-cli google-sheets export \
  --spreadsheet-url <url> --sheet-name "Sheet1" --output data.csv --format csv

# JSON output mode (all commands)
vds-cli google-sheets -- --json-only read \
  --spreadsheet-url <url> --sheet-name "Sheet1"
```

## Authentication

**Defaults**:
- Service account credentials: use the explicit path/config option when available; otherwise the active Unix-like default is `~/.vds/google_credentials.json`
- API key: `VDS_GOOGLE_API_KEY` or, under the active Unix-like default, `~/.vds/google_api_key.txt`

**Auth methods**:
- `service_account` - Uses service account JSON file
- `api_key` - Uses API key from env or file

## Full Command Prefix

Interactive monorepo-root usage commonly uses:

```bash
vds-cli google-sheets <command>
# Or direct uv invocation:
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli google-sheets <command>
```
