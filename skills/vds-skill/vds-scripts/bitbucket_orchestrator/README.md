# VDS Bitbucket Orchestrator

Python toolkit for Bitbucket operations using the `atlassian-python-api` SDK. Provides a unified CLI interface for
repository management, pull requests, pipelines, and Bitbucket automation.

## Quick Start

```bash
cd vds-scripts
# Optional: run the shared bootstrap to sync all packages
./scripts/bootstrap_uv.sh

# Package-specific sync & tests (only when you need dev deps)
uv sync --project bitbucket_orchestrator --extra dev
uv run --project bitbucket_orchestrator pytest
```

Run the CLI directly (uv automatically activates the project environment once the project has been synced at least
once):

```bash
# Using uv run (console script)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket --help

# Using the unified VDS CLI
./scripts/worktree_uv.sh run --project vds_cli vds-cli env load
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories PROJECT_KEY
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pull-requests PROJECT_KEY REPO_SLUG
```

**Agent-friendly output**
- When invoking via `vds-cli`, pass Typer flags after `--`, e.g. `vds-cli bitbucket -- --json-only projects`.
- `--json-only` emits clean JSON to stdout and skips writing reports/markdown (and suppresses logs).
- `--no-reports` keeps normal console output while avoiding filesystem writes.

## Available Commands

### Project Operations

- **`projects`** - List all Bitbucket projects

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects --limit 50
  ```

- **`create-project`** - Create a new project

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-project PROJECT_KEY "Project Name" \
    --description "Project description"
  ```

### Repository Operations

- **`repositories`** - List repositories in a project

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories PROJECT_KEY --limit 25
  ```

- **`repo`** - Repository CRUD operations (create/get/update/delete)

  ```bash
  # Get repository
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo get PROJECT_KEY REPO_SLUG

  # Create repository (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo create PROJECT_KEY REPO_SLUG --yes

  # Update repository description (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo update PROJECT_KEY REPO_SLUG \
    --description "Updated description" --yes

  # Delete repository (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo delete PROJECT_KEY REPO_SLUG --yes
  ```

- **Repository Management (Python client)** - Full CRUD operations via Python client

  ```python
  from vds_bitbucket_orchestrator.client import BitbucketClient
  from vds_bitbucket_orchestrator.config import load_settings

  settings = load_settings(strict=True)
  client = BitbucketClient(settings)

  # Create repository
  client.create_repository("INSURANCE", "vds-ai-memory", is_private=True)

  # Get repository
  repo = client.get_repository("INSURANCE", "vds-ai-memory")

  # Update repository
  client.update_repository("INSURANCE", "vds-ai-memory", description="Updated")

  # Delete repository (DANGER!)
  # client.delete_repository("INSURANCE", "vds-ai-memory")
  ```

  See `BITBUCKET_API_PRACTICES.md` for complete API reference aligned with
  [Atlassian Python API documentation](https://atlassian-python-api.readthedocs.io/bitbucket.html).

- **`fork`** - Fork repository operations

  ```bash
  # Fork repository within same project
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork create PROJECT_KEY REPO_SLUG \
    --new-repo REPO_FORK --yes

  # Fork repository to new project
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork create PROJECT_KEY REPO_SLUG \
    --new-project NEW_PROJECT_KEY --new-repo NEW_REPO_SLUG --yes

  # List forks of a repository
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork list PROJECT_KEY REPO_SLUG
  ```

  > **Note**: Fork operations require `--yes` flag for confirmation. The `list` action uses heuristic-based filtering
  > and may not capture all forks.

### Pull Request Operations

- **`pull-requests`** - List pull requests
  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pull-requests PROJECT_KEY REPO_SLUG \
    --state OPEN \
    --order newest \
    --limit 100
  ```

### Pull Request Management

Complete PR workflow automation from CLI:

> **Note**: When routing through `vds-cli`, pass Bitbucket global flags (e.g. `--json-only`, `--no-reports`, `--no-color`)
> immediately after `bitbucket` (or use `--`), e.g. `vds-cli bitbucket -- --json-only get-pr ...`.

#### Create and Review
```bash
# Create pull request
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Fix boundary timers" fix/ekyc-psj-fix-001 \
  --target release \
  --description "Fixes ENGINE-09005 errors" \
  --reviewers "user1,user2"

# Create draft PR and include required reviewers (best-effort; falls back if draft unsupported)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Draft: Payment validation" feature/payment-validation \
  --target develop \
  --draft \
  --include-required-reviewers

# Create cross-project PR (optional: override source/destination project/repo)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Cross project PR" feature/branch \
  --source-project PLATFORM --source-repo platform-repo \
  --dest-project INSURANCE --dest-repo insurance-repo \
  --target release

# Get PR details
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket get-pr EKYC ekyc-business 154

# Get PR details with commit list (best-effort)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket get-pr EKYC ekyc-business 154 \
  --include-commits --commit-limit 20

# View PR changes
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154

# View PR changes for a specific file + write JSON summary to disk
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154 \
  --file "src/main/resources/application.yml" \
  --output /tmp/pr_154_diff.json \
  --no-color

# Best-effort unified diff (only when API provides hunks)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154 --unified --no-color --output /tmp/pr_154.patch

# List PR activities
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-activities EKYC ekyc-business 154 --limit 10

# List only comment activities
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-activities EKYC ekyc-business 154 --type COMMENTED --limit 10

# List PR comments (derived from activities)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-comments EKYC ekyc-business 154 --limit 20

# List PR comments (threaded fields like parent/severity when available)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket list-pr-comments EKYC ekyc-business 154 --limit 20
```

#### Approve and Merge
```bash
# Add review comment
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "LGTM! Ready to merge."

# Inline-style comment or reply (best effort; falls back to general comment if server/SDK lacks support)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "Fix this typo" --file "src/main.java" --line 42

./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "Good catch!" --reply-to 123

# Approve PR
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket approve-pr EKYC ekyc-business 154 --yes

# Merge PR (requires --yes)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 --yes

# Merge with strategy, custom message, and close source branch
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 \
  --strategy squash \
  --message "Squash merge PR #154" \
  --close-source-branch \
  --yes

# Merge without approval check (not recommended)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 \
  --skip-approval-check --yes

# Or decline PR (requires --yes)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket decline-pr EKYC ekyc-business 154 --reason "Not meeting requirements" --yes
```

#### Remove Approval
```bash
# Unapprove PR
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket unapprove-pr EKYC ekyc-business 154 --yes
```

All commands support `--json-only` for clean JSON output and automatic markdown report generation.

### Pipeline Operations (Bitbucket Cloud Only)

- **`pipelines`** - List pipelines
  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipelines WORKSPACE REPOSITORY --limit 10
  ```

### User and Group Management

- **`groups`** - List all groups

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket groups --filter "developers" --limit 50
  ```

- **`project-users`** - List users with permissions for a project

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket project-users PROJECT_KEY \
    --filter "john" \
    --limit 25
  ```

- **`project-groups`** - List groups with permissions for a project

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket project-groups PROJECT_KEY \
    --filter "developers" \
    --limit 25
  ```

### Permission Management

- **`grant-group-repo`** - Grant group permissions to a repository

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket grant-group-repo PROJECT_KEY REPO_SLUG \
    GROUP_NAME write
  ```

- **`branch-permissions`** - Branch permissions management

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions get PROJECT_KEY --permission-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions set PROJECT_KEY \
    --matcher-type BRANCH --matcher-value "refs/heads/master" \
    --permission-type READ_ONLY --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions delete PROJECT_KEY --permission-id 1 --yes
  ```

- **`conditions`** - Conditions-Reviewers management

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions list PROJECT_KEY
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions get PROJECT_KEY --condition-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions create PROJECT_KEY \
    --condition-file condition.json --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions list PROJECT_KEY --repo REPO_SLUG
  ```

- **`code`** - Code/file content operations

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code file PROJECT_KEY REPO_SLUG --file "path/to/file.py"
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code commits PROJECT_KEY REPO_SLUG --limit 50
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code diff PROJECT_KEY REPO_SLUG \
    --file "path/to/file.py" --hash-oldest abc123 --hash-newest def456
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code changelog PROJECT_KEY REPO_SLUG \
    --ref-from master --ref-to develop
  ```

### Webhook Management (Bitbucket Cloud Only)

- **`webhooks`** - Manage repository webhooks
  ```bash
  # List webhooks (optionally filter by event, include statistics)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks list PROJECT_KEY REPO_SLUG --filter-event "repo:push"

  # Create a webhook (requires --yes confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks create PROJECT_KEY REPO_SLUG \
    --name "CI Hook" \
    --url "https://ci.example.com/bitbucket" \
    --event repo:push \
    --event pr:opened \
    --yes

  # Update a webhook
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks update PROJECT_KEY REPO_SLUG \
    --webhook-id 42 \
    --name "Updated Hook" \
    --set-inactive \
    --yes

  # Delete a webhook
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks delete PROJECT_KEY REPO_SLUG \
    --webhook-id 42 \
    --yes
  ```

### Cloud Workspace Operations (Bitbucket Cloud Only)

- **`workspace`** - Manage Cloud workspaces
  ```bash
  # List all workspaces
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace list

  # Get workspace details
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace get --workspace-slug workspace1

  # Get workspace permissions
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace permissions --workspace-slug workspace1

  # Get repository permissions in workspace
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace permissions --workspace-slug workspace1 --repo-slug repo1

  # List projects in workspace
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace projects --workspace-slug workspace1

  # Get specific project from workspace
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace project --workspace-slug workspace1 --project-key PROJ1
  ```

### Repository Variables (Bitbucket Cloud Only)

- **`repo-variables`** – Manage repository-level pipeline variables
  ```bash
  # List repository variables (JSON output with --no-markdown)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables list \
    --workspace team-slug \
    --repo-slug repo-slug \
    --no-markdown

  # Get a single variable by UUID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables get \
    --workspace team-slug \
    --repo-slug repo-slug \
    --uuid {variable-uuid} \
    --no-markdown

  # Create a secured variable (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables create \
    --workspace team-slug \
    --repo-slug repo-slug \
    --key API_TOKEN \
    --value "super-secret" \
    --secured true \
    --yes \
    --no-markdown

  # Update an existing variable (key/value/secured)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables update \
    --workspace team-slug \
    --repo-slug repo-slug \
    --uuid {variable-uuid} \
    --value "rotate-me" \
    --yes \
    --no-markdown

  # Delete a variable
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables delete \
    --workspace team-slug \
    --repo-slug repo-slug \
    --uuid {variable-uuid} \
    --yes \
    --no-markdown
  ```

### Repository Issues (Bitbucket Cloud Only)

- **`issue`** – Manage repository issues when Bitbucket Issues tracker is enabled
  ```bash
  # List issues (with optional query/sort)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue list \
    --workspace team-slug \
    --repo-slug repo-slug \
    --query 'state = "open"' \
    --sort -updated_on \
    --no-markdown

  # Create an issue
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue create \
    --workspace team-slug \
    --repo-slug repo-slug \
    --title "Production bug" \
    --description "Steps to reproduce..." \
    --kind bug \
    --priority critical \
    --no-markdown

  # Update an issue (title/state/kind/priority/description)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue update \
    --workspace team-slug \
    --repo-slug repo-slug \
    --issue-id 123 \
    --state resolved \
    --no-markdown

  # Delete an issue (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue delete \
    --workspace team-slug \
    --repo-slug repo-slug \
    --issue-id 123 \
    --yes \
    --no-markdown
  ```

### Advanced Pipeline Operations (Bitbucket Cloud Only)

- **`pipeline-advanced`** – Inspect pipelines, steps, logs, and stop executions
  ```bash
  # Get pipeline details
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced get \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pipeline-uuid {pipeline-uuid} \
    --no-markdown

  # List steps for a pipeline
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced steps \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pipeline-uuid {pipeline-uuid} \
    --no-markdown

  # Get a specific step
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced step \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pipeline-uuid {pipeline-uuid} \
    --step-uuid {step-uuid} \
    --no-markdown

  # Fetch pipeline step log (optionally provide byte range)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced log \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pipeline-uuid {pipeline-uuid} \
    --step-uuid {step-uuid} \
    --start 0 \
    --end 5000 \
    --output ./logs/{pipeline-uuid}-{step-uuid}.log

  # Stop a running pipeline (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced stop \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pipeline-uuid {pipeline-uuid} \
    --yes \
    --no-markdown
  ```

### Pull Request Blockers (Bitbucket Cloud Only)

- **`pr-blocker`** – Manage blocker comments on pull requests
  ```bash
  # List blockers on a pull request
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker list \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pull-request-id 123 \
    --no-markdown

  # Add a blocker (optional reason/severity)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker add \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pull-request-id 123 \
    --message "Pending security review" \
    --reason "Security" \
    --severity HIGH \
    --no-markdown

  # Delete a blocker (requires --yes)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker delete \
    --workspace team-slug \
    --repo-slug repo-slug \
    --pull-request-id 123 \
    --blocker-uuid {blocker-uuid} \
    --yes \
    --no-markdown
  ```

### Commit Status (Bitbucket Server/DC)

- **`commit-status`** - Bitbucket Server/Data Center build statuses for a commit. Usage: `vds-cli bitbucket commit-status get <PROJECT> <REPO> <COMMIT> [--limit N] [--key KEY]`
  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket commit-status get PROJECT_KEY REPO_SLUG COMMIT_ID \
    --limit 20 \
    --key "ci"
  ```

### Code Insights (Bitbucket Cloud Only)

- **`code-insights`** - Manage Code Insights reports
  ```bash
  # Get a report
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights get PROJECT_KEY REPO_SLUG COMMIT_ID \
    --report-key "test-report"

  # Create a report
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights create PROJECT_KEY REPO_SLUG COMMIT_ID \
    --report-key "coverage-report" \
    --title "Coverage Report" \
    --reporter "coverage-tool" \
    --result "PASSED" \
    --data-file coverage-data.json \
    --report-type "COVERAGE" \
    --yes

  # Add annotations to a report
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights annotate PROJECT_KEY REPO_SLUG COMMIT_ID \
    --report-key "test-report" \
    --annotations-file annotations.json \
    --yes

  # Delete a report
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights delete PROJECT_KEY REPO_SLUG COMMIT_ID \
    --report-key "test-report" \
    --yes
  ```

### Repository Settings

- **`repo-settings`** - Manage repository settings
  ```bash
  # Branching model
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings branching-model get PROJECT_KEY REPO_SLUG
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings branching-model set PROJECT_KEY REPO_SLUG \
    --model-file branching-model.json --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings branching-model enable PROJECT_KEY REPO_SLUG --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings branching-model disable PROJECT_KEY REPO_SLUG --yes

  # Default branch
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings default-branch get PROJECT_KEY REPO_SLUG
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings default-branch set PROJECT_KEY REPO_SLUG \
    --branch "main" --yes

  # Repository hooks
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings hooks get PROJECT_KEY REPO_SLUG \
    --start 0 --limit 50
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings hooks enable PROJECT_KEY REPO_SLUG \
    --hook-key "com.atlassian.bitbucket.server.bitbucket-bundle:force-push-hook" --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings hooks disable PROJECT_KEY REPO_SLUG \
    --hook-key "com.atlassian.bitbucket.server.bitbucket-bundle:force-push-hook" --yes

  # Git LFS
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings lfs get PROJECT_KEY REPO_SLUG
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings lfs set PROJECT_KEY REPO_SLUG \
    --enabled --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings lfs set PROJECT_KEY REPO_SLUG \
    --disabled --yes
  ```

### Advanced Code Operations

- **`code-advanced`** - Advanced code operations
  ```bash
  # List files in repository
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced file-list \
    --project-key PROJECT_KEY \
    --repository-slug REPO_SLUG \
    --sub-folder "src" \
    --query "*.py" \
    --start 0 \
    --limit 100

  # Get commit information
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced commit-info \
    --project-key PROJECT_KEY \
    --repository-slug REPO_SLUG \
    --commit "abc123" \
    --path "file.py"

  # Get commit changes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced commit-changes \
    --project-key PROJECT_KEY \
    --repository-slug REPO_SLUG \
    --commit-id "abc123" \
    --merges "exclude"

  # Search code (Cloud-only)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced search \
    --team "workspace" \
    --search-query "def test_function" \
    --page 1 \
    --limit 20

  # Advanced code search with repository filter (Cloud-only)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced search-advanced \
    --team "workspace" \
    --search-query "class MyClass" \
    --repository "repo-slug" \
    --page 1 \
    --limit 50
  ```
  > **Note**: Code search operations are Cloud-only. Server/DC instances do not support code search via REST API. The
  > `search-advanced` action includes repository filtering capabilities.

## Configuration

The orchestrator uses environment variables from the shared VDS env file:

```bash
# Required for authentication
VDS_USERNAME=your-username
VDS_PASSWORD=your-password

# Optional: Use token instead of username/password
BITBUCKET_ACCESS_TOKEN=your-api-token

# Bitbucket base URL (defaults based on mode detection)
BITBUCKET_BASE_URL=https://bitbucket.digital.vn

# For Bitbucket Cloud, specify workspace
BITBUCKET_CLOUD_WORKSPACE=your-workspace
```

The orchestrator automatically detects whether you're using Bitbucket Cloud or Server/Data Center based on the URL and
configuration.

## Project Layout

- `src/vds_bitbucket_orchestrator/config.py` – Environment configuration and settings
- `src/vds_bitbucket_orchestrator/client.py` – Bitbucket client using atlassian-python-api SDK
- `src/vds_bitbucket_orchestrator/cli.py` – Typer CLI interface
- `src/vds_bitbucket_orchestrator/errors.py` – Custom error types
- `tests/` – pytest test suite

## Feature Coverage

The orchestrator implements **121+ methods** covering core Bitbucket operations. For a complete feature coverage
reference and SDK comparison, see [`ATLASSIAN_FEATURES_REFERENCE.md`](../ATLASSIAN_FEATURES_REFERENCE.md).

**Current Coverage**: ~51% of atlassian-python-api SDK features

**Recently Added**:

- ✅ Advanced code search (search-advanced with repository filter) - **NEW**
- ✅ Fork repository operations (create, list) - **NEW**
- ✅ Cloud Workspace Operations (list, get, permissions, projects, project) - **NEW**
- ✅ Branch permissions management
- ✅ Code/file content operations
- ✅ Conditions-Reviewers management
- ✅ Webhook management (Cloud-only)
- ✅ Code Insights reports and annotations (Cloud-only) - **NEW**
- ✅ Repository settings (branching model, default branch, hooks, LFS) - **NEW**
- ✅ Advanced code operations (file listing, commit info, commit changes, code search) - **NEW**
- ✅ Repository variables (Cloud-only) - **NEW**
- ✅ Deployment environments & variables (Cloud-only) - **NEW**
- ✅ Advanced pipeline operations (Cloud-only) - **NEW**
- ✅ Pull request blockers (Cloud-only) - **NEW**

**Note**: Default reviewers are managed through Conditions-Reviewers (see `conditions` command)

## Advanced Features

The `BitbucketClient` class provides many additional methods beyond the CLI:

### Repository Management

- `get_repository()`, `create_repository()`, `update_repository()`
- `get_repository_labels()`, `set_repository_label()`

### Pull Request Management

- `create_pull_request()`, `get_pull_request()`
- `add_pull_request_comment()`, `get_pull_request_activities()`
- `get_pull_request_changes()`, `delete_pull_request()`, `merge_pull_request()`

### Branch and Tag Management

- `get_branches()`, `create_branch()`, `delete_branch()`
- `get_tags()`, `set_tag()`, `delete_tag()`

### Pipeline Management (Cloud Only)

- `trigger_pipeline()`

### Permission Management

- `grant_user_repository_permissions()`, `grant_user_project_permissions()`
- `grant_group_project_permissions()`, `grant_group_repository_permissions()`

### Branch Permissions

- `set_branches_permissions()` - Set branch permissions
- `get_branch_permission()` - Get branch permission
- `delete_branch_permission()` - Delete branch permission

### Conditions-Reviewers Management

- `get_project_conditions()`, `get_project_condition()` - Get project conditions
- `create_project_condition()`, `update_project_condition()`, `delete_project_condition()` - Manage project conditions
- `get_repo_conditions()`, `get_repo_condition()` - Get repository conditions
- `create_repo_condition()`, `update_repo_condition()`, `delete_repo_condition()` - Manage repository conditions

### Code Management

- `get_content_of_file()` - Get file content
- `get_commits()` - Get commits
- `get_diff()` - Get diff between commits
- `get_changelog()` - Get changelog between refs

### Webhook Management (Cloud Only)

- `list_webhooks()` - List repository webhooks
- `get_webhook()` - Retrieve a webhook
- `create_webhook()` - Create a webhook
- `update_webhook()` - Update webhook metadata/events
- `delete_webhook()` - Delete a webhook

These can be accessed programmatically:

```python
from vds_bitbucket_orchestrator.client import BitbucketClient
from vds_bitbucket_orchestrator.config import BitbucketSettings, load_settings

settings = load_settings(strict=True)
with BitbucketClient(settings) as client:
    projects = client.list_projects(limit=50)
    repos = client.list_repositories("PROJECT_KEY", limit=25)
    prs = client.list_pull_requests("PROJECT_KEY", "REPO_SLUG", state="OPEN")
```

## Retry Logic

The orchestrator includes comprehensive retry logic with exponential backoff:

- Automatic retry on transport errors and rate limiting
- Configurable retry attempts and backoff factor
- Intelligent error classification (retryable vs non-retryable)
- Structured logging for retry attempts

## Cloud vs Server Mode

The orchestrator automatically detects the Bitbucket mode:

- **Cloud Mode**: Detected when URL contains `bitbucket.org` or `cloud.bitbucket.org`
- **Server/Data Center Mode**: Detected for on-premise installations

Some features (like pipelines) are only available in Cloud mode.

## Run Reports

Run reports are written to `~/.cache/vds-bitbucket-reports/` (plus Markdown unless `--no-markdown` is used).

## Linting

We use Ruff for linting/formatting:

```bash
uv run --extra dev ruff check
uv run --extra dev ruff format
```

## Testing

```bash
# Run all tests
uv run --extra dev pytest

# Run specific test file
uv run --extra dev pytest tests/test_cli.py

# Run with coverage
uv run --extra dev pytest --cov=src/vds_bitbucket_orchestrator
```

## Error Handling

The orchestrator provides structured error types:

- `BitbucketAuthError` - Authentication failures
- `BitbucketNotFoundError` - Resource not found (404)
- `BitbucketRateLimitedError` - Rate limit exceeded (429)
- `BitbucketConflictError` - Conflict errors (409)
- `BitbucketResponseError` - Server errors (500)
- `BitbucketTransportError` - Network/connection errors
- `BitbucketRetryError` - Retry attempts exhausted
- `BitbucketClientError` - General client errors

All errors include context information for debugging.
