# Specialist Routing

Use this routing map when the platform skill identifies a specialist domain.

| Intent | Preferred Skill | Why |
|-------|------------------|-----|
| Run audit workflows, readiness checks, reruns, uploads | `audit-orchestrator-skill` | Phase-aware audit guidance lives there |
| Evaluate README/API docs/security docs with LLM support | `llm-analysis-skill` | Specialist content-evaluation guidance lives there |
| Create or consolidate specs | `spec-creation-skill` | Owns spec workflow and alignment practices |
| Develop or update CLI/orchestrator packages | `cli-development-skill` | Owns Typer/JSON/CLI package standards |
| Configure or use LSPs | `lsp-skill` | Owns LSP tooling guidance |
| Analyze cross-repo dependency cycles | `circular-dependency-skill` | Owns cycle-analysis workflow |
| Research with local + web sources | `research-skill` | Owns research-first workflow |
| Build structural graph context | `code-review-graph-skill` | Companion graph-analysis workflow |
