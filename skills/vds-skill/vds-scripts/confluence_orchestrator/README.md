# VDS Confluence Orchestrator

Python toolkit for Confluence operations using the `atlassian-python-api` SDK. The project closely mirrors the existing
git orchestrator: uv-managed environment, Typer CLI, httpx client with structured logging, and JSON/Markdown run
reports.

## SDK Alignment

- Official reference: [atlassian-python-api Confluence docs](https://atlassian-python-api.readthedocs.io/confluence.html)
- Current pinned dependency is `atlassian-python-api==4.0.7` (latest stable as of February 6, 2026)
- Runtime in this repo uses the legacy `atlassian.Confluence` contract, and wrapper logic auto-adapts for future
  `ConfluenceCloud` / `ConfluenceServer` variants when available
- Compatibility adapters are built in for contract drift points (`move_page` arg shape, bulk permission payload shape,
  comment reply/history method differences)

## Quick Start

```bash
cd vds-scripts
# Optional: sync every orchestrator once
./scripts/bootstrap_uv.sh

# Package-specific sync & tests
uv sync --project confluence_orchestrator --extra dev
./scripts/worktree_uv.sh run --project confluence_orchestrator pytest
```

Run the CLI directly (uv automatically loads the project environment once it has been synced at least once):

```bash
./scripts/worktree_uv.sh run --project confluence_orchestrator vds-cli confluence --help
```

### Authentication preference

For SDK-backed Confluence access, prefer:

1. `VDS_USERNAME` + `VDS_PASSWORD` as the primary authentication mechanism
2. `INTERNAL_CONFLUENCE_TOKEN` / `EXTERNAL_CONFLUENCE_TOKEN` as fallback credentials

This matches the current runtime/client behavior used by `vds-cli confluence` and `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist`.

**Agent-friendly output**
- When using `vds-cli`, pass Typer flags after `--` (e.g. `vds-cli confluence -- --json-only content ...`).
- `--json-only` prints JSON to stdout and skips reports/markdown (logging suppressed).
- `--no-reports` keeps normal console output while avoiding filesystem writes.

Common commands (short form):
```bash
./scripts/worktree_uv.sh run --project confluence_orchestrator vds-cli confluence content page 99647801 --server external --expand body.storage
./scripts/worktree_uv.sh run --project confluence_orchestrator vds-cli confluence content child-pages 88716675 --server internal --expand body.storage
./scripts/worktree_uv.sh run --project confluence_orchestrator vds-cli confluence export page --page-id 99647801 --output page.pdf
```

Via vds-cli router:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence -- content page 99647801 --server external --expand body.storage
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence -- content child-pages 88716675 --server internal --expand body.storage
```

For registry parsing workflows, prefer `content child-pages ... --expand body.storage` so child payloads include page bodies and downstream parsers can avoid extra per-page `get` calls.

**Sync Commands** (new):
```bash
# Sync PDFs to Confluence
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pdfs \
  166465076 \
  --dir /path/to/pdf/directory \
  --server external

# Sync PNGs to Confluence
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence sync pngs \
  166465076 \
  --dir /path/to/png/directory \
  --server external

# Or run scripts directly from confluence_orchestrator directory:
cd vds-scripts/confluence_orchestrator
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_to_confluence.py sync 166465076 --dir /path/to/pdfs --server external
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_png_attachments.py sync 166465076 --dir /path/to/pngs --server external
./scripts/worktree_uv.sh run --project confluence_orchestrator python sync_pdfs_from_markdown.py /path/to/target-state --dry-run
```

See `SYNC_SCRIPTS.md` for complete sync script documentation.

Full command examples:
```bash
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli --help
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli get 99647801 --server external -- --strip-markup
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content page 99647801 --server external --expand body.storage
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content create-page --space TTTC --title "Automation" --body-file ./examples/page_storage.html
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content add-attachment 99647801 --file ./diagram.png --comment "Latest architecture diagram"
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content delete-attachment 99647801 --filename Current_Architecture_Reference.pdf
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content copy-tree 77470432 --target-page-id 96796900 --source-server external --target-server internal --target-space TTPMCOREPM --dry-run
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content copy-tree 77470432 --target-page-id 96796900 --source-server external --target-server internal --target-space TTPMCOREPM
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli batch-native scan --cql "space = TTTC" --limit 10 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli webhook-native create --name "Notify" --url https://example.com/hook --event page_created --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli space-permissions get --space-key TTTC --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli space-permissions set --space-key TTTC --group "confluence-users" --operation read --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli space-management archive --space-key TTTC --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli space-management trash-list --space-key TTTC --limit 25 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli space-management trash-remove --space-key TTTC --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli group list --limit 50 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli group members --group "confluence-users" --limit 100 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli user get --username testuser --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli user get --userkey key123 --expand status,details --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli user password --username testuser --new-password "newpass123" --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli user group-add --username testuser --group "confluence-users" --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli user group-remove --username testuser --group "confluence-users" --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli export page --page-id 99647801 --output page.pdf
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli export space --space-key TTTC --export-type pdf --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli draft get --page-id 12345 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli draft list --space-key TTTC --limit 50 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli draft remove --page-id 12345 --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content ancestors 99647801 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content move 99647801 --target-title "Parent" --position append --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content tables 99647801 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content regex 99647801 --pattern "\d+" --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli content restrictions 99647801 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli history get --page-id 99647801 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli history version --page-id 99647801 --version 2 --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli history remove --page-id 99647801 --version 2 --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli cache statistics --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli cache flush --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli cache flush --cache-name "com.gliffy.cache.gon" --yes --json
./scripts/worktree_uv.sh run --project confluence_orchestrator python -m confluence_orchestrator.cli cache size --json
```

The unified `vds_cli` still routes `confluence` commands through this project, so the usual workflow is:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli env load
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence get 99647801 --server external -- --strip-markup
```

Run reports are written to `vds-scripts/reports/confluence_runs/YYYY/MM/DD/<timestamp>.json` (plus Markdown unless
`--no-markdown` is used).

## Linting

We use Ruff for linting/formatting:

```bash
uv run --extra dev ruff check
uv run --extra dev ruff format
```

## Project Layout

- `src/confluence_orchestrator/config.py` – environment loader (shared VDS env file + repo `.env`)
- `src/confluence_orchestrator/http.py` – shared httpx client with retry/backoff
- `src/confluence_orchestrator/cli.py` – Typer CLI bridging legacy bash scripts **and** exposing native `content`
  subcommands
- `src/confluence_orchestrator/content.py` – REST v1 helper layer (read + write: pages, templates, attachments,
  attachment deletion by filename/ID)
- `src/confluence_orchestrator/content_v2.py` – REST v2 adapter (read-only pages/templates/search)
- `src/confluence_orchestrator/orchestration.py` – Batch polling + webhook management utilities
- `src/confluence_orchestrator/reporting.py` – JSON/Markdown run reports
- `tests/` – pytest suite using httpx MockTransport and Typer CliRunner

## Available Commands

### Search Operations

- **`search`** - CQL search with advanced options

  ```bash
  # Basic CQL search
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search --cql "type = page AND space = TTTC" --limit 25

  # Advanced CQL search with excerpt and pagination
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search --cql "type = page" --advanced --excerpt "highlighted" --start 10 --limit 50

  # Advanced search with expand options
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search --cql "title ~ 'test'" --advanced --expand "body.storage,space" --limit 25
  ```

  > **Note**: Use `--advanced` flag or `--excerpt` parameter to enable advanced search with additional options like
  > excerpt strategies and expanded pagination.

- **`search-by-space-type`** - Search by space and/or content type (helper that builds CQL automatically)

  ```bash
  # Search by space only
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search-by-space-type --space TTTC --limit 50

  # Search by content type only
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search-by-space-type --type page --limit 25

  # Search by both space and type
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search-by-space-type --space TTTC --type page --start 0 --limit 50

  # With expand options
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search-by-space-type --space TTTC --type blogpost --expand "body.storage,version"
  ```

  > **Note**: At least one of `--space` or `--type` must be provided. This helper automatically builds the CQL query for
  > you.

### User & Group Management

- **`group list`** - List all groups

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence group list --limit 50
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence group list --start 0 --limit 100
  ```

- **`group members`** - Get group members

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence group members --group "confluence-users"
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence group members --group "admins" --start 0 --limit 100
  ```

- **`user get`** - Get user details

  ```bash
  # By username
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user get --username testuser
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user get --username testuser --expand status,details

  # By user key
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user get --userkey key123
  ```

- **`user password`** - Change user password (requires confirmation)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user password \
    --username testuser \
    --new-password "newpass123" \
    --yes
  ```

  > **Security Note**: Password changes require `--yes` flag for confirmation. Use strong passwords and follow security
  > best practices.

- **`user group-add`** - Add user to group (requires confirmation)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user group-add \
    --username testuser \
    --group "confluence-users" \
    --yes
  ```

- **`user group-remove`** - Remove user from group (requires confirmation)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence user group-remove \
    --username testuser \
    --group "confluence-users" \
    --yes
  ```

### Export Operations

- **`export page`** - Export page as PDF

  ```bash
  # Export to file
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export page --page-id 99647801 --output page.pdf

  # Export to stdout (binary)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export page --page-id 99647801 > page.pdf

  # API version is auto-detected (Cloud vs Server based on URL)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export page --page-id 99647801 --output page.pdf
  ```

  > **Note**: API version is automatically detected based on server URL (Cloud vs Server). The `--api-version` flag is
  > accepted for CLI compatibility but the SDK auto-detects the mode from client initialization.

- **`export space`** - Get space export download URL

  ```bash
  # PDF export
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export space --space-key TTTC --export-type pdf

  # HTML export
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export space --space-key TTTC --export-type html

  # XML export
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence export space --space-key TTTC --export-type xml
  ```

  > **Note**: Export types supported: `pdf`, `html`, `xml`. The command returns a download URL that can be used to fetch
  > the exported content.

### Draft Management (Server-only)

- **`draft get`** - Get draft page by ID

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence draft get --page-id 12345
  ```

  > **Note**: Server/Data Center only. Not available in Cloud.

- **`draft list`** - List all draft pages in a space

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence draft list --space-key TTTC --limit 50
  ```

  > **Note**: Server/Data Center only. Returns draft pages that haven't been published.

- **`draft remove`** - Remove a draft page

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence draft remove --page-id 12345 --yes
  ```

  > **Warning**: Server/Data Center only. Requires `--yes` flag for confirmation. This permanently removes the draft.

### Advanced Content Operations

- **`content ancestors`** - Get page ancestors (parent pages)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content ancestors 99647801
  ```

  > Returns the hierarchy of parent pages for a given page.

- **`content move`** - Move page to a new location

  ```bash
  # Move page as child of target page
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content move 99647801 \
    --target-title "Parent Page" \
    --position append \
    --yes

  # Move page before target page
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content move 99647801 \
    --target-title "Sibling Page" \
    --position before \
    --yes
  ```

  > **Notes**:
  >
  > - Requires `--yes` flag for confirmation
  > - `--position` can be: `append` (as child), `before`, or `after` (as sibling)
  > - For legacy `atlassian-python-api` contracts, `before/after` are mapped to `above/below` automatically
  > - `--target-title` is the title of the target page

- **`content tables`** - Extract tables from page

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content tables 99647801
  ```

  > Extracts all tables from the page content and returns structured table data.

- **`content regex`** - Extract regex matches from page

  ```bash
  # Extract email addresses
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content regex 99647801 \
    --pattern "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

  # Extract version numbers
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content regex 99647801 \
    --pattern "v\d+\.\d+\.\d+"
  ```

  > **Note**: Uses Python regex syntax. Returns all matches found in the page content.

- **`content restrictions`** - Get content restrictions

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content restrictions 99647801
  ```

  > Returns all viewing/editing restrictions configured for the content.

### History & Versioning

- **`history get`** - Get page history

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence history get --page-id 99647801
  ```

  > Returns the complete version history of a page, including all versions and their metadata.

- **`history version`** - Get specific version

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence history version --page-id 99647801 --version 2
  ```

  > Returns the content of a specific version of a page.

- **`history remove`** - Remove history (experimental)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence history remove --page-id 99647801 --version 2 --yes
  ```

  > **Warning**: Experimental feature. Requires `--yes` flag for confirmation. Permanently removes a specific version
  > from the page history.

### Cache Management (Server-only)

- **`cache statistics`** - Get cache statistics

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache statistics
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache statistics --server external
  ```

  > **Note**: Server/Data Center only. Returns cache hit/miss statistics and performance metrics.

- **`cache flush`** - Flush cache

  ```bash
  # Flush all caches
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache flush --yes

  # Flush specific cache package
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache flush --cache-name "com.gliffy.cache.gon" --yes
  ```

  > **Warning**: Server/Data Center only. Requires `--yes` flag for confirmation. Flushes all caches or a specific cache
  > package (e.g., `com.gliffy.cache.gon`).

- **`cache size`** - Get cache size information

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache size
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence cache size --server external
  ```

  > **Note**: Server/Data Center only. Returns total cache size and cache count information.

### Space Permissions & Management

- **`space-permissions`** - Manage space permissions (get, set, remove)
- **`space-management`** - Manage space lifecycle (archive, trash-list, trash-remove)

```bash
# Apply bulk permissions from a JSON file
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence -- --json-only space-permissions set \
  --space-key TTTC \
  --permissions-file ./permissions-bulk.json \
  --yes \
  --server external
```

Bulk permission payloads (`--permissions-file`) accept either a JSON object or list of objects in this shape:

```json
[
  {"target": {"type": "group", "value": "confluence-users"}, "operations": ["read"]},
  {"target": {"type": "user", "value": "user-key-123"}, "operations": ["read", "write"]},
  {"target": {"type": "anonymous"}, "operations": ["read"]}
]
```

## Recently Added

- ✅ Advanced Search Operations (advanced CQL search, search-by-space-type) - **NEW**
- ✅ Cache Management (Server-only: cache statistics/flush/size) - **NEW**
- ✅ History & Versioning (history get/version/remove) - **NEW**
- ✅ Advanced Content Operations (ancestors, move, tables, regex, restrictions) - **NEW**
- ✅ Draft Management (Server-only: draft get/list/remove) - **NEW**
- ✅ Export Operations (page PDF export, space export URLs) - **NEW**
- ✅ User & Group Management (group list/members, user get/password/group-add/group-remove) - **NEW**
- ✅ Space Permissions Management - **NEW**
- ✅ Space Management (archive, trash operations) - **NEW**

## Pending Work (Phase 2+)

- Pagination helpers + structured analytics exports
- Final hand-off from bash modules once feature parity is reached
