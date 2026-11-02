<!-- diátaxis: explanation -->

# Development Roadmap

## Completed Phases

| Phase | Theme | Merge Date | Key Deliverable |
|-------|-------|-----------|----------------|
| 177 | Docs Foundation | 2026-04-21 | Diátaxis structure, dual-audience, vi-VN |
| 178 | Validation Design | — | Design-only, rolled into 179 |
| 179 | Observability & Quality | 2026-04-29 | Validation gates, metrics, Confluence sync |
| 180 | Comprehensive Docs | 2026-04-30 | 8 sections, 20 new docs |

## Active Work

| Phase | Theme | Status |
|-------|-------|--------|
| 220 Track-α | Lint hardening | In progress |

## Planned Phases

| Phase | Theme | ETA | Scope |
|-------|-------|-----|-------|
| 181 | Orchestrator Deep Dives | 2026-05 | Per-orchestrator tutorials |
| 182 | Video Tutorials | 2026-05 | Screen recordings for setup |
| 183 | Community Contributions | 2026-06 | External contributor guide |
| 184 | Advanced AI Patterns | 2026-06 | Multi-agent workflows, memory optimization |

## Decision Criteria

Phase prioritization follows:

1. **Operational impact** — Does this reduce incidents or toil?
2. **Onboarding friction** — Does this help new developers?
3. **Strategic alignment** — Does this support broader organizational goals?
4. **Effort vs value** — Is the scope proportional to the impact?

## See Also

```bash
# List completed phases
vds-cli roadmap --status completed
# Show active work items
vds-cli roadmap --status active --format markdown
```

- [What's New](whats-new.md)
- [Contribute New Orchestrator](../how-to/contribute-new-orchestrator.md)
- Spec directories under `.gpt-5.4/specs/`
