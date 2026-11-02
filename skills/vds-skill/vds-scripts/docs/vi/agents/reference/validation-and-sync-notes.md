<!-- diátaxis: reference -->

<!-- TODO: translate — Vietnamese translation pending -->

# Validation And Sync Notes

This note records the remaining validation steps for the WHO ecosystem alignment work.

## Worktree-safe implementation status

Current edits are isolated in dedicated repo worktrees for:
- `vds-scripts`
- `vds-skills`

## Remaining validation steps

1. Review capability coverage against `docs/agents/reference/who-capability-inventory.md`
2. Review routing consistency against `docs/agents/reference/who-capability-routing-matrix.md`
3. Re-run skills alignment from the monorepo root when it is safe to touch generated surfaces:
   - `./WHO-project/vds-skills/scripts/verify-alignment.sh`
4. Regenerate root `AGENTS.md` from canonical WHO skills source when it is safe to update root generated outputs:
   - `vds-cli skills sync --agent claude`

## Important constraint

The root generated `AGENTS.md` lives outside these two repo worktrees. It should be synced only in a controlled follow-up step so isolated worktree implementation does not unintentionally mix with the main monorepo working tree.
