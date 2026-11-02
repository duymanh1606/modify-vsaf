<!-- diátaxis: reference -->

# Research Orchestrator

> Evidence-first technical research combining local repository evidence with external sources.

## Scope

- **Does:** Search local code (rg, sg, grepai), query external APIs (Tavily, Exa, Context7), score evidence, generate research packets.
- **Does NOT:** Make decisions for you, replace human judgment on strategic choices.
- **Primary users:** AI agents (fact validation), human leads (technology evaluation).

## CLI Entry

```bash
# Via unified router
vds-cli research --help

# Direct entry
vds-cli research --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `search` | Unified search | `--tool`, `--json` |
| `health` | Check tool availability | — |
| `score` | Score evidence quality | `--threshold` |

## Common Workflows

### Workflow: Validate Technical Claim

1. Search local evidence: `vds-cli research search "claim text"`
2. Query external sources: `vds-cli research search "topic" --tool tavily`
3. Collect and organize findings
4. Score evidence quality
5. Emit decision-ready report

## Related

- **Orchestrators:** [memory](memory-orchestrator.md), [spec](spec-orchestrator.md), [audit](audit-triage-playbook.md)
- **Skills:** [research-skill](../../../../vds-skills/skills/research-skill/SKILL.md)
- **Confluence:** [WHO Research](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)

## Troubleshooting

| Issue | Cause | Resolution |
|-------|-------|------------|
| Command not found | Orchestrator not installed | Run `uv sync --all-packages` |
| Config missing | `~/.vds/.env` unset | Add required credentials per [AGENTS.md](../../../AGENTS.md) |
| Permission denied | Insufficient privileges | Check Bitbucket/Confluence token scope |
