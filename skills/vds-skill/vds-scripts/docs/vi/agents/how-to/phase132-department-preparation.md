<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# Phase 132 Department-Wide Materials Preparation

Use this guide when preparing all actionable projects within a department before broad analysis. This guide covers the classification → investigation → re-preparation loop that ensures each project is in a known state before launching analysis.

For the multi-project execution mechanics, see [phase131-all-project-preparation.md](phase131-all-project-preparation.md).
For portable path conventions, see [../reference/portable-paths-and-config.md](../reference/portable-paths-and-config.md).

## Preparation classification model

After `prepare` runs for each project, `workflow-projects` classifies each project into:

| `materials_classification` | `blocker_class` | Meaning | Action |
|---------------------------|-----------------|---------|--------|
| `ready` | (none) | Materials complete, analysis can proceed | Automatic — enters analysis queue |
| `recoverable` | `missing_materials` | Materials incomplete, generic failure | Re-run `prepare --project <PSK>` |
| `recoverable` | `projection_lag` | State exists but readiness hasn't caught up | Re-run `state readiness --project <PSK>` |
| `recoverable` | `external_permission_block` | Bitbucket project is permission-denied | Grant access, then re-run `prepare` |
| `recoverable` | `missing_linkage` | No Bitbucket repo links found in page or state | Investigate page content or junction state |

Additionally, `quality_classification` describes material quality for `ready` projects:

| `quality_classification` | Meaning |
|--------------------------|---------|
| `high_confidence` | All material quality checks passed |
| `acceptable_with_quality_debt` | Materials present but some quality debt |
| `quality_unknown` | No quality assessment available |

## Canonical preparation sequence

```bash
# 1. Discover all child projects under a department page
vds-cli audit parse-registry --registry-page <DEPARTMENT_PAGE_ID> --state-dsn env

# 2. Prepare materials for a specific project
vds-cli audit prepare --project <PROJECT_PAGE_ID>

# 3. Verify readiness
vds-cli audit --json-only state readiness --project <PROJECT_PAGE_ID>

# 4. Run analysis (after all projects are ready)
vds-cli audit workflow-project \
  --project-storage-key <PROJECT_PAGE_ID> \
  --thread-id <THREAD_ID> \
  --checklist-page-id 88722450
```

## Department-wide preparation with classification

```bash
# Prepare all projects under a department with bounded concurrency
vds-cli audit workflow-projects \
  --registry-page <DEPARTMENT_PAGE_ID> \
  --prepare-materials \
  --max-projects-prepare-concurrent 3 \
  --max-projects-concurrent 2 \
  --max-concurrent 4 \
  --checklist-page-id 88722450
```

After preparation, inspect the `cross-project-summary.json` artifact to see each project's classification:

```bash
cat ~/.vds/cache/audit_runs/<run_dir>/cross-project-summary.json | \
  python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{p[\"project_storage_key\"]}: {p[\"materials_classification\"]} ({p.get(\"blocker_class\",\"\")}') for p in d.get('projects',[])]"
```

## Investigating blocked projects

### Permission-blocked (`external_permission_block`)

When `sync repos` cannot access a Bitbucket project:

1. Check `last_error` for the specific Bitbucket project key and error message
2. Verify the operator's Bitbucket credentials have access: `vds-cli audit doctor credentials --require-state-dsn`
3. If access was recently granted, re-run preparation for that project only:

```bash
vds-cli audit prepare --project <PROJECT_PAGE_ID>
```

The SWIT Bitbucket project is the current known reference case for permission-blocked projects.

### Missing linkage (`missing_linkage`)

When a project page has no discoverable Bitbucket repository links:

1. Use `research-skill` to investigate the Confluence page content
2. Check if junction state already has repo linkage: `vds-cli audit --json-only state readiness --project <PSK>`
3. If repos exist in Bitbucket but aren't linked from Confluence, add links to the project page and re-parse

### Projection lag (`projection_lag`)

Materials exist in state but readiness hasn't caught up:

```bash
# Re-run readiness check only (no re-preparation needed)
vds-cli audit --json-only state readiness --project <PROJECT_PAGE_ID>
```

### Missing materials (`missing_materials`)

Generic preparation failure. Re-run the full preparation:

```bash
vds-cli audit prepare --project <PROJECT_PAGE_ID>
```

## Re-preparing only the recoverable subset

After initial preparation, re-prepare only the projects that failed without re-preparing already-ready siblings:

```bash
# List the specific PSKs that failed, then target them explicitly
vds-cli audit workflow-projects \
  --project-storage-keys <PSK_1>,<PSK_2> \
  --prepare-materials \
  --checklist-page-id 88722450
```

Do NOT re-run the full department scope when only a subset needs re-preparation.

## Skill usage during preparation

| Skill | When to use |
|-------|-------------|
| `audit-orchestrator-skill` | Running preparation and analysis commands |
| `research-skill` | Investigating blockers (permission, linkage, source data) |
| `git-worktree-skill` | Isolating preparation fixes and verification |
| `spec-creation-skill` | Updating the audit-orchestrator spec after behavior changes |

## Key safety rules

- `--skip-readiness-check` is a debug-only bypass. Never use it as the normal preparation path.
- `--require-all-materials` blocks ALL analysis when any project fails. Default is `False` — siblings continue independently.
- Department page `88716694` (Payment) is the selection anchor for Payment projects. Each project resolves its own Confluence parent via FR-150 auto-resolution.
- Checklist page `88722450` is at the root level and must be passed explicitly for department pages where auto-discovery fails.

## Related guides

- [All-project preparation](phase131-all-project-preparation.md)
- [Confluence upload recovery](phase131-confluence-upload-recovery.md)
- [CLI commands reference](../reference/cli-commands.md)
