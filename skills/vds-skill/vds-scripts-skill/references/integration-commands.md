# Integration Commands

vds Representative WHO integration command families.

These examples use `vds-cli` (MCP-registered entrypoint). For direct uv invocation, use `.claude/vds-scripts/scripts/worktree_uv.sh run --directory .claude/vds-scripts --package <uv-package-name> ...` (project-local) or `~/.claude/vds-scripts/...` (global fallback).

- `vds-cli jira ...`
  - JQL search example: `vds-cli jira search "project = CBDC ORDER BY updated DESC" --limit 5 --json-only`
  - Note: `vds-jira-cli search` now accepts `--json-only` as a command-local flag after `search`, in addition to the global pre-subcommand form.
- `vds-cli confluence ...`
- `vds-cli bitbucket ...`
- `vds-cli git ...`
- `vds-cli elastic ...`
- `vds-cli grafana ...`
- `vds-cli sonarqube ...`

Use the scripts workspace reference docs for deeper command examples.
