<!-- diátaxis: reference -->
# Agent Operational Contract

This reference defines the runtime contract for AI agents operating inside the VDS WHO ecosystem. All behaviors listed here are required unless explicitly gated by capability flags.

---

## Token Budgets

### Default session limits

| Tier | Context tokens | Output tokens | Typical use |
|------|---------------|---------------|-------------|
| Fast | 8K | 1K | Grep, status, quick reads |
| Standard | 32K | 4K | Most authoring and debugging |
| Deep | 128K | 8K | Audit analysis, large diffs |

### Budget gates

- Agents must declare intent before entering a deep reasoning pass.
- Agents must stop and report when a task exceeds the declared tier.
- Compaction and checkpointing are preferred over silent truncation.

---

## Skill Loading

### Canonical source

Skills are loaded on-demand from:

```
WHO-project/vds-skills/skills/<skill-name>/SKILL.md
```

### Load order

1. Check `cat skills/<skill-name>/SKILL.md` at the canonical path.
2. Fallback to direct file read at the canonical path above.
3. If both fail, report the exact missing path and stop.

### Skill scope rules

- Skills are advisory, not overriding. Runtime behavior in code wins when there is a conflict.
- Agents must not inline skill content into instructions or AGENTS.md.
- Agents must not modify canonical `SKILL.md` files unless the user explicitly requests a skill update.

---

## Tool Patterns

### Execution primitives

| Tool | Purpose | Escalation rule |
|------|---------|-----------------|
| `edit_file` | Apply structured patches to code | Approval required when >5 files or >100 lines changed |
| `exec_command` | Run shell commands via PTY | Always return output and exit code; never hide failures |
| `read_file` | Fetch file contents | Use absolute or workspace-relative paths; quote paths with spaces |
| `glob` | List matching files | Prefer `rg` or `sg` over unbounded `find .` |
| `web_search` | External research | Verify against local evidence before acting |

### Concurrency rules

- Background commands: use `run_in_background: true` for any command expected to take over 5 seconds.
- Read commands: always wait for output before issuing dependent writes.
- Mock rule for tests: external services must be mocked; no real API calls in test files.

---

## Memory Recall

### Session memory

- Ephemeral session context is provided by the harness (cwd, env vars, file tree).
- Agents must treat session hints as advisory; verify against current filesystem state.

### Persistent memory

- Long-term memory is stored via the `memory_orchestrator` API.
- Commands: `vds-cli memory search`, `vds-cli memory store`.
- Category tags used: `code`, `design`, `incident`, `onboarding`.

### Cross-agent recall

- Shared memory writes must include `--importance high` when the discovery is likely to affect other agents.
- Agents must search memory before claiming a new root-cause diagnosis.

---

## Escalation Rules

### When to escalate

- Command fails due to sandbox, permission, or path restriction.
- External API returns unreachable or rate-limited.
- Task boundary is crossed (e.g., moving from docs to Confluence sync to CI pipeline changes).
- Uncertainty about whether a change affects AGENTS.md sync lines or validator counts.

### Escalation format

Include in every escalation:
1. Exact command that failed
2. Exit code and last 5 lines of output
3. File paths involved
4. Concrete next step you need approval for

---

## Compaction Management

### Trigger conditions

- Tool context grows beyond the session tier limit.
- Multiple file reads accumulate without producing a write.
- A long reasoning chain is about to generate a large single edit.

### Compaction steps

1. Summarize completed work in 3–5 sentences.
2. List open questions or blockers.
3. Preserve file paths and line-number anchors for the next action.
4. Discard verbose tool output that has already informed a decision.

---

## Persona Boundaries

### Human-facing docs

- Tutorials and how-to guides are written for human contributors.
- Code blocks must be copy-pasteable without modification.
- Paths must be quoted and iCloud-safe.

### Agent-facing docs

- Reference and explanation docs are written for AI agents.
- May include pseudocode, decision matrices, and validator call patterns.
- Should explicitly mark machine-executable steps with `>` or code fences.

---

## Validation Hooks

### Required pre-merge checks

- `vds-cli docs validate` exits 0.
- New files linked from `llms.txt` or `AGENTS.md`.
- Diátaxis quadrant declared via `<!-- diátaxis: X -->` header.

### Optional but recommended

- `vds-cli docs check-freshness` reports 0 stale pairs.
- `vds-cli spec validate` passes on spec files in the patch.

---

## Environment Assumptions

- `cwd` is the monorepo root unless the user specifies a worktree path.
- Shell is `zsh` on macOS, `bash` elsewhere.
- Python tooling is executed through `uv run --project <pkg>`.
- Secrets live in `~/.vds/.env` and are never inlined.
