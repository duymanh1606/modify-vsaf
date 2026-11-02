<!-- diátaxis: how-to -->

# Confluence → Bitbucket Sync Workflow

> Validate documentation health, push to Confluence, and verify Bitbucket links in a single pipeline.

## Prerequisites

- `vds-scripts` cloned and bootstrapped (`./scripts/worktree_uv.sh sync`)
- `vds-cli doctor` passes
- `~/.vds/.env` contains `VDS_USERNAME`, `VDS_PASSWORD`, `CONFLUENCE_HOST`
- Bitbucket project slug and target repo known

## Workflow Overview

```
docs validate (check health)
    ↓
confluence sync (push pages)
    ↓
bitbucket verify (check links)
```

## Step 1: Validate Documentation Health

Run the docs validator to check diátaxis headers, link integrity, and structure.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs validate --check-diataxis --check-links
```

Expected output:

```
[docs] Scanning: docs/agents/
[docs] Files checked: 42
[docs] Diátaxis headers: 42/42 PASS
[docs] Broken links: 0
[docs] Warnings: 2 (orphaned images)
[docs] Result: PASS
```

Run a stricter check before CI:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli docs validate --check-diataxis --check-links --fail-on-warning
```

## Step 2: Sync to Confluence

Push validated documentation to the Confluence space.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli confluence sync --source docs/agents/how-to/ --space WHO --parent-page 88722450
```

Expected output:

```
[confluence] Connected: https://confluence.digital.vn
[confluence] Pages to sync: 12
[confluence] Created: 3
[confluence] Updated: 9
[confluence] Unchanged: 0
[confluence] Errors: 0
[confluence] Sync complete
```

Sync a single guide with explicit title:

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli confluence sync --source docs/agents/how-to/first-audit-run.md \
  --space WHO --parent-page 88722450 --title "First Audit Run"
```

## Step 3: Verify Bitbucket Links

After Confluence pages are live, verify that Bitbucket repo links resolve correctly.

```bash
./scripts/worktree_uv.sh run --project vds_cli \
  vds-cli bitbucket verify-links --project vds-scripts --check-confluence-refs
```

Expected output:

```
[bitbucket] Repos scanned: 1
[bitbucket] README links: 14
[bitbucket] Confluence refs: 6
[bitbucket] Broken: 0
[bitbucket] Result: PASS
```

## CI Integration

Add the following job to `.github/workflows/docs-sync.yml`:

```yaml
  docs-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate docs
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli docs validate --check-diataxis --check-links --fail-on-warning
      - name: Sync to Confluence
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli confluence sync --source docs/agents/ --space WHO --parent-page ${{ vars.CONFLUENCE_PARENT_PAGE }}
      - name: Verify Bitbucket links
        run: |
          ./scripts/worktree_uv.sh run --project vds_cli \
            vds-cli bitbucket verify-links --project vds-scripts --check-confluence-refs
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `docs validate` fails on diátaxis | Missing `<!-- diátaxis: how-to -->` header | Add header to offending file and re-run |
| `confluence sync` auth error | Missing or expired credentials | Check `~/.vds/.env` for `VDS_USERNAME` and `VDS_PASSWORD` |
| `confluence sync` page conflict | Duplicate page title in space | Use `--title` override or delete duplicate manually |
| `bitbucket verify-links` finds broken refs | Confluence page ID changed | Update hardcoded page IDs in README or docs |
| Sync is slow | Large image attachments | Add `--skip-attachments` for text-only sync |
