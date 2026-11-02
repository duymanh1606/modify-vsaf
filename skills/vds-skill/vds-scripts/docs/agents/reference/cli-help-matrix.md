<!-- diátaxis: reference -->

# Verified CLI help matrix

This reference helps AI agents and operators choose the correct VDS CLI entrypoint.
**`vds-cli` is the ONLY valid user-facing entry point.** Direct package executables
are internal router implementation details and must never be invoked by users.

## How to use this matrix

1. **Always** use routed `vds-cli <service> <command>` for all operations.
2. **Never** invoke direct package executables (`vds-audit`, `vds-spec`, etc.) —
   these are internal to the router.
3. Treat `--help` as the authoritative discovery surface before assuming an
   command name.
4. In dedicated `vds-scripts` worktrees, prefer `./scripts/worktree_uv.sh ...`
   for `uv` commands so inherited parent `VIRTUAL_ENV` state does not leak into
   the wrong worktree.

## Routed command families

| Routed family | `vds-cli` form | Help status | Notes |
| --- | --- | --- | --- |
| platform | `vds-cli --help` | live-verified | Unified router entrypoint |
| audit | `vds-cli audit ...` | live-verified | Specialist workflow surface |
| spec | `vds-cli spec ...` | live-verified | Shared spec lifecycle tooling |
| jira | `vds-cli jira ...` | live-verified | |
| confluence | `vds-cli confluence ...` | live-verified | |
| bitbucket | `vds-cli bitbucket ...` | live-verified | |
| git | `vds-cli git ...` | live-verified | |
| elastic | `vds-cli elastic ...` | live-verified | |
| sonarqube | `vds-cli sonarqube ...` | live-verified | |
| grafana | `vds-cli grafana ...` | live-verified | |
| schema | `vds-cli schema ...` | live-verified | |
| diagrams | `vds-cli diagrams ...` | live-verified | |
| google-sheets | `vds-cli google-sheets ...` | live-verified | |
| task management | `vds-cli tasks ...` | live-verified | |
| openapi | `vds-cli openapi ...` | live-verified | |
| pdf | `vds-cli pdf ...` | live-verified | |
| markdown | `vds-cli markdown ...` | live-verified | Use `vds-cli markdown format` for formatting |
| intellij | `vds-cli intellij ...` | live-verified | |
| links | `vds-cli links ...` | live-verified | |
| structure | `vds-cli structure ...` | live-verified | |
| lsp | `vds-cli lsp ...` | live-verified | |
| brd | `vds-cli brd ...` | live-verified | |
| excel | `vds-cli excel ...` | live-verified | |
| circular dependency | `vds-cli circular-dependency ...` | live-verified | |
| progress | `vds-cli progress ...` | live-verified | |
| hexagonal | `vds-cli hexagonal ...` | live-verified | |
| multi-agent | `vds-cli multi-agent ...` | live-verified | |
| public-interface | `vds-cli public-interface ...` | live-verified | |
| metabase | `vds-cli metabase ...` | live-verified | |
| mcp | `vds-cli mcp ...` | live-verified | |
| research | `vds-cli research ...` | live-verified | |
| scheduler | `vds-cli scheduler ...` | live-verified | VDS workflow scheduling |

## Built-in commands

Commands built into `vds-cli` (not routed to orchestrators):

| Command | Purpose |
| --- | --- |
| `vds-cli status` | System status and health checks |
| `vds-cli doctor` | Diagnose routing and environment readiness |
| `vds-cli version` | Show VDS CLI version |
| `vds-cli regenerate-manifest` | Regenerate repo-manifest.yaml from Bitbucket |

## Worktree-safe examples

> All examples **must** use `vds-cli` routing — direct executables are internal.

- `./scripts/worktree_uv.sh run --project vds_cli vds-cli --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli tasks --help`
- `./scripts/worktree_uv.sh run --project vds_cli vds-cli schema --help`

## Source notes

This matrix is maintained from:

- live `--help` verification in the active Phase 3 worktree
- Routed-family documentation in `vds_cli/README.md`, `cli-commands.md`, and `vds-cli-reference.md`
- The canonical standard: `vds-cli` is the ONLY user-facing entry point
