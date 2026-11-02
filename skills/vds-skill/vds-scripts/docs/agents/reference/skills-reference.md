<!-- diátaxis: reference -->

# Skills Reference

The canonical skills catalog is:

- [WHO skills catalog](../../../../vds-skills/README.md)

Key operational skills:

- [vds-scripts-skill](../../../../vds-skills/skills/vds-scripts-skill/SKILL.md) — platform-routing entrypoint for the WHO scripts ecosystem
- [WHO capability routing matrix](who-capability-routing-matrix.md) — human/agent routing aid for command families and skill ownership
- [audit-orchestrator-skill](../../../../vds-skills/skills/audit-orchestrator-skill/SKILL.md) — deep audit workflow execution and interpretation
- [spec-creation-skill](../../../../vds-skills/skills/spec-creation-skill/SKILL.md) — spec creation and consolidation
- [research-skill](../../../../vds-skills/skills/research-skill/SKILL.md) — source-backed research
- [code-review-graph-skill](../../../../vds-skills/skills/code-review-graph-skill/SKILL.md) — structural graph companion analysis
- [llm-analysis-skill](../../../../vds-skills/skills/llm-analysis-skill/SKILL.md) — LLM-backed content evaluation
- [lsp-skill](../../../../vds-skills/skills/lsp-skill/SKILL.md) — LSP setup and usage
- [circular-dependency-skill](../../../../vds-skills/skills/circular-dependency-skill/SKILL.md) — dependency-cycle analysis

Guidance:
- use `vds-scripts-skill` first for platform routing and command-family selection,
- use specialist skills for deep workflow/runbook guidance,
- prefer `rg` / direct file reads first for simple exact answers,
- do not treat graph output as authoritative audit evidence.

## Related Documents

- [VDS CLI Reference](vds-cli-reference.md)
- [Orchestrator Index](orchestrator-index.md)
- [Skills Reference](skills-reference.md)
- [Confluence Hub](http://confluence.digital.vn/display/TTCN24/WHO-Project+Ecosystem+Documentation)
