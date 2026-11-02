<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# CLI Commands

Current command surface is WHO-owned and runs from `WHO-project/vds-scripts`.
When operating from a dedicated `vds-scripts` worktree, prefer `./scripts/worktree_uv.sh ...` so a different checkout's active `.venv` does not leak into the current worktree.
`worktree_uv.sh` also bootstraps missing shared runtime env from `~/.vds/.env` (or `VDS_ENV_FILE`) and re-roots execution to the owning repo, so detached shells and tmux sessions do not depend on manual `source ~/.vds/.env`.

> **Interactive use vs. shell scripts**
>
> Commands throughout this document use `uv run --project WHO-project/vds-scripts/<package>`
> as a convenient interactive form when the caller's CWD is the monorepo root.
> **Do not copy this form into shell scripts.** Shell scripts must source
> `scripts/vds_sh_helpers.sh` and use `vds_uv_run_package <member>` instead,
> so that invocations are worktree-safe and do not encode monorepo-relative
> paths. See [`scripts/README.md`](../../scripts/README.md#uv-contract--canonical-usage)
> for the canonical script authoring contract.

## Persistent Execution

Direct CLI invocation works for quick commands (under 5 minutes). Long-running commands — `workflow`, `workflow-project`, `workflow-projects`, and `prepare` — must keep their parent process alive for the duration. When a Claude session or shell times out, the parent process exits and spawned children become orphaned, losing their state.

Use `scripts/run-audit-in-tmux.sh` to run any `vds-cli audit` command in a persistent named tmux session that survives session disconnects:

```bash
./scripts/run-audit-in-tmux.sh <name> <vds-cli audit subcommand> [args...]

# Management
./scripts/run-audit-in-tmux.sh --list
./scripts/run-audit-in-tmux.sh --status <name>
./scripts/run-audit-in-tmux.sh --attach <name>
./scripts/run-audit-in-tmux.sh --kill <name>
```

The tmux runner delegates to `./scripts/worktree_uv.sh`, so shared env bootstrap follows the same precedence contract:
- explicit CLI flags win over everything else;
- explicitly exported shell env wins over shared env file values;
- `VDS_ENV_FILE` overrides the default `~/.vds/.env` path;
- child workflow lanes still receive the resolved `--state-dsn` explicitly from the parent workflow command.

### Phase 165 Runner Scripts

Three consolidated shell runners provide operator-level convenience for common audit patterns.

#### Single Project Audit

```bash
# Auto-resolve checklist from state, launch in tmux
./scripts/run-project-audit.sh 88718977

# Override checklist, limit concurrency
./scripts/run-project-audit.sh 88718977 --checklist-page-id 88722450 --max-concurrent 4

# Single repo within a project
./scripts/run-project-audit.sh 88718977 --scope-id <scope-id> --upload-to-confluence

# Resume a previous run
./scripts/run-project-audit.sh 88718977 --resume

# Dry run to inspect the generated command
./scripts/run-project-audit.sh 88718977 --dry-run
```

#### Department-Wide Evaluation

```bash
# Discover all projects in a department, launch bounded parent session
./scripts/run-department-audit.sh 88716694 --checklist-page-id 88722450

# Filter to specific projects
./scripts/run-department-audit.sh 88716694 --project-filter 88718977,88718943

# Exclude a project
./scripts/run-department-audit.sh 88716694 --project-exclude 91335346

# Dry run
./scripts/run-department-audit.sh 88716694 --dry-run
```

#### Monitoring and Management

```bash
# Unified dashboard across all active sessions
./scripts/audit-dashboard.sh

# Continuous refresh every 10 seconds
./scripts/audit-dashboard.sh --watch

# Filter to a department
./scripts/audit-dashboard.sh --department payment

# Machine-readable JSON output
./scripts/audit-dashboard.sh --json

# List / kill sessions
./scripts/run-project-audit.sh --list
./scripts/run-department-audit.sh --kill payment
```

#### Continuation Modes

| Intent | Command |
|--------|---------|
| Fresh evaluation | `./scripts/run-project-audit.sh <key>` (default: `--new-run`) |
| Resume interrupted run | `./scripts/run-project-audit.sh <key> --resume` |
| Publish completed results | `vds-cli audit publish-project-run --resume-run <thread_id> --upload-to-confluence` |

The shell runners are operator convenience wrappers. `workflow-project` and `workflow-projects` remain the canonical Python CLI execution surfaces.

## Key Commands

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli progress --help`

## Direct executable naming notes

Always use `vds-cli <service> --help` for discovery. Direct executables are internal router implementation detail.
Current verified direct names include:

- `vds-cli git-orchestrator`
- `vds-cli schema-convert`
- `vds-cli diagrams`
- `vds-cli google-sheets`
- `vds-cli jira-cli`
- `vds-cli mcp-server`
- `vds-cli progress` (PR review)
- `vds-cli progress`

Use `vds-scripts-skill` as the platform-routing skill for choosing the right command family. Use specialist skills such as `audit-orchestrator-skill` when you need deep workflow guidance.
Default workflow-generated report artifacts live under the effective VDS cache root, typically `<cache-root>/audit_runs`, unless overridden by `VDS_AUDIT_REPORT_DIR` or an explicit `--report-dir`.
See `portable-paths-and-config.md` for the cross-platform path and precedence model.
See `cli-help-matrix.md` for the verified routed command inventory.

## Page Identity

Current audit runtime uses a strict page-identity model:

- `registry/root page` is for discovery. Use it with `parse-registry`, `extract-docs --registry-page`, and `workflow-projects --registry-page`.
- `department page` is typically a parent page that groups multiple project pages. It may have cached page materials, but it is not automatically a canonical audit project. When `parse-registry` starts from a department page, the emitted project rows must keep that page as `department_page` and keep the nearest recovered parent container/root as `root_page`.
- `project page` is the canonical project identity. `project_storage_key` must be the numeric Confluence `page_id` for that project page.
- `checklist page` is a child page used by workflow execution and may need to be passed explicitly if automatic checklist discovery fails.

Operational implications:

- `vds-cli audit state readiness --project <ID>` expects a canonical project page ID already present in centralized state.
- A department/root page can exist in materials cache and still fail `state readiness` lookup. That is page extraction only, not project preparation.
- If you want to prepare or run multiple child projects under one parent page, target that parent as a registry/root input and let root-scoped selection resolve only canonical child project pages with valid `department_page_id`, valid `root_page_id`, and non-`unassigned:*` department assignment.
- `parse-registry` output should preserve additive page objects, not only scalar ids: `project_page`, `department_page`, and `root_page` should all be present whenever lineage is available.
- Generic manifest/state reconstruction may preserve merge-companion rows for reuse, but root-scoped consumer filtering must exclude rows missing valid hierarchy lineage for the selected root.
- Warnings like `No checklist page was discovered among root children` usually indicate that a parent page was targeted directly without first resolving the child project page or explicit checklist page.

## Canonical Preparation Guard

Normal analysis should keep readiness enabled. Use this sequence:

1. Discovery + persist to Postgres (requires `--state-dsn env`):
   `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit parse-registry --registry-page <PROJECT_OR_DEPARTMENT_OR_ROOT_PAGE> --state-dsn env`

   > **Critical**: Without `--state-dsn env`, `parse-registry` only outputs JSON and does NOT save discovered projects to the Postgres state backend. Omitting this flag means `prepare` and `state readiness` will not find the projects.

2. Materials preparation:
   `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit prepare --project <PROJECT_PAGE_ID>`
3. Readiness proof:
   `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --json-only state readiness --project <PROJECT_PAGE_ID> [--repo <REPO_STORAGE_KEY_OR_SLUG>]`
4. Analysis:
   `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow <REPO_PATH> --project-storage-key <PROJECT_PAGE_ID> --thread-id <THREAD_ID>`
   (Full canonical 56-row evaluation is the default. Use `--target row-1` or another selector verified through `query-checklist` for specific rows. Use `--no-canonical-checklist` only to opt out — this produces incomplete reports.)

   When checklist auto-discovery fails (i.e. the checklist page is not a direct child of the project page), add `--checklist-page-id` to restore full canonical evaluation. For Payment department projects, the verified working command is:
   `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow <REPO_PATH> --project-storage-key <PROJECT_PAGE_ID> --checklist-page-id 88722450 --thread-id <THREAD_ID>`
   Confirmed bootstrap signal: `canonical_checklist_bootstrap_preflight_passed: source=explicit_page_id`

Guard rules:

- `workflow` and `workflow-project` should fail loudly when canonical materials are not ready.
- `--skip-readiness-check` is debug-only and should not be used for normal agent analysis.
- If you start from a department/root page, resolve child project pages first, then prepare and run analysis per project.

Current provider launch-readiness commands:
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --json-only doctor profile-availability --mode active`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --json-only doctor profile-availability --profiles zai-openai --mode active`

## Live Debug Logging

- Root CLI realtime JSONL logs are on by default through `--realtime-logs`.
- Debug-oriented workflow lanes now auto-elevate richer agent event logging when the operator already signals debugging with `--target`, root `--verbose`, `--trace`, `--debug-evidence-context`, or `--debug-batch-timing`.
- Since Phase 155, `--debug-evidence-context`, `--debug-batch-timing`, and `--trace` are accepted by `workflow-project` and forwarded to child `workflow` lanes. They are still NOT accepted by `workflow-projects` directly.
- `--target` and `--offline` are accepted by all three workflow commands.
- `--verbose` is a root-level flag: `vds-cli audit --verbose workflow ...` — not a per-subcommand flag.
- Text-delta event logging is enabled for those debug lanes so long prompt-agent waits stay visible in live logs.
- Full payload trace logging remains a heavier mode and is auto-enabled only for `--trace`, `--debug-evidence-context`, or `--debug-batch-timing`.

Current Confluence connectivity commands:
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit doctor check-confluence --json`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search -s internal -q 'type=page' --limit 2 --json`

Current Confluence operator notes:
- Checklist-heavy reads default to the internal server because that is where the authoritative checklist pages live.
- Override checklist-read routing only when needed: `VDS_AUDIT_CHECKLIST_READ_SERVER=external`.
- `VDS_AUDIT_CHECKLIST_READ_TIMEOUT` defaults to 60 seconds for checklist-heavy reads.
- Runtime operations stay on the selected Confluence base URL. Use `doctor check-confluence` to inspect other configured URLs explicitly; do not assume implicit failover between them.
- `VDS_AUDIT_SKIP_EVIDENCE_CHECK=1` — bypasses the security evidence preflight check. On `workflow`, pass the flag directly or set the env var; child `workflow` processes spawned by `workflow-project` inherit this via subprocess propagation when set in the parent environment.
- `VDS_AUDIT_STATE_API_TIMEOUT_SECONDS=120` — raise from the default (15 s) when running concurrent child workflows that simultaneously load the state manifest. Set in `~/.vds/.env`.
- If multiple endpoint labels point at the same exact base URL, `doctor check-confluence` reuses one exact-URL probe result so duplicate aliases do not report contradictory status.
- `doctor check-confluence` uses a 30 second probe timeout per endpoint to accommodate the current internal Confluence latency envelope.
- `workflow` and `workflow-project` use the same 30 second startup probe budget before auto-activating offline mode, so slow-but-reachable internal Confluence does not get marked unreachable earlier than the doctor surface.
- Parent project dispatch should pass the resolved `--state-dsn` into child `workflow` subprocesses explicitly. Environment inheritance may still work, but explicit pass-through keeps child lanes pinned to the same centralized state backend the parent already resolved.
- Probe failures stay in the structured doctor output and do not emit warning-level Confluence transport logs during the diagnostic command itself.

Current checklist inspection command surface:
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist --checklist-page 88722450 --summary-only`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist --checklist-page 88722450 --target row-1`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist --checklist-page 88722450 --target chk_1`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit query-checklist --project-storage-key 88727304 --checklist-profile default --summary-only`

Use `query-checklist` when you need to inspect source checklist rows directly without launching workflow evaluation. It accepts an explicit checklist page or can bootstrap from a project storage key plus checklist profile.
For source-checklist pages, derive operator-facing `--target` selectors from `query-checklist` output itself. Prefer numeric row selectors (`1`) or row ids (`row-1`) for a unique row. Parser check ids (`chk_1`) are valid but may repeat across sections on the same checklist page. Do not copy `dispatch-manifest.json` internal `explicit:<page>:...` payloads into `workflow --target` or `query-checklist --target`; those are internal dispatch row-key bundles, not CLI selector forms.

Current Phase 131 multi-project command surface (initial landed runtime):
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-projects --registry-page <REGISTRY_PAGE_ID> --prepare-materials --max-projects-prepare-concurrent 3 --max-projects-concurrent 3 --max-concurrent 16`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-projects --project-storage-keys 88727304,88718940 --profiles zai-openai --profile-availability active --max-projects-concurrent 2 --max-concurrent 16`
- With explicit checklist page for department-level projects where checklist auto-discovery fails: `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-projects --project-storage-keys 91334048,91335346 --checklist-page-id 88722450 --prepare-materials --max-projects-concurrent 2 --max-concurrent 4`

> **`--checklist-page-id` is required when running from department or registry pages**: When `workflow-project` or `workflow-projects` is invoked against a project whose checklist page is not a direct child of that project page, auto-discovery fails and evaluation falls back to targeted mode (1-3 rows) instead of the full canonical 56-row run. Pass `--checklist-page-id <CHECKLIST_PAGE_ID>` explicitly to restore full canonical evaluation. For Payment department projects, the checklist page is `88722450` — it lives at the root level, not under each child project.

> **Prerequisite for `--project-storage-keys`**: Projects must already be present in centralized Postgres state before `workflow-projects --project-storage-keys` can select them. If any requested key is missing, `workflow-projects` will fail loudly with "missing from centralized state". Run `parse-registry --registry-page <PAGE_ID> --state-dsn env` first to discover and persist new projects.

Current hardening notes for explicit project selection and parent identity:
- Parent multi-project selection now treats canonical numeric Confluence `page_id` as authoritative project identity when available, even if centralized state still carries a legacy slug-style `project_storage_key` for the same project.
- When any explicitly requested project key is missing from the current centralized state selection payload, `workflow-projects` now fails loudly instead of silently truncating the project set.
- Parent manifest entries, child thread IDs, and child report directories are being hardened toward canonical numeric project identity.

Phase 131 current runtime guidance:
- Parent preparation parallelism and parent analysis parallelism are separate controls in the current Phase 131 design and runtime surface. Do not describe either one as merely a synonym for child `workflow-project --max-concurrent`.
- `workflow-projects` is a thin parent command that orchestrates `parse-registry`, `prepare`, readiness/completeness checks, and child `workflow-project` launches; it does not replace child project execution semantics.
- Parent recovery classifies project outcomes such as `completed`, `failed`, `timed_out`, `exception`, `provider_blocked`, and `upload_failed`, while child runtime truth remains in child artifacts and centralized state.
- Parent Confluence behavior in Phase 131 is pass-through only: successful child `workflow-project` runs still own repo uploads and project aggregate uploads, and parent artifacts only collect upload outcomes for monitoring and recovery planning.
- Parent manifest and progress-state files are derived orchestration artifacts for monitoring and resume scoping only. Readiness, completeness, provider launch gating, and final child workflow truth still come from authoritative runtime checks and child artifacts.
- Treat the current `workflow-projects` surface as an initial landed runtime for hardening and bounded verification. Do not present it as closure-grade for full live all-project production use until the remaining runtime hardening and live verification work are complete.
- A current known hardening area is mixed state snapshots where some projects still carry legacy slug-style `project_storage_key` values; parent orchestration must normalize these to numeric page identity before explicit project selection, child thread derivation, and child report-root creation.
- Another current hardening area is child zero-result dispatch handling: when all repo jobs fail and produce no mergeable outputs, the child workflow should terminate with a controlled failure summary rather than a misleading merge-input usage error.

## Phase 124 Closure Pack

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec validate audit-orchestrator`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec check-alignment audit-orchestrator`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec consolidate audit-orchestrator`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec validate-sync audit-orchestrator --agents-file AGENTS.md --agents-label "Audit orchestrator" --json-only`
- `python3 WHO-project/vds-scripts/audit_orchestrator/scripts/verify_phase124_handoff.py --output-json reports/verification/phase124/command-pack.json`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit publish-system-doc --help`

The audit-orchestrator package still exposes `validate-spec-sync` for compatibility, but the shared `vds-cli spec validate-sync` gate is the preferred sync command after the WHO migration.

## Targeted Workflow Reruns

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --profile zai-openai workflow <repo-cache-root>/PAR-project/merchant-report --project-storage-key 88727304 --thread-id phase124-row2-par-mr-zai --target row-2`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-project --project-storage-key 88727304 --thread-id <thread_id>`
- With explicit checklist page (required when checklist auto-discovery fails from a department/project page): `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit workflow-project --project-storage-key 88727304 --thread-id <thread_id> --checklist-page-id 88722450`

Current Phase 130 live verification also validated a narrow control-aware security preflight exception for `CL-014`, `CL-042`, `CL-051`, `CL-052`, and `CL-053` when code anchors are present but current indexed docs do not provide document anchors. The machine-readable preflight payload records this as `code_anchor_exception_applied=true`.

For single-row `workflow` reruns, use `--target <CHECK_ID_OR_ROW_SELECTOR>` (canonical mode stays on by default). Do not use unsupported legacy selectors such as `--check-ids` or `--targeted-rows`.

Current default project posture is default-all profile resolution plus bounded top-level repo dispatch. Omit `--profiles` to use all configured available profiles. The intended high-parallel behavior is that each child repo workflow exploits the full resolved profile pool internally, while the project command keeps one child repo workflow per repo by default and keeps outer repo-job fan-out explicit with `--max-concurrent`.

Current phase distinction:
- merged mainline runtime baseline is Phase 169 complete;
- canonical latest spec is v21.0.0 with Phase 171 merged;
- keep operator guidance aligned to the merged Phase 171 baseline, which incorporates gradual dispatch ramp-up (`--ramp-up-slots`, `--ramp-up-interval`, stagger 200ms default), Phase 170 schema contract hardening (`_DISPATCH_SCHEMA_CONTRACT`, `dispatch_schema_gate()`, safe `claimed_at` repair, `doctor schema`), Phase 169 dispatch observability (heartbeat, utilization, progress summaries, dead-run detection), Phase 168 finalization reliability, and Phase 167 dispatch optimization.

Verified one-repo project-scoped pattern:

```bash
./scripts/run-audit-in-tmux.sh core-transfer-swit-all-profiles \
  workflow-project \
  --project-storage-key 88718975 \
  --scope-id <scope-id-from-parse-repo> \
  --checklist-page-id 88722450 \
  --max-concurrent 16 \
  --upload-to-confluence \
  --incremental-upload \
  --new-run
```

Operational interpretation:
- Prefer `--scope-id` from `parse-repo` to narrow `workflow-project` to one prepared repo while keeping project semantics, upload hierarchy, and aggregate generation.
- Existing `--seed-payload` JSON remains a compatibility surface only and emits deprecation warnings on the current merged mainline baseline.
- Omit `--profiles` when you want the runtime to resolve the current active profile pool automatically. This is the correct syntax for "all available profiles".
- `--max-concurrent` limits the number of active child lanes at once. It does not mean only that many total profiles participate; queued lanes still run later if more profiles are available.
- Use DB dispatch surfaces such as `dispatch_runs`, `dispatch_lanes`, and `doctor dispatch-status` as the authoritative record of which profiles were available, excluded, and completed for the run. `dispatch-manifest.json` and `dispatch-progress.state` are debug artifacts when present.
- Phase 156 publication hardening now re-parents reused Confluence pages, skips cross-project page-id collisions during registry backfill, and strips `--incremental-upload` whenever upload is disabled by offline mode.
- Mainline also includes post-158 hardening for row-sharded merge isolation and Confluence page-creation race defense, plus Phase 161 hardening for manual verification isolation, PDF test-surface recovery, bounded runtime hardening, and Confluence SDK call minimization. Full Phase 159 work-stealing flags remain planned, not live.

For multi-project execution, keep the distinction explicit in docs and runbooks: `workflow-projects` is now the merged parent runtime command surface for Phase 131, and it separates maximum-parallel project preparation from maximum-parallel project analysis. Docs and runbooks should call out both parent-stage concurrency lanes when describing the Phase 131 path.

## Common CLI Mistakes

| Mistake | Correct usage |
|---------|--------------|
| `--no-upload-attachments` does not exist | Use `--upload-attachments` (opt-in flag). Omitting it is the default — attachments are skipped unless this flag is explicitly passed. |
| `--upload-to-confluence` without `--confluence-parent` | Valid normal path. Repo-page publication defaults to the canonical project page as the hierarchy anchor; the publisher then creates one shared `Project Audit - <project name> (<page id>)` node under that project page. Use `--confluence-parent <page_id>` only when you need to override the anchor manually. |
| Using department page `88716694` as the repo-page upload parent for Payment projects | `88716694` is the department discovery/selection page, not the normal repo-page publication parent. Doing so would place project audit pages under the department page instead of under each canonical project page. Let the default project-page anchor behavior create the shared project audit node beneath each Payment project page. |
| `--page-url` on `parse-registry` | The correct flag is `--registry-page <page_id>`. `--page-url` does not exist for this command. |
| `parse-registry` without `--state-dsn` | Without `--state-dsn env`, parse-registry only outputs JSON and does NOT persist discovered projects to Postgres. Downstream `prepare` and `state readiness` commands will not find the projects. Always use: `vds-cli audit parse-registry --registry-page <PAGE_ID> --state-dsn env` |
| `workflow-projects --project-storage-keys` before `parse-registry` | `--project-storage-keys` requires projects already present in centralized Postgres state. New Confluence-only projects must be discovered first: `vds-cli audit parse-registry --registry-page <PAGE_ID> --state-dsn env`. Without this, the command fails with "missing from centralized state". |
| `prepare` shows `checklist_discovery_failed` | Automatic checklist discovery expects the checklist page to be a direct child of the project page. When it is not, pass `--checklist-page-id <CHECKLIST_PAGE_ID>` explicitly to `prepare`. For Payment department projects, use `88722450`, not `88716673`. Example: `vds-cli audit prepare --project <PROJECT_PAGE_ID> --checklist-page-id 88722450` |
| `workflow-project` runs only 1-3 targeted rows instead of full 56-row canonical | Checklist discovery failed — the checklist page is not under the project page. Pass `--checklist-page-id <CHECKLIST_PAGE_ID>` to restore full canonical evaluation. For Payment department: `--checklist-page-id 88722450`. The flag is passed through to all child repo workflow runs. |
| `workflow-projects` child runs are targeted (1-3 rows) instead of full canonical | Same root cause. Pass `--checklist-page-id <CHECKLIST_PAGE_ID>` to `workflow-projects` and it is forwarded to all child `workflow-project` runs. Example for Payment department: `--checklist-page-id 88722450`. |
| Implicit auto-resume reused an older run when you wanted a fresh run | Use a fresh thread id and explicit new-run intent when available. When reusing a known prior run, prefer explicit resume-specific-run or publish-from-run-root surfaces instead of relying on auto-selected resumable artifacts. |
| Using `--no-canonical-checklist` on `workflow` | Produces incomplete reports — full canonical 56-row evaluation is the DEFAULT since Phase 133. Use `--target row-1` or another selector verified through `query-checklist` for specific rows within canonical mode. Only use `--no-canonical-checklist` to explicitly opt out, knowing reports will be incomplete. |
| Need to inspect checklist rows without running a workflow | Use `vds-cli audit query-checklist`. Example: `vds-cli audit query-checklist --checklist-page 88722450 --summary-only` or `--target row-1`. Use `chk_1` only if you want every source row that shares that parser-local check id. |
| `workflow-project ... --skip-readiness-check` | `--skip-readiness-check` is on `workflow` (single-repo) only. Use `--offline` on `workflow-project` to bypass readiness gating in degraded Confluence scenarios. |
| `workflow <repo> ... --max-concurrent N` | `--max-concurrent` is on `workflow-project` and `workflow-projects` only. The single-repo `workflow` command has no outer concurrency control — it evaluates one repo's rows with `--row-concurrency`. |
| `workflow-project ... --max-concurrent 16` means "only 16 profiles are used" | Incorrect. It caps simultaneous active lanes only. In row-sharded runs, more than 16 profiles can still participate over the lifetime of the run as earlier lanes finish and queued lanes start. |
| Listing every profile manually to mean "all available profiles" | Prefer omitting `--profiles`. Explicit lists go stale and can include providers that active preflight will exclude for cooldown or availability reasons. |
| `workflow-project` single-repo rerun without `--scope-id` | `workflow-project` has no direct `--repo` flag. Prefer `--scope-id <id>` from `parse-repo` for one prepared repo. Use `--seed-payload` only when you must consume an existing compatibility JSON payload. |
| `workflow <repo> ... --new-run` | `--new-run` is on `workflow-project` only. For `workflow`, use a fresh `--thread-id` to start a new run. |
| `workflow <repo> ... --resume-run` | `--resume-run` is on `workflow-project` only. For `workflow`, use `--resume` with an existing thread/report dir. |
| `workflow <repo> --verbose ...` or `workflow-project --verbose ...` | `--verbose` is a root-level flag that must come before the subcommand: `vds-cli audit --verbose workflow <repo> ...` or `vds-cli audit --verbose workflow-project ...`. |
| `workflow-projects ... --skip-readiness-check` | `--skip-readiness-check` is on `workflow` only. `workflow-projects` has no equivalent — use `--skip-materials` to skip preparation, which also avoids re-running readiness. |
| `workflow-projects ... --debug-evidence-context` | `--debug-evidence-context` is available on `workflow` and `workflow-project`, but not on `workflow-projects`. Put it on the child `workflow-project` invocation instead. |

## Payment Department

Department page ID: `88716694`. Used with `parse-registry --registry-page 88716694` to discover child projects.

New child projects (e.g., `91334048`, `91335346`) exist only on Confluence until `parse-registry --state-dsn env` is run. Running `workflow-projects --project-storage-keys 91334048,91335346` before that step will fail with "missing from centralized state".

Correct sequence for new Payment department projects:

```bash
# Step 1: Discover all child projects under the department page and persist to Postgres
vds-cli audit parse-registry --registry-page 88716694 --state-dsn env

# Step 2: Prepare materials for a specific child project
vds-cli audit prepare --project <CHILD_PROJECT_PAGE_ID>
# If checklist_discovery_failed, add explicit checklist page (use 88722450, not 88716673):
# vds-cli audit prepare --project <CHILD_PROJECT_PAGE_ID> --checklist-page-id 88722450
# Note: page 88716673 has topology issues (checklist_topology_report=null); 88722450 is the correct page.

# Step 3: Verify readiness
vds-cli audit --json-only state readiness --project <CHILD_PROJECT_PAGE_ID>

# Step 4: Run workflow
# --checklist-page-id is required: the checklist page 88722450 is at the root level,
# not a direct child of each project page, so auto-discovery fails without it.
# Without this flag, evaluation falls back to targeted (1-3 rows) instead of full canonical (56 rows).
vds-cli audit workflow-project --project-storage-key <CHILD_PROJECT_PAGE_ID> --thread-id <thread_id> --checklist-page-id 88722450
```

For multi-project execution across the department after parse-registry has run:

```bash
vds-cli audit workflow-projects \
  --project-storage-keys 91334048,91335346 \
  --checklist-page-id 88722450 \
  --prepare-materials \
  --max-projects-prepare-concurrent 2 \
  --max-projects-concurrent 2 \
  --max-concurrent 4
```

Important publication note:
- department page `88716694` is the selection and discovery anchor for Payment projects
- omit `--confluence-parent` in normal runs — repo-page publication defaults to the canonical project page as the hierarchy anchor
- the shared `Project Audit - <project name> (<page id>)` node is created under that project page, and repo report pages are created as its direct children
- do NOT supply `--confluence-parent 88716694` as a global override for Payment publication; `88716694` is the department discovery page, not the normal repo-page parent

Run-intent note:
- use a fresh thread id for a new run
- prefer explicit resume-specific-run or publish-from-run-root behavior when reusing a known prior run, rather than relying on implicit auto-resume

## PDF Report Generation (Phase 148)

Generate offline PDF audit reports from existing run artifacts (no network required).

```bash
# Repo-scope PDF
vds-cli audit generate-pdf repo ~/.vds/cache/audit_runs/<run_dir>

# Project-scope PDF (aggregates all repo run dirs)
vds-cli audit generate-pdf project ~/.vds/cache/audit_runs/<project_run_dir> --project-key MY_PROJECT

# Department-scope PDF (aggregates across projects)
vds-cli audit generate-pdf department ~/.vds/cache/audit_runs/ --department-name "My Department"

# Output to specific path; open after generation
vds-cli audit generate-pdf repo <run_dir> --output /tmp/report.pdf --open

# JSON-only output (for scripting)
vds-cli audit generate-pdf repo <run_dir> --json-only
```

All three subcommands accept `--output <path>`, `--open`, and `--json-only`. Exit codes: `0` = success, `1` = generation failed, `2` = artifact not found.

Workflow integration: `workflow` and `workflow-project` generate a PDF report by default after every successful evaluation. Pass `--no-generate-pdf` to disable. The parent-level `--json-only` flag propagates to all `generate-pdf` subcommands, so both `vds-cli audit --json-only generate-pdf repo ...` and `vds-cli audit generate-pdf repo ... --json-only` work.

## Related Guides

- [Scripts workspace guide](../../README.md)
- [VDS CLI reference](vds-cli-reference.md)
- [Audit orchestrator guide](../../../audit_orchestrator/README.md)
