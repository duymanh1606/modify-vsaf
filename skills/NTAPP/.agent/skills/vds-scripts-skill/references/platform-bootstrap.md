# Platform Bootstrap

Use this guide when you need to enter the WHO scripts ecosystem and choose the first command to run.

## Canonical entrypoints

```bash
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli --help
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli env status
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli status
uv run --directory ~/.claude/vds-scripts --package vds-cli vds-cli doctor
```

## Common first steps

1. Check environment readiness with `vds-cli env status`
2. Check routed-service availability with `vds-cli status` and `vds-cli doctor`
3. Decide whether the task belongs to:
   - a platform command family
   - a specialist CLI such as `vds-audit` or `vds-spec`
   - a specialist skill such as `audit-orchestrator-skill`

## When to stop using the platform skill

If the task becomes specialist or phase-sensitive, route to the specialist skill rather than extending the platform path.
