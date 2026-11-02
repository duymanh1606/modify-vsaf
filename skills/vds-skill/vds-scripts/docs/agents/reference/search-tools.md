<!-- diátaxis: reference -->

# Search Tools Reference

> Available search tools in the VDS ecosystem and when to use each.

## Tool Escalation Ladder

| I know... | Tool | Example | When to escalate |
|-----------|------|---------|-----------------|
| Exact string | `rg` | `rg "UserAuthError" --type py` | No results → `sg` |
| Code shape | `sg` | `sg -p 'class $N(BaseModel)' -l python` | No results → `grepai` |
| Concept/meaning | `grepai` | `grepai search "auth middleware"` | Too many → scope it |
| Caller chain | `graphify` | `graphify query "auth flow"` | No graph → `gitnexus` |
| Prior decisions | `vds-cli memory` | `vds-cli memory search "retry pattern"` | No results → proceed fresh |

## Commands

```bash
# Quick exact-string search
rg "pattern" --type py

# Semantic code search
grepai search "credential resolution"

# Architecture query
graphify query "audit state management"
```

## Related

- [Research Orchestrator](research-orchestrator.md)
- [Memory Orchestrator](memory-orchestrator.md)
- [VDS CLI](vds-cli-reference.md)
