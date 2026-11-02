<!-- diátaxis: reference -->

# Git Orchestrator

> Perform git operations: worktrees, branches, status, logs, stashes, and merge workflows as part of VDS monorepo tasks.

## Scope

**What this orchestrator does:**
- Manage git worktrees (create, list, remove, prune).
- Check branches and status across repositories.
- Read commit history and create branches.
- Rebase, cherry-pick, and merge workflow automation.
- Run git bisect when a regression is detected.

**What it does NOT do:**
- Does not provide full repository hosting.
- Does not replace Bitbucket clone/pull/push (see Bitbucket orchestrator for those).

**Primary users:** AI agents managing worktrees and feature branches; human devops running merge pipelines.

## CLI Entry

```bash
vds-cli git --help
vds-cli git-orchestrator --help
```

## Key Commands

| Command | Purpose | Common Flags |
|---------|---------|-------------|
| `worktree-create` | Create a new worktree for a branch | `--branch`, `--path` |
| `worktree-list` | List active worktrees | `--repo` |
| `worktree-remove` | Remove a worktree directory | `--path` |
| `branch` | Create, list, or switch branches | `--name`, `--start-point` |
| `status` | Show modified, staged, and untracked files | `--repo` |
| `log` | Show commit history with stats | `--limit`, `--format` |
| `rebase` | Reapply commits on top of another branch | `--branch` |
| `merge` | Merge a branch into current | `--branch` |
| `stash` | Save and restore working changes | `--command` |
| `bisect` | Binary search to find bad commit | `--start`, `--bad` |

## Common Workflows

### Workflow 1: Feature Branch + Worktree
1. Create branch: `vds-cli git branch --name feat/who-docs-v2 --start-point master`.
2. Create worktree: `vds-cli git worktree-create --branch feat/who-docs-v2 --path worktrees/docs-v2`.
3. Make changes in isolated workspace.
4. Merge back: `vds-cli git merge --branch feat/who-docs-v2`.
5. Cleanup: `vds-cli git worktree-remove --path worktrees/docs-v2`.

### Workflow 2: Cherry-pick Fix Across Branches
1. Identify fix commit: `vds-cli git log --limit=5`.
2. Switch to target branch: `vds-cli git branch --name main`.
3. Cherry-pick: `vds-cli git cherry-pick --commit=abc1234`.

## Related

- **Orchestrators:** [bitbucket](bitbucket-orchestrator.md), [tasks](tasks-orchestrator.md), [progress](progress-orchestrator.md)
- **Skills:** [git-worktree-skill](../../../../vds-skills/skills/git-worktree-skill/SKILL.md)
- **GitNexus:** [gitnexus-workspace](../../../../vds-skills/skills/gitnexus-workspace-skill/SKILL.md)
