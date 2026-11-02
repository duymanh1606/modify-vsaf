<!-- diátaxis: how-to -->

<!-- TODO: translate — Vietnamese translation pending -->

# Phase 131 All-Project Preparation

Use this guide when you want to prepare multiple projects for parent `workflow-projects` execution before or during bounded analysis.
For shared env/config/cache path behavior and portable cache-root conventions, see `../reference/portable-paths-and-config.md`.
When running from a dedicated `vds-scripts` worktree, prefer `./scripts/worktree_uv.sh run --project audit_orchestrator ...` over plain `uv run ...` so a different checkout's active `.venv` does not leak into the current worktree.

> **Note — interactive use vs. shell scripts**: The `uv run --project <path>` commands below are for interactive terminal or agent use from the repo root. When writing shell scripts, use `vds_uv_run_package <member>` from `scripts/vds_sh_helpers.sh` instead — see `scripts/README.md` for the canonical contract.

## What `workflow-projects` preparation does

The parent command is intentionally thin. It composes existing runtime surfaces rather than replacing them:

- `parse-registry` for project discovery when `--registry-page` is used
- `prepare` for project-scoped material preparation
- `state readiness` as the authoritative child-launch gate
- `state completeness` as a material-quality signal surfaced in parent artifacts
- child `workflow-project` for actual project analysis

Parent artifacts are derived orchestration outputs only:

- `dispatch-manifest.json`
- `dispatch-progress.state`
- `cross-project-summary.json`

Do not treat these files as a replacement for centralized readiness, completeness, evidence, or child terminal truth.

## Selection modes

### Registry-wide discovery

Use `--registry-page` when the registry page should decide project scope.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --registry-page <REGISTRY_PAGE_ID> \
  --prepare-materials \
  --max-projects-prepare-concurrent 3 \
  --max-projects-concurrent 3 \
  --max-concurrent 16
```

### Explicit project set

Use `--project-storage-keys` when you already know the exact project page IDs.

> **State prerequisite**: Projects must already be present in centralized Postgres state before `--project-storage-keys` can select them. If any key is missing, `workflow-projects` fails loudly with "missing from centralized state". For newly created Confluence pages that have not yet been parsed, run `parse-registry --registry-page <PARENT_OR_DEPARTMENT_PAGE_ID> --state-dsn env` first.

```bash
# If projects are new (Confluence-only), parse first:
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit parse-registry --registry-page <PARENT_PAGE_ID> --state-dsn env

# Then run workflow-projects with explicit keys:
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 88727304,88718940 \
  --prepare-materials \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 16
```

### Explicit checklist page when discovery fails

When the checklist page is **not a direct child of the project page** (e.g., Payment department projects where checklist page `88722450` lives at the root level), auto-discovery fails and child `workflow-project` runs fall back to targeted mode (1-3 rows) instead of the full canonical 56-row evaluation.

**Important page ID facts**:
- `88722450` — standard backend checklist page; correct for all Payment department projects. This produces a full 56-row evaluation. Confirmed bootstrap signal: `canonical_checklist_bootstrap_preflight_passed: source=explicit_page_id`
- `88716673` — Payment-specific page with topology issues (`checklist_topology_report=null`); do NOT use this as the `--checklist-page-id` value; the parser cannot extract rows from it.

Pass `--checklist-page-id` to `workflow-projects` and it is forwarded to all child runs:

```bash
# Payment department example — checklist page is at root, not under each project
# Repo-page publication defaults to the canonical project page as the hierarchy anchor.
# Omit --confluence-parent; the publisher creates the shared Project Audit node under each project page.
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 91334048,91335346 \
  --checklist-page-id 88722450 \
  --prepare-materials \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

The same flag works on `workflow-project` (single project):

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-project \
  --project-storage-key 91334048 \
  --thread-id <thread_id> \
  --checklist-page-id 88722450
```

For repo-page publication on a single Payment project, omit `--confluence-parent` in the normal case. The project page is the default hierarchy anchor; `88716694` remains the department discovery page, not the upload parent:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-project \
  --project-storage-key 91334048 \
  --thread-id <thread_id> \
  --checklist-page-id 88722450 \
  --upload-to-confluence
```

Supply `--confluence-parent` only when overriding the default project-page anchor (e.g., for a specific target page). Resolution uses three-tier fallback: explicit `--confluence-parent` → canonical project page id → `project_storage_key`.

Run-intent guidance:
- use a fresh `--thread-id` when you want a new run identity
- when the command surface supports resume-specific-run or publish-only-by-run-root, prefer that explicit selector over implicit auto-resume when reusing a known prior run

## Preparation and gating controls

### Default preparation behavior

`workflow-projects` defaults to `--prepare-materials`.

That means each selected project is prepared before child project analysis is launched. In the current runtime, parent preparation can surface preparation payload details such as readiness and completeness summaries into parent project entries.

### Skip preparation

Use `--skip-materials` only when the project set is already ready or when a resume-driven rerun should rely on current centralized state instead of re-preparing everything.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --project-storage-keys 88727304,88718940 \
  --skip-materials \
  --max-projects-concurrent 2 \
  --max-concurrent 16
```

### Strict material gate

Use `--require-all-materials` when any failed preparation/readiness result should block analysis launch for the selected scope.

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit workflow-projects \
  --registry-page <REGISTRY_PAGE_ID> \
  --prepare-materials \
  --require-all-materials \
  --max-projects-prepare-concurrent 3 \
  --max-projects-concurrent 3 \
  --max-concurrent 16
```

In strict mode, the parent run completes preparation/readiness evaluation for the selected set, records blocking projects in parent artifacts, and returns a blocked parent outcome instead of failing on the first project.

## Reading the parent artifacts

### `dispatch-manifest.json`

Use this to inspect:

- selected projects
- parent thread ID
- child thread IDs and child report roots
- preparation and execution status per project
- readiness/completeness information surfaced from preparation payloads
- pressure diagnostics such as effective preparation and analysis concurrency

### `dispatch-progress.state`

Use this for a current progress snapshot while the parent run is active.

### `cross-project-summary.json`

Use this after the run for rollup triage:

- counts by status
- project-level recovery states
- parent pressure diagnostics
- upload outcome collection
- child report locations

## Verification sequence

Before a large run, it is still safer to verify:

1. credentials and profile availability
2. project selection scope
3. preparation behavior on a small slice
4. parent artifacts and child report layout

Recommended checks:

```bash
./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only doctor profile-availability --mode active

./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only state readiness --project 88727304

./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit --json-only state completeness --project 88727304

./scripts/worktree_uv.sh run --project audit_orchestrator \
  vds-cli audit query-checklist --checklist-page 88722450 --summary-only
```

Use `query-checklist` when you need to confirm the source checklist page is parsable before a broad parent run, especially when department-level auto-discovery has already shown `checklist_discovery_failed` in earlier attempts.

## Current caveat

The historical Phase 131 parent workstream is now part of the merged mainline parent runtime. For broad all-project operation, still use bounded slices first and scale outward only after checking parent artifacts and child report layout on a smaller set.
