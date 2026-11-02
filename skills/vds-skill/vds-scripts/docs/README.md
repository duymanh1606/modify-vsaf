# VDS Scripts Documentation

Centralized reference for the Python orchestration stack (git/jira/confluence/bitbucket/vds_cli/mcp_server, markdown tools, docker). Use this single README for all operational guidance.

---

## 1. Quick Start

For the canonical human + AI-agent install/bootstrap workflow, start with `docs/agents/how-to/install-and-bootstrap-who-scripts-and-skills.md`.
Use the steps below as the scripts-workspace quick start after that canonical bootstrap path is understood.

1. **Install uv**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Bootstrap all projects**
   ```bash
   cd vds-scripts
   ./scripts/bootstrap_uv.sh --frozen
   ```
3. **Verify credentials + health**
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli status
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
   ```
   If `vds-cli` fails with `ModuleNotFoundError: vds_cli`, run:
   ```bash
   uv --project vds_cli sync --no-editable
   ```
4. **Sample operations**
   ```bash
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --project insurance
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --limit 5
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content search "space = TDOV" --limit 5
   ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects
   ```

**Environment:** Store shared credentials in `VDS_ENV_FILE` or `<config-root>/.env`.
`<config-root>` resolves from `VDS_CONFIG_DIR` when set,
otherwise from the friendly user-home VDS default (`~/.vds` on Unix-like systems).
All `vds-scripts` CLIs auto-load the shared env file via `vds_cli_common`.
If a variable is already set in the shell, it takes precedence over values loaded from `.env`.
Use `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status` to confirm.
See `docs/agents/reference/portable-paths-and-config.md` for the full precedence and path model.
If you update shared packages (e.g., `vds_cli_common`), re-sync the affected project:
`uv sync --project <orchestrator> --reinstall`.

---

## 2. Documentation Map (Diátaxis)

- **Tutorials (learning by doing)**:
  - Use **section 1 Quick Start** on this page to bootstrap uv, sync projects, and run first commands.
  - Follow the environment setup workflow in `AGENTS.md` §2.1–2.3 for an end‑to‑end walkthrough.
- **How‑To guides (task recipes)**:
  - **CLI Reference** (section 3 below) – copy/pasteable commands for common tasks (git, Jira, Confluence, Bitbucket, PDF).
  - Git orchestrator examples in `vds-scripts/git_orchestrator/README.md`.
  - Diagram generation flows in `vds-scripts/diagram_generator/README.md`.
- **Reference (API/command surface)**:
  - Atlassian Features Matrix (section 4) – what each orchestrator supports and the exact subcommands.
  - Individual orchestrator READMEs (`jira_orchestrator/README.md`, `confluence_orchestrator/README.md`, `bitbucket_orchestrator/README.md`).
- **Explanation (architecture & rationale)**:
  - Migration & Architecture Snapshot (section 2) – why `vds-scripts/` exists and how components fit together.
  - Bitbucket orchestrator architecture / practices docs under `bitbucket_orchestrator/`.

For **AI agents**, use this file as the primary operational reference and `AGENTS.md` as the higher‑level policy and workflow guide.

---

## 3. Migration & Architecture Snapshot

- **Cutover Date:** 2025‑11‑26 – `docs-nttc/scripts/*` replaced by this repo.
- **Included Components:** `git_orchestrator`, `jira_orchestrator`, `confluence_orchestrator`, `bitbucket_orchestrator`, `vds_cli`, `mcp_server`, `markdown_orchestrator`, `diagram_generator`, `docker`.
- **Rollback (reference only):** restore `split/vds-scripts` branch inside monorepo if needed.
- **Shared Assets:** `repo-manifest.yaml` now lives in repo root; default path updated in git orchestrator.
- **Standards:** All packages use `pyproject.toml`, `uv.lock`, Ruff, pytest, `atlassian-python-api v4.0.7`.

---

## 4. CLI Reference

| Task | Command |
| --- | --- |
| Check env / status | `./scripts/worktree_uv.sh run --project vds_cli vds-cli env status` • `./scripts/worktree_uv.sh run --project vds_cli vds-cli status` |
| Regenerate manifest | `./scripts/worktree_uv.sh run --project vds_cli vds-cli regenerate-manifest` (add `--dry-run` to preview) |
| Git pull/status (manifest-aware) | `./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --project lep` • `... git status --match "*notification*"` |
| Branch lifecycle | `./scripts/worktree_uv.sh run --project vds_cli vds-cli git branch list --project insurance` |
| Jira operations | `./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "<JQL>" --limit 20` • `... jira session create` |
| Confluence | `./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence content page <ID> --server external --expand body.storage` |
| Bitbucket | `./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories INSURANCE` |
| Elastic | `./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic ping` |
| Grafana | `./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana health` |
| Hooks / Markdown lint | `./scripts/worktree_uv.sh run --project markdown_orchestrator python -m vds_markdown_orchestrator.cli lint` |

> **Tip:** `./scripts/worktree_uv.sh run --project vds_cli vds-cli --help` and `... <service> --help` expose all flags. Use `--json-only` for machine-readable output or `--no-reports` to skip report files.

Git commands automatically attempt to regenerate `vds-scripts/repo-manifest.yaml` from Bitbucket (LEP/INSURANCE/SAVING/EKYC)
before running the underlying git orchestrator. To disable this behavior (for example, when offline), set
`VDS_GIT_AUTO_REGENERATE_MANIFEST=0` (or `false`/`off`) in your shell environment before invoking `vds-cli git ...`.

## 4.1 Smoke Matrix (2026-02-06)

Run from `WHO-project/vds-scripts`:

```bash
# Unified CLI + live credentialed checks
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "assignee = currentUser() ORDER BY updated DESC" --limit 1
./scripts/worktree_uv.sh run --project jira_orchestrator vds-cli jira search "assignee = currentUser() ORDER BY updated DESC" --limit 1 --json-only
./scripts/worktree_uv.sh run --project vds_cli vds-cli confluence search --cql "type=page" --limit 1
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects

# Service-specific live checks
./scripts/worktree_uv.sh run --project vds_cli vds-cli elastic ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli grafana health
./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube ping
./scripts/worktree_uv.sh run --project vds_cli vds-cli pdf -- version
```

Notes:
- `vds-cli` routes all orchestrators after loading shared environment variables.
- Router integrity is validated against each orchestrator's `[project.scripts]` declaration and target source module to prevent stale entrypoint drift.

---

## 5. Atlassian Features Matrix

| Service | Feature | Command / Notes |
| --- | --- | --- |
| Jira | Search / filters | `vds-cli jira search "<JQL>" --limit N` (enhanced JQL on cloud) |
| Jira | Issue details & transitions | `vds-cli jira issue <KEY>` • `jira transition <KEY> --status Done` |
| Jira | Sessions | `jira session create/status/destroy` (reduces auth overhead) |
| Confluence | CQL search & page read | `confluence content search "<CQL>"` • `confluence content page <ID>` |
| Confluence | Attachments | `confluence content attachments sync --page-id ...` (built-in retry) |
| Bitbucket | Projects/repos | `bitbucket projects` • `bitbucket repositories <PROJECT>` |
| Bitbucket | Pull requests | `bitbucket pull-requests <PROJECT> <REPO>` (approve/comment/block) |
| Git orchestration | Multi-repo ops | `git clone/pull/fetch/status/list/branch/checkout/add/commit/push/log/diff/stash/tag/remote` with `--project/--match/--tag` filters |

All commands honor the shared manifest and emit JSON reports under `reports/<service>/YYYY/MM/DD/`.

---

## 6. Docker & Deployment

```bash
cd vds-scripts/docker
cp env.example .env   # if provided
docker compose up -d
docker compose logs -f
docker compose down
```

- Services: MCP server (FastMCP) + Redis.
- Rebuild image: `docker compose build --no-cache mcp-server`.
- Phase 2 Ubuntu portability verification: `./scripts/verification/phase2_portable_paths_ubuntu_docker.sh` (supported entrypoint; uses `docker/compose.phase2-verification.yml` underneath)
- Run smoke tests inside container:
  ```bash
  docker compose exec mcp-server ./scripts/worktree_uv.sh run --project vds_cli vds-cli status
  docker compose exec mcp-server uv run --project mcp_server pytest tests/unit -q
  ```

### 6.1 Offline Deployment (Air-Gapped)

- Procedure: `docs/deployment/offline-docker-image-load.md`
- Loader script: `scripts/deployment/load_docker_images_offline.sh`
- Example:
  ```bash
  ./scripts/deployment/load_docker_images_offline.sh --images-dir /opt/vds/images
  ```

---

## 7. Monitoring (T7) Log

| Date | Env | CLI | Jira | Confluence | Bitbucket | Git | Docker | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025‑11‑26 | | | | | | | | |
| 2025‑11‑27 | | | | | | | | |
| 2025‑11‑28 | | | | | | | | |
| 2025‑11‑29 | | | | | | | | |
| 2025‑11‑30 | | | | | | | | |
| 2025‑12‑01 | | | | | | | | |
| 2025‑12‑02 | | | | | | | | |
| 2025‑12‑03 | | | | | | | | |
| 2025‑12‑04 | | | | | | | | |
| 2025‑12‑05 | | | | | | | | |
| 2025‑12‑06 | | | | | | | | |
| 2025‑12‑07 | | | | | | | | |
| 2025‑12‑08 | | | | | | | | |
| 2025‑12‑09 | | | | | | | | |
| 2025‑12‑10 | | | | | | | | |

- Daily steps: env status → CLI status → Jira/Confluence/Bitbucket/Git smoke → docker uptime.
- Log incidents in the table above or issue tracker with captured `reports/verification/*` artifacts.
- Exit criteria: 14 consecutive successful days + no unresolved incidents >72h + final summary circulated.

---

## 8. Deployment Task Tracker

| ID | Description | Owner | Status | Notes |
| --- | --- | --- | --- | --- |
| T1 | Dependency matrix | Platform Core | ✅ | Logged in `vds-scripts.md` |
| T2 | Filter repo & push | DevOps | ✅ | Tag `v1.0.0-pre` |
| T3 | Document uv/bootstrap | Python Guild | ✅ | `scripts/bootstrap_uv.sh` |
| T4 | Update documentation links | Docs Team | ✅ | AGENTS + README updated |
| T5 | Verification (lint/tests/smoke) | QA Automation | ✅ | Evidence under `reports/verification/` |
| T6 | Cutover & announcement | Release Eng | ✅ | Completed 2025‑11‑26 |
| T7 | Post-cutover monitoring | Ops + AI Agents | 🔄 | Use section 6 table |
| T8 | Cleanup legacy dirs | Platform Core | ✅ | All `docs-nttc/scripts/*` removed |

Contacts: `platform-core@digital.vn`, `automation@digital.vn`, `ops@digital.vn`.

---

## 9. Support & References

- **repo-manifest:** `vds-scripts/repo-manifest.yaml`
- **Reports:** `vds-scripts/reports/<service>/YYYY/MM/DD/`
- **SLA/MTTR policy:** `docs/operations/sla-mttr-policy.md`
- **Bitbucket practices / architecture:** under respective orchestrator directories.
- **AGENTS.md:** root guide referencing this README.

_Last updated: 2026‑02‑06_










