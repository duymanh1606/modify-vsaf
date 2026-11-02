<!-- diátaxis: reference -->
# Confluence Sync Target — WHO-Project Ecosystem Documentation

> **Last synced:** 2026-04-30
> **Source:** `docs/agents/reference/confluence-sync-target.md` → `vds-cli docs confluence-sync`

This page is the target of the `vds-cli docs confluence-sync` command. Edit this file, then run:

```bash
vds-cli docs confluence-sync
```

## Canonical Spec Location (Consolidated 2026-04-29)

Previously scattered across four directories. Now unified in `ARCHIVE/`:

| Old Location | Status |
|-------------|--------|
| `.gpt-5.4/specs/ARCHIVE/who-docs-canonical/` | Archived (Phase 177) |
| `.gpt-5.4/specs/ARCHIVE/who-docs-phase-178/` | Archived (Phase 178) |
| `.gpt-5.4/specs/ARCHIVE/who-docs-phase-179/` | Archived (Phase 179) |
| `.gpt-5.4/specs/ARCHIVE/who-project-documentation-enhancement/` | **Canonical (ARCHIVED, completed)** |

### Canonical Spec Triplet

**`.gpt-5.4/specs/ARCHIVE/who-project-documentation-enhancement/`**

| File | Version | Purpose |
|------|---------|---------|
| `requirements.md` | **v2.0.1** | Problem statement, scope, acceptance criteria, post-179 merge state |
| `design.md` | v2.0.0 | Tiered context, Diátaxis, validation, observability |
| `tasks.md` | **v2.0.1** | Unified DOC-001 to DOC-027 + DOC-019–026 post-179 merge tasks |
## Latest Acceptance Gates (Phase 179)

| Gate | Before | After |
|------|--------|-------|
| **Unit Tests** | 201 | **203 passed** |
| **Doc Quality Score** | 0.79 | **0.80** |
| **Low Docs (<0.5)** | 2 | **0** |
| **Validation Issues** | 3 warnings | **0** |
| **Freshness Pairs** | 6 | **8** (+ECOSYSTEM files) |

## Recently Added CLI Surfaces

| Command | Purpose |
|---------|---------|
| `vds-cli docs onboarding-funnel` | Aggregate tool-use by Diátaxis quadrant |
| `vds-cli docs freshness-heatmap` | Quant lag days per freshness pair |
| `vds-cli docs ecosystem-index` | Multi-collector daily ecosystem pulse |
| `vds-cli docs validate --check-ecosystem` | Warn if ECOSYSTEM-DOCS.md/CHANGELOG.md missing |
| `vds-cli telegram status` | Telegram bridge daemon status |
| `vds-cli telegram audit` | Telegram bridge audit log |
| `vds-cli telegram session` | Claude session store ops |
| `vds-cli telegram logs` | Bridge/shim log tail |
| `vds-cli telegram restart` | Hot-reload bridge daemon |


## Sync Scope

**English pages** (auto-managed by CI pipeline):
| Page | ID | Status |
|------|-----|--------|
| WHO-Project Ecosystem Documentation | 98997962 | ✅ Auto-synced |
| Ecosystem Installation Guide | 98997963 | ✅ Auto-synced |
| vds-scripts Quick Reference | 98997964 | ✅ Auto-synced |
| vds-skills Quick Reference | 98997965 | ✅ Auto-synced |
| vds-claude-plugins Quick Reference | 98997966 | ✅ Auto-synced |
| Documentation Health Dashboard | 98997968 | ✅ Auto-synced |

**Vietnamese pages** (manually managed, IDs mapped in `.confluence.yaml`):
| Page | ID | Status | Note |
|------|-----|--------|------|
| Hướng dẫn cài đặt hệ sinh thái | 99846963 | ⚠️ Manual | Created externally, not in CI scope |
| Tài liệu tham khảo vds-scripts | 99846964 | ⚠️ Manual | Created externally, not in CI scope |
| Tài liệu tham khảo vds-skills | 99846965 | ⚠️ Manual | Created externally, not in CI scope |
| Tài liệu tham khảo vds-claude-plugins | 99846966 | ⚠️ Manual | Created externally, not in CI scope |

> **Note:** Vietnamese pages require manual content updates. The sync pipeline updates English pages only. Page IDs are preserved in `docs/.confluence.yaml` for reference.

## Doc Ecosystem Metrics (vds-scripts)

| Metric | Value |
|--------|-------|
| Scored docs | **110** (+26 new) |
| Average quality | 0.85/1.0 |
| Low-quality docs | 0 |
| Orchestrators | **37** in router.py + **37** reference docs |
| Vietnamese pages | 87 (39 orchestrator + 48 other) |
| New Phase 180 docs | 16 (+8 vi-VN translations) |
| Telegram bridge | 102 tests, 9 refs, daemon + 2 runners |
| Skills | 27 with SKILL.md |
| Freshness pairs | 18 |

---

## Sync Instructions

**Edit `confluence-sync-target.md`** (this file) to update Confluence. Then push:

```bash
git add docs/agents/reference/confluence-sync-target.md
git commit -m "docs: sync target update"
git push origin HEAD
```

Then either wait for the CI pipeline or run manually:

```bash
vds-cli docs confluence-sync --dry-run  # preview
vds-cli docs confluence-sync             # apply
```
