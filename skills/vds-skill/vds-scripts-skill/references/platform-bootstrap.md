# Platform Bootstrap

Use this guide when you need to enter the WHO scripts ecosystem and choose the first command to run.

## Canonical entrypoints

vds-scripts can be installed at **project-local** `.claude/vds-scripts/` (preferred) or **global** `~/.claude/vds-scripts/`.

- Project-local usage (preferred):
  - `.claude/vds-scripts/scripts/worktree_uv.sh run --directory .claude/vds-scripts --package vds-cli vds-cli --help`
  - `.claude/vds-scripts/scripts/worktree_uv.sh run --directory .claude/vds-scripts --package vds-cli vds-cli env status`
  - `.claude/vds-scripts/scripts/worktree_uv.sh run --directory .claude/vds-scripts --package vds-cli vds-cli doctor`
- Interactive monorepo-root usage:
  - `./WHO-project/vds-scripts/scripts/worktree_uv.sh run --directory WHO-project/vds-scripts --package vds-cli vds-cli --help`
- Dedicated `vds-scripts` worktree usage:
  - `./scripts/worktree_uv.sh run --package vds_cli vds-cli --help`
- Maintained shell scripts should not copy those raw forms. They should source `scripts/vds_sh_helpers.sh` and use the helper contract (`vds_uv_run_package`, `vds_uv_sync_package`, `vds_uv_sync_all`).
- Preferred integrated baseline is Python 3.10+.

## Common first steps

1. Check environment readiness with `vds-cli env status`
2. Check routed-service availability with `vds-cli status` and `vds-cli doctor`
3. Decide whether the task belongs to:
   - a platform command family
   - a specialist CLI such as `vds-audit` or `vds-spec`
   - a specialist skill such as `audit-orchestrator-skill`

## When to stop using the platform skill

If the task becomes specialist or phase-sensitive, route to the specialist skill rather than extending the platform path.
