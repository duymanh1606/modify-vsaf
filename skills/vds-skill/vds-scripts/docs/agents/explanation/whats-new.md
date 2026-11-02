<!-- diátaxis: explanation -->

# What's New

Track recent changes and verify your environment is current.

## 2026-04-30 — Comprehensive Documentation (Phase 180)

New documentation covering 8 target sections:
- Introduction, Quick Start, System Requirements, Configuration Reference
- Features Overview, Feature Progression Guide, Orchestrator Comparison
- Architecture docs (expanded), System Architecture, Data Flow
- Current Development, Roadmap, Contribution Guide
- Tips & Tricks, Troubleshooting Guide, Common Errors Reference

Verify you have the new docs:
```bash
vds-cli docs validate && vds-cli docs quality-score
```

## 2026-04-29 — Telegram Bridge & Lint Hygiene

- **Telegram Bridge**: Bot-based notifications with multi-runner support (Claude, ACP, Codex)
  - 102 test files, 9 skill references
  - Daemon + 2 runner surfaces
- **Lint Hygiene**: Track-α fixes for Phase 220
  - AGENTS.md capped at 250 lines
  - `vds-cli lint` command family

Check bridge status:
```bash
vds-cli telegram status --daemon 2>/dev/null || echo "Telegram bridge not configured"
```

## 2026-04-22 — Phase 179 Merge

- Diátaxis documentation structure (explanation, tutorial, how-to, reference)
- Validation gates in AGENTS.md
- Observability: `vds-cli docs consumption-funnel`, `freshness-report`, `ecosystem-report`
- Confluence sync reference doc
- Infrastructure v2.15 documentation

## 2026-04-21 — Phase 177 Merge

- Dual-audience persona separation (human vs agent)
- Vietnamese translations (58 canonical + 19 drafts)
- Ecosystem docs index (`ECOSYSTEM-DOCS.md`)
- Changelog (`ECOSYSTEM-CHANGELOG.md`)
- Pre-commit hooks and CI quality gate

## Upcoming

- Phase 220 Track-α: Lint hardening continued
- Phase 181+: Additional orchestrator deep dives
- Video tutorials

## Quick Health Check

Run this weekly:
```bash
# Verify all gates pass
vds-cli docs validate
vds-cli --help > /dev/null && echo "CLI OK"

# Check test baseline
pytest --co -q | tail -1

# Check for stale docs
vds-cli docs freshness-report --days 30
```

## See Also

- [Development Roadmap](development-roadmap.md)
- [ECOSYSTEM-CHANGELOG.md](../../../ECOSYSTEM-CHANGELOG.md)
