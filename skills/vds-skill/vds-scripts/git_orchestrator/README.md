# VDS Git Orchestrator

Python-based replacement for the legacy bash bulk git workflow. Key goals:

- Async git operations across LEP, INSURANCE, and EKYC repositories.
- Manifest-driven configuration with rich filtering for AI agents or operators.
- Structured logging (JSON + console) and aggregated run summaries under `reports/git_runs/`.
- Optional pre/post hooks per repository.
- uv-managed Python project targeting Python 3.14.

## Setup

**Important**: You can run git orchestrator commands from **any location** - you never need to `cd` into individual repositories. The orchestrator automatically resolves repository paths using absolute paths from the manifest.

**Manifest note**: direct `vds-git-orchestrator ...` usage still depends on manifest discovery (or an explicit manifest path) from the current execution context. For normal operator workflows, prefer routed `vds-cli git ...` from the `vds-scripts` workspace root so manifest resolution and regeneration follow the standard workspace conventions.

The project uses [uv](https://docs.astral.sh/uv/) to manage Python environments.

```bash
# Install and lock dependencies from the workspace root
cd WHO-project/vds-scripts
./scripts/worktree_uv.sh sync --project git_orchestrator

# Optional: run the CLI directly (or use unified vds-cli)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli git --help

# If vds-cli fails to import (ModuleNotFoundError: vds_cli),
# reinstall vds_cli in non-editable mode:
./scripts/worktree_uv.sh sync --project vds_cli --no-editable

# Customize the manifest as needed
cp repo-manifest.yaml repo-manifest.local.yaml
```

**Key Points**:

- **No directory changes needed**: All git operations use absolute paths - you can run commands from `vds-scripts/`, monorepo root, or any location
- **Manifest path resolution**: The orchestrator automatically finds the manifest and resolves repository paths relative to it
- **Individual repositories**: You never need to `cd` into `LEP-project/document-management` or any other repository directory

`vds-scripts/repo-manifest.yaml` contains the default repository catalogue consumed by the VDS CLI. Use
`repo-manifest.yaml.example` as a template when layering additional tags or hooks.

## CLI Usage

**All operations run from a central location** - you **never need to `cd` into individual repositories**. The orchestrator uses absolute paths from the manifest to execute git commands in each repository automatically.

**Example**: Instead of manually doing:
```bash
cd LEP-project/document-management && git pull
cd ../insurance-payment-service && git pull
```

You simply run:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "*document-management"
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "*payment*"
```

All from a single location - no directory navigation required!

### Individual Repository Operations

Filter by repository name using `--match` pattern:

```bash
# Single repository by exact name
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "document-management"

# Single repository by pattern
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --match "*payment-service"

# Single repository checkout with tracking
./scripts/worktree_uv.sh run --project vds_cli vds-cli git checkout origin/release --match "*document-management"
```

### Group Operations

Filter by project, pattern, or tags:

```bash
# All repositories in a project
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --project insurance

# Multiple repositories matching a pattern
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "*notification*"

# Combined filters (project + pattern)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --project insurance --match "*payment*"
```

### Common Operations

```bash
# Fast-forward every repo defined in the manifest
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull

# Preview the repo list without touching git
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "*notification*" --dry-run

# Fetch a tagged subset and emit JSON logs + reports
./scripts/worktree_uv.sh run --project vds_cli vds-cli git fetch --tag frontend --json-log

# Show status deltas for EKYC services
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --project ekyc

# Clone missing LEP repositories (retry falls back to default branch)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git clone --project lep

# List repositories matching a pattern
./scripts/worktree_uv.sh run --project vds_cli vds-cli git list --match "*notification*"

# Branch operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli git branch list --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git branch create --name feature/new-feature --project lep

# Checkout operations (use origin/branch for automatic tracking)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git checkout origin/release --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git checkout feature/new --create --project lep

# Stage files
./scripts/worktree_uv.sh run --project vds_cli vds-cli git add --all --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git add src/main.py README.md --project lep

# Commit changes
./scripts/worktree_uv.sh run --project vds_cli vds-cli git commit "Update documentation" --project insurance

# Push to remote
./scripts/worktree_uv.sh run --project vds_cli vds-cli git push --branch main --project insurance

# View commit history
./scripts/worktree_uv.sh run --project vds_cli vds-cli git log --limit 10 --oneline --project lep

# Show differences
./scripts/worktree_uv.sh run --project vds_cli vds-cli git diff --staged --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git diff src/main.py --project lep

# Stash operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli git stash list --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git stash save "WIP: feature work" --project lep
./scripts/worktree_uv.sh run --project vds_cli vds-cli git stash pop --project insurance

# Tag operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli git tag list --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git tag create --name v1.0.0 --message "Release v1.0.0" --project lep

# Remote operations
./scripts/worktree_uv.sh run --project vds_cli vds-cli git remote list --project insurance
```

Filter flags can be combined:

| Flag | Purpose | |------|---------| | `--project <id>` | Restrict to a project (`lep`, `insurance`, `ekyc`, etc.) | |
`--match <pattern>` | Unix shell-style match against repo name | | `--tag/--skip-tag` | Include or exclude
manifest-defined tags | | `--dry-run` | Available for `pull`, `fetch`, `clone`, `branch`, `checkout`, `add`, `commit`,
`push`, `stash`, and `tag` when you want to preview work | | `--concurrency <n>` | Override the default parallelism
(`min(8, max(2, cpu_count/2))` by default) | | `--manifest/-m` | Merge additional manifest files at runtime | |
`--json-log` | Emit structured logs alongside the rich console output |

## Available Commands

### Core Operations

- **`pull`** - Fetch and fast-forward repositories
- **`fetch`** - Fetch latest refs without fast-forward
- **`status`** - Show git status for repositories
- **`clone`** - Clone missing repositories
- **`list`** - List repositories from manifest

### Branch Management

- **`branch`** - List, create, or delete branches
  - Actions: `list`, `create`, `delete`
  - Use `--name` for create/delete operations

### Checkout Operations

- **`checkout`** - Checkout a branch or path
  - Use `--create` or `-b` to create a new branch

### Staging and Committing

- **`add`** - Stage files for commit
  - Use `--all` or `-A` to stage all files
  - Or specify file paths as arguments
- **`commit`** - Commit staged changes
  - Requires commit message as argument

### Remote Operations

- **`push`** - Push commits to remote
  - Use `--branch` to specify branch
  - Use `--remote` to specify remote name
- **`remote`** - List, add, or remove remotes
  - Actions: `list`, `add`, `remove`
  - Use `--name` and `--url` for add operation

### History and Diff

- **`log`** - Show commit history
  - Use `--limit` or `-n` to limit number of commits
  - Use `--oneline` for compact output
- **`diff`** - Show changes
  - Use `--staged` to show staged changes
  - Specify file paths as arguments

### Stash Operations

- **`stash`** - Stash or restore working directory changes
  - Actions: `list`, `save`, `pop`, `apply`, `drop`
  - Use `--message` or `-m` for save operation

### Tag Management

- **`tag`** - List, create, or delete tags
  - Actions: `list`, `create`, `delete`
  - Use `--name` for create/delete operations
  - Use `--message` or `-m` for annotated tags

Every run produces a timestamped JSON report (`reports/git_runs/git-run-*.json`) capturing per-repo outcomes, filters,
and run metadata. Add the directory to your `.gitignore` if you store reports locally.

When Bitbucket throttles concurrent HTTP sessions, the orchestrator automatically retries failed repositories serially
(concurrency = 1) if the error message indicates a network failure.

## Integration with `vds-cli`

The unified VDS CLI (`./scripts/worktree_uv.sh run --project vds_cli vds-cli git`) delegates all git operations to this
orchestrator. The CLI automatically passes the default manifest and honours the `VDS_GIT_CONCURRENCY` environment
variable when present. Set `VDS_GIT_CONCURRENCY_DEFAULT` to adjust the fallback concurrency, and
`VDS_BITBUCKET_HTTP_BASE` if you need to target an alternate Bitbucket host.

Examples:

```bash
# Individual repository operations (using --match)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --match "document-management"
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --match "*payment-service"

# Group operations (using --project, patterns, or tags)
./scripts/worktree_uv.sh run --project vds_cli vds-cli git pull --project lep --dry-run
./scripts/worktree_uv.sh run --project vds_cli vds-cli git status --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git branch list --project ekyc
./scripts/worktree_uv.sh run --project vds_cli vds-cli git checkout origin/release --project lep
./scripts/worktree_uv.sh run --project vds_cli vds-cli git add --all --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git commit "Update docs" --project lep
./scripts/worktree_uv.sh run --project vds_cli vds-cli git push --branch main --project insurance
./scripts/worktree_uv.sh run --project vds_cli vds-cli git log --limit 10 --oneline --project ekyc
```

## Hooks

Repositories can declare optional hooks in the manifest for various operations. Hooks are shell commands executed inside
the repository directory. Supported hooks:

- `pre_pull`, `post_pull` - Before/after pull operations
- `pre_fetch`, `post_fetch` - Before/after fetch operations
- `pre_status`, `post_status` - Before/after status operations
- `pre_branch`, `post_branch` - Before/after branch operations
- `pre_checkout`, `post_checkout` - Before/after checkout operations
- `pre_add`, `post_add` - Before/after add operations
- `pre_commit`, `post_commit` - Before/after commit operations
- `pre_push`, `post_push` - Before/after push operations
- `pre_stash`, `post_stash` - Before/after stash operations
- `pre_tag`, `post_tag` - Before/after tag operations

Example:

```yaml
hooks:
  pre_pull:
    - "scripts/check-env.sh"
  post_pull:
    - "./mvnw --quiet -DskipTests package"
  pre_commit:
    - "npm run lint"
  post_commit:
    - "git log -1 --oneline"
```

## Tests

```bash
uv --project vds-scripts/git_orchestrator run --extra tests pytest vds-scripts/git_orchestrator/tests
```
