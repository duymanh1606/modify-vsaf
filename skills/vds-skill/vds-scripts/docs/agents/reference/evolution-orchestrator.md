<!-- diátaxis: reference -->

# Evolution Orchestrator

> WHO ecosystem evolution loop — manage skill evolution through three-gate pipeline, verdict tracking, and automatic promotion.

## Scope

- **Does:** Route skills through gates, track verdicts, auto-promote approved changes, sign/verify HMAC integrity.
- **Does NOT:** Make autonomous decisions without kill-switch approval, replace code review.
- **Primary users:** AI agents (skill maintenance), human leads (approval), release managers.

## CLI Entry

```bash
# Evolution Loop CLI
vds-cli evolution --help
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `status` | Show kill-switch state, queue depth, recent verdicts |
| `list` | List all verdicts (pending, promoted, rejected) |
| `show VERDICT_ID` | Show detailed verdict |
| `route SKILL.md` | Route skill through Gate 1→2→3 pipeline |
| `promote VERDICT_ID` | Promote eligible verdict to master |
| `reject VERDICT_ID` | Reject verdict |
| `escalate VERDICT_ID` | Escalate for human review |
| `sign-verdict PATH` | HMAC sign verdict |
| `verify-verdict PATH` | Verify HMAC signature |
| `ensemble-judge SKILL` | Three-judge evaluation |
| `openspace-doctor` | Readiness checks |
| `openspace-sync-shadow` | Sync canonical→shadow skills |

## Kill Switch

Controls autonomous mode:

| Mode | Env Var | Behavior |
|------|---------|----------|
| MANUAL | `OPENSPACE_AUTONOMOUS_ENABLED=false` | Human controls all |
| AUTO | `OPENSPACE_AUTONOMOUS_ENABLED=true` | Daemon auto-promotes |

## Three-Gate Pipeline

```
ExecutionAnalysis
       │
       ▼
┌──────────────┐
│ Gate 1       │ → Structural (queue, budget)
└──────────────┘
       │
       ▼
┌──────────────┐
│ Gate 2       │ → Behavioral (regression)
└──────────────┘
       │
       ▼
┌──────────────┐
│ Gate 3       │ → Semantic (Claude quality)
└──────────────┘
       │
       ▼
   Verdict
```

## Common Workflows

### Workflow: Route a Skill (Manual)

```bash
# Route skill through pipeline
vds-cli evolution route path/to/skill.md

# Check verdict
vds-cli evolution list
vds-cli evolution show VERDICT_ID

# Promote if eligible
vds-cli evolution promote VERDICT_ID
```

### Workflow: Enable Auto-Promote

```bash
# Set kill switch to AUTO
export OPENSPACE_AUTONOMOUS_ENABLED=true

# Run daemon
./scripts/install-evolution-auto.sh
```

### Workflow: Verify System Health

```bash
# Check status
vds-cli evolution status

# Run diagnostics
vds-cli evolution openspace-doctor

# Sync skills
vds-cli evolution openspace-sync-shadow
```

## Related

- **Spec:** [.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md](../../.gpt-5.4/specs/who-ecosystem-evolution-loop/SPEC.md)
- **Deep Integration:** [docs/evolution-loop-deep-integration.md](../../docs/evolution-loop-deep-integration.md)
- **Rollout Guide:** [docs/evolution-auto-run-rollout.md](../../docs/evolution-auto-run-rollout.md)