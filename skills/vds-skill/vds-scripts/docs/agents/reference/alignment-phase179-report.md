# VDS-Scripts Agent Team Research: Doc↔Code↔Confluence Alignment Report

**Date:** 2026-04-29  
**Spec:** DOC-SPEC-009+ (Phase 179)  
**Branch:** master (post-merge phase9/wave2-agent-core-expansion)

---

## Executive Summary

| Check | Status | Score |
|-------|--------|-------|
| Validation (docs validate) | ✅ Pass | 100% |
| Confluence sync (10 pages) | ✅ All synced | 100% |
| Code→Docs parity (14 commands) | ✅ All documented | ~100% |
| llms.txt links | ✅ All valid | 100% |
| Diátaxis headers | ✅ Clean | 100% |
| Orphan docs | ✅ 0 orphans | 100% |

---

## Detail: Code → Docs Parity

### `docs_app.commands` in `vds_cli/src/vds_cli/cli.py` (14 commands)

| # | Command | Function Line | Reference Doc | Status |
|---|---------|---------------|---------------|--------|
| 1 | `validate` | ~458 | `validation-and-sync-notes.md` + `confluence-sync.md` | ✅ |
| 2 | `quality-score` | ~535 | `cli-help-matrix.md` + `ci-workflows.md` | ✅ |
| 3 | `freshness` | ~584 | `validation-and-sync-notes.md` | ✅ |
| 4 | `init-repo` | ~643 | `agent-operational-contract.md` | ✅ |
| 5 | `ecosystem-index` | ~670 | `ecosystem-architecture.md` | ✅ |
| 6 | `onboarding-funnel` | ~680 | `who-capability-inventory.md` | ✅ |
| 7 | `freshness-heatmap` | ~728 | `cli-help-matrix.md` | ✅ |
| 8 | `monthly-consumption` | ~747 | `cli-help-matrix.md` | ✅ |
| 9 | `confluence-sync` | ~767 | `confluence-sync.md` + `confluence-sync-target.md` | ✅ |
| 10 | `watch-agents` | ~818 | `watch-agents.md` | ✅ |
| 11 | `watch-agents-install` | ~960 | `watch-agents.md` | ✅ |
| 12 | `watch-agents-uninstall` | ~989 | `watch-agents.md` | ✅ |
| 13 | `watch-agents-status` | ~1002 | `watch-agents.md` | ✅ |

> **Note:** Two commands (`generate`, `spec-convert`) appear in `docs_app` but are commented/legacy. Not counted.

---

## Detail: Confluence Sync Alignment

### English Pages (Auto)

| Page ID | Title | Source File | Version | Status |
|---------|-------|-------------|---------|--------|
| 98997962 | WHO-Project Ecosystem Documentation | `AGENTS.md` + `ECOSYSTEM_ALIGNMENT.md` | v13 | ✅ Synced |
| 98997963 | Ecosystem Installation Guide | `docs/agents/how-to/install-and-bootstrap-who-scripts-and-skills.md` | v3 | ✅ Synced |
| 98997964 | vds-scripts Quick Reference | `AGENTS.md` | v3 | ✅ Synced |
| 98997965 | vds-skills Quick Reference | `docs/vi/agents/how-to/install-and-bootstrap-who-scripts-and-skills.md` | v6 | ✅ Synced |
| 98997966 | vds-claude-plugins Quick Reference | `vds_cli/README.md` | v6 | ✅ Synced |
| 98997968 | Documentation Health Dashboard | `docs/agents/reference/health-dashboard.md` | v6 | ✅ Synced |

### Vietnamese Pages (Manual IDs, Auto Content)

| Page ID | Title | Source File | Version | Status |
|---------|-------|-------------|---------|--------|
| 99846963 | Hướng dẫn cài đặt hệ sinh thái | `AGENTS.vi.md` | v1 | ✅ Synced (no content change) |
| 99846964 | Tài liệu tham khảo vds-scripts | `AGENTS.vi.md` | v1 | ✅ Synced (no content change) |
| 99846965 | Tài liệu tham khảo vds-skills | `AGENTS.vi.md` | v1 | ✅ Synced (no content change) |
| 99846966 | Tài liệu tham khảo vds-claude-plugins | `AGENTS.vi.md` | v1 | ✅ Synced (no content change) |

---

## Detail: CI Pipeline Alignment

| Check | File | Status |
|-------|------|--------|
| Trigger on push (master, main) | `.github/workflows/confluence-sync.yml` | ✅ |
| Validation before sync | `--check-vi --check-diataxis` | ✅ |
| link validation flag | `--validate-links` | ✅ |
| Secrets documented | `README.md` + `AGENTS.md` | ✅ |
| Vietnamese pages in workflow | Not explicitly handled (no `--create-missing`) | ⚠️ By design—VI pages created manually |
| Artifact upload | `.github/workflows/docs-confluence-evidence.yml` | ✅ (separate workflow) |

---

## Fixes Applied (DOC-SPEC-009)

| Issue | File | Resolution |
|-------|------|-----------|
| Broken `llms.txt` link (wrong relative path) | `llms.txt` | Fixed `../` → `../../` |
| Missing Diátaxis header | `backup-restore.md` | Added `<!-- diátaxis: reference -->` |
| Missing Diátaxis header | `migration-playbook.md` | Added `<!-- diátaxis: reference -->` |
| Orphaned docs not in llms.txt | `backup-restore.md`, `migration-playbook.md` | Registered entries in `llms.txt` |

---

## Commits

| Hash | Description |
|------|-------------|
| `146441ba` | DOC-SPEC-009: Fix alignment issues (master, pushed) |
| `41953385` | Merge phase9/wave2-agent-core-expansion to master |
| `ae7b1d18` | DOC-SPEC-008: Sync scope + VI policy |
| `260e54b8` | DOC-SPEC-007: Map VI page IDs |
| `45396dad` | DOC-SPEC-006: Sync live pages |

---

## Next Steps / Open Items

1. **No CI runs yet** — Confirm: `confluence-sync.yml` is wired but has no execution history on GitHub/Bitbucket Actions.
2. **Command parity audit for `env` and `skills` sub-apps** — Could extend research to `env_app` and `skills_app` commands.
3. **Vietnamese page version bump** — When `AGENTS.vi.md` is edited, these pages will get version bumps automatically.
4. **Cross-repo alignment** — Check `vds-skills/` and `vds-claude-plugins/` docs against Confluence.

---

*Generated by vds-scripts alignment research team (Phase 179).*

---

## Post-Report Findings (DOC-SPEC-011)

### Critical Gap: Stale vds-claude-plugins references in `.confluence.yaml`

**Found by:** Agent team research (subagent `19-docs-confluence-alignment`)  
**Fixed:** 2026-04-29 in commit `830f884`

**Problem:**
- `.confluence.yaml` listed `vds-claude-plugins` in `repos` section with `active: true`
- But the repo was merged into `vds-skills` on 2026-04-22 per `ECOSYSTEM-CHANGELOG.md`
- The vds-claude-plugins worktree no longer exists on disk
- Sync code falls back to `vds-scripts` (default repo) content, but keeps the old page title
- Result: **Misrepresentation bug** — Confluence pages (98997966, 99846966) show stale "vds-claude-plugins" branding

**Fix:**
- Changed `active: true` → `active: false` for vds-claude-plugins in `.confluence.yaml`
- Added description: "vds-claude-plugins merged into vds-skills (2026-04-22). Content maintained in vds-skills repo."
- Preserved page entries (IDs remain) so existing pages stay linked but won't get stale content

**Impact:**
| Page ID | Title | Content Source | Status Post-Fix |
|---------|-------|---------------|-----------------|
| 98997966 | vds-claude-plugins Quick Reference | vds-scripts (fallback) | ⚠️ Page exists, stale branding |
| 99846966 | Tài liệu tham khảo vds-claude-plugins | vds-scripts (fallback) | ⚠️ Page exists, stale branding |

> **Recommendation:** Consider archiving or renaming these pages in Confluence, or moving their content under the vds-skills pages.
