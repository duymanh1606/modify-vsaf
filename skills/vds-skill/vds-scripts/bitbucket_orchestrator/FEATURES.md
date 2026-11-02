# VDS Bitbucket Orchestrator - Complete Feature Overview

**Last Updated**: 2026-01-21
**Version**: Current (with PR management enhancements)
**Status**: Production-ready (manual API validation pending)

---

## Overview

The VDS Bitbucket Orchestrator is a comprehensive Python toolkit for Bitbucket operations using the `atlassian-python-api` SDK. It provides a unified CLI interface for repository management, pull requests, pipelines, permissions, and Bitbucket automation across both **Bitbucket Server/Data Center** and **Bitbucket Cloud**.

**Key Capabilities**:
- ✅ **34 CLI commands** covering all major Bitbucket operations
- ✅ **Full PR lifecycle management** (create, approve, merge, decline, comment, diff, activities)
- ✅ **Dual mode support** (Server/Data Center + Cloud)
- ✅ **Agent-friendly output** (JSON, markdown reports, structured logging)
- ✅ **Comprehensive error handling** with retry logic
- ✅ **289/289 tests passing**

---

## Feature Categories

### 1. Project Operations (2 commands)

#### `projects`
List all Bitbucket projects with filtering and pagination.

**Features**:
- Filter by keyword
- Limit results
- JSON output support
- Markdown reports

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket projects --limit 50
```

#### `create-project`
Create a new Bitbucket project.

**Features**:
- Project key and name
- Optional description
- JSON output
- Markdown reports

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-project PROJECT_KEY "Project Name" \
  --description "Project description"
```

---

### 2. Repository Operations (3 commands)

#### `repositories`
List repositories in a project with filtering and pagination.

**Features**:
- Filter by keyword
- Limit results
- JSON output
- Markdown reports

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repositories PROJECT_KEY --limit 25
```

#### Repository Management (Python Client)
Full CRUD operations via `BitbucketClient`:
- `create_repository()` - Create repository
- `get_repository()` - Get repository details
- `update_repository()` - Update repository settings
- `delete_repository()` - Delete repository (dangerous!)

#### `fork`
Fork repository operations.

**Features**:
- Fork within same project
- Fork to new project
- List forks of a repository
- Requires `--yes` for confirmation

**Example**:
```bash
# Fork within same project
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork create PROJECT_KEY REPO_SLUG \
  --new-repo REPO_FORK --yes

# Fork to new project
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork create PROJECT_KEY REPO_SLUG \
  --new-project NEW_PROJECT_KEY --new-repo NEW_REPO_SLUG --yes

# List forks
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket fork list PROJECT_KEY REPO_SLUG
```

---

### 3. Pull Request Operations (12 commands)

#### `pull-requests`
List pull requests with filtering.

**Features**:
- Filter by state (OPEN, MERGED, DECLINED)
- Sort order (newest, oldest)
- Limit results
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pull-requests PROJECT_KEY REPO_SLUG \
  --state OPEN --order newest --limit 100
```

#### `create-pr` ⭐ **Enhanced**
Create pull requests with full workflow support.

**Features**:
- Same-project and cross-project PRs
- Draft PR support (best-effort with fallback)
- Include required reviewers from policy
- Custom reviewers list
- Title, description, source/target branches
- JSON output with PR ID and URL
- Markdown reports with timestamps

**Enhancements Beyond Spec**:
- `--include-required-reviewers` flag (auto-include required reviewers)

**Example**:
```bash
# Standard PR
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Fix boundary timers" fix/ekyc-psj-fix-001 \
  --target release --description "Fixes ENGINE-09005" --reviewers "user1,user2"

# Draft PR with required reviewers
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Draft: Payment validation" feature/payment-validation \
  --target develop --draft --include-required-reviewers

# Cross-project PR
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket create-pr EKYC ekyc-business \
  "Cross project PR" feature/branch \
  --source-project PLATFORM --source-repo platform-repo \
  --dest-project INSURANCE --dest-repo insurance-repo --target release
```

#### `get-pr` ⭐ **Enhanced**
Get detailed PR information with mergeability status.

**Features**:
- Full PR metadata (title, description, author, reviewers, state)
- Mergeability status (can merge, conflicts, vetoes)
- Optional commit list expansion (best-effort)
- Commit limit control
- JSON output
- Markdown reports

**Example**:
```bash
# Basic PR details
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket get-pr EKYC ekyc-business 154

# With commit list
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket get-pr EKYC ekyc-business 154 \
  --include-commits --commit-limit 20
```

#### `approve-pr` ⭐ **Enhanced**
Approve pull requests.

**Features**:
- Requires `--yes` flag for safety
- JSON output
- Markdown reports with ISO 8601 timestamps (`approved_at`)

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket approve-pr EKYC ekyc-business 154 --yes
```

#### `unapprove-pr` ⭐ **Enhanced**
Remove approval from pull requests.

**Features**:
- Requires `--yes` flag for safety
- JSON output
- Markdown reports with ISO 8601 timestamps (`unapproved_at`)

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket unapprove-pr EKYC ekyc-business 154 --yes
```

#### `merge-pr` ⭐ **Enhanced**
Merge pull requests with strategy selection and safety checks.

**Features**:
- Merge strategies: `merge-commit`, `squash`, `fast-forward`, `rebase` (best-effort)
- Pre-merge approval check (warns if no approvals)
- Server-side validation (conflicts, permissions, build status)
- Optimistic locking via version parameter
- Custom merge commit message
- Auto-close source branch option
- Requires `--yes` flag
- JSON output
- Markdown reports

**Enhancements Beyond Spec**:
- `--message` / `-m` for custom merge commit message
- `--close-source-branch` to close source branch after merge
- `rebase` strategy (best-effort alias for fast-forward with warning)

**Example**:
```bash
# Standard merge
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 --yes

# Squash merge with custom message and close branch
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 \
  --strategy squash --message "Squash merge PR #154" --close-source-branch --yes

# Skip approval check (not recommended)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket merge-pr EKYC ekyc-business 154 \
  --skip-approval-check --yes
```

#### `decline-pr` ⭐ **Enhanced**
Decline/reject pull requests.

**Features**:
- Optional decline reason/comment (adds comment before declining)
- Requires `--yes` flag
- JSON output
- Markdown reports with ISO 8601 timestamps (`declined_at`)

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket decline-pr EKYC ekyc-business 154 \
  --reason "Not meeting requirements" --yes
```

#### `comment-pr` ⭐ **Best-Effort**
Add comments to pull requests.

**Features**:
- General PR comments
- Inline comments (best-effort: `--file` + `--line`, falls back to general comment with context)
- Reply to comments (best-effort: `--reply-to`, falls back to general comment)
- Markdown formatting support
- JSON output with comment ID
- Markdown reports

**Example**:
```bash
# General comment
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "LGTM! Ready to merge."

# Inline-style comment (best-effort)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "Fix this typo" --file "src/main.java" --line 42

# Reply to comment (best-effort)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket comment-pr EKYC ekyc-business 154 \
  --text "Good catch!" --reply-to 123
```

#### `pr-comments`
List PR comments (simple version, derived from activities).

**Features**:
- Limit results
- JSON output
- Markdown reports

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-comments EKYC ekyc-business 154 --limit 20
```

#### `list-pr-comments`
List PR comments with threaded fields (parent, severity, etc.).

**Features**:
- Limit results
- Threaded comment fields when available
- JSON output
- Markdown reports

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket list-pr-comments EKYC ekyc-business 154 --limit 20
```

#### `pr-diff` ⭐ **Best-Effort**
View PR diffs with multiple output formats.

**Features**:
- Summary format (default): File-level change list + UI URL
- Unified diff format (best-effort: `--unified`, only when API provides hunks)
- File-specific filtering (`--file`)
- Context lines control (`--context`)
- Output to file (`--output`: JSON for summary, plain text for unified)
- Color control (`--no-color`)
- JSON output

**Example**:
```bash
# Summary format
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154

# File-specific with JSON output
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154 \
  --file "src/main/resources/application.yml" --output /tmp/pr_154_diff.json --no-color

# Unified diff (best-effort)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-diff EKYC ekyc-business 154 \
  --unified --context 3 --no-color --output /tmp/pr_154.patch
```

#### `pr-activities`
List PR activities with filtering.

**Features**:
- Filter by activity type (`--type`: COMMENTED, APPROVED, MERGED, etc.)
- Limit results
- JSON output
- Markdown reports

**Example**:
```bash
# All activities
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-activities EKYC ekyc-business 154 --limit 10

# Only comments
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-activities EKYC ekyc-business 154 \
  --type COMMENTED --limit 10
```

---

### 4. User and Group Management (3 commands)

#### `groups`
List all Bitbucket groups.

**Features**:
- Filter by keyword
- Limit results
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket groups --filter "developers" --limit 50
```

#### `project-users`
List users with permissions for a project.

**Features**:
- Filter by keyword
- Limit results
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket project-users PROJECT_KEY \
  --filter "john" --limit 25
```

#### `project-groups`
List groups with permissions for a project.

**Features**:
- Filter by keyword
- Limit results
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket project-groups PROJECT_KEY \
  --filter "developers" --limit 25
```

---

### 5. Permission Management (3 commands)

#### `grant-group-repo`
Grant group permissions to a repository.

**Features**:
- Permission levels (read, write, admin)
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket grant-group-repo PROJECT_KEY REPO_SLUG \
  GROUP_NAME write
```

#### `branch-permissions`
Branch permissions management.

**Features**:
- Get permission by ID
- Set permissions (matcher type, matcher value, permission type)
- Delete permissions
- Requires `--yes` for write operations

**Example**:
```bash
# Get permission
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions get PROJECT_KEY --permission-id 1

# Set permission
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions set PROJECT_KEY \
  --matcher-type BRANCH --matcher-value "refs/heads/master" \
  --permission-type READ_ONLY --yes

# Delete permission
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket branch-permissions delete PROJECT_KEY \
  --permission-id 1 --yes
```

#### `conditions`
Conditions-Reviewers management.

**Features**:
- List conditions (project-level or repo-level)
- Get condition by ID
- Create condition from JSON file
- Delete condition
- Requires `--yes` for write operations

**Example**:
```bash
# List project conditions
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions list PROJECT_KEY

# Get condition
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions get PROJECT_KEY --condition-id 1

# Create condition
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions create PROJECT_KEY \
  --condition-file condition.json --yes

# List repo conditions
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket conditions list PROJECT_KEY --repo REPO_SLUG
```

---

### 6. Code Operations (2 commands)

#### `code`
Basic code/file content operations.

**Features**:
- Get file content (`file` action)
- List commits (`commits` action)
- Get diff between commits (`diff` action)
- Get changelog between refs (`changelog` action)

**Example**:
```bash
# Get file content
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code file PROJECT_KEY REPO_SLUG \
  --file "path/to/file.py"

# List commits
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code commits PROJECT_KEY REPO_SLUG --limit 50

# Get diff
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code diff PROJECT_KEY REPO_SLUG \
  --file "path/to/file.py" --hash-oldest abc123 --hash-newest def456

# Get changelog
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code changelog PROJECT_KEY REPO_SLUG \
  --ref-from master --ref-to develop
```

#### `code-advanced`
Advanced code operations.

**Features**:
- List files in repository (`file-list` action)
- Get commit information (`commit-info` action)
- Get commit changes (`commit-changes` action)
- Search code (Cloud-only: `search` action)
- Advanced code search with repository filter (Cloud-only: `search-advanced` action)

**Example**:
```bash
# List files
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced file-list \
  --project-key PROJECT_KEY --repository-slug REPO_SLUG \
  --sub-folder "src" --query "*.py" --start 0 --limit 100

# Get commit info
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced commit-info \
  --project-key PROJECT_KEY --repository-slug REPO_SLUG \
  --commit "abc123" --path "file.py"

# Search code (Cloud-only)
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-advanced search \
  --team "workspace" --search-query "def test_function" --page 1 --limit 20
```

---

### 7. Pipeline Operations (2 commands) - Cloud Only

#### `pipelines`
List pipelines.

**Features**:
- Filter by state
- Limit results
- JSON output

**Example**:
```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipelines WORKSPACE REPOSITORY --limit 10
```

#### `pipeline-advanced`
Advanced pipeline operations.

**Features**:
- Get pipeline details (`get` action)
- List pipeline steps (`steps` action)
- Get specific step (`step` action)
- Fetch step logs (`log` action) with byte range support
- Stop running pipeline (`stop` action, requires `--yes`)

**Example**:
```bash
# Get pipeline details
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced get \
  --workspace team-slug --repo-slug repo-slug --pipeline-uuid {uuid} --no-markdown

# Get step log
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced log \
  --workspace team-slug --repo-slug repo-slug \
  --pipeline-uuid {uuid} --step-uuid {step-uuid} \
  --start 0 --end 5000 --output ./logs/{uuid}-{step-uuid}.log

# Stop pipeline
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pipeline-advanced stop \
  --workspace team-slug --repo-slug repo-slug --pipeline-uuid {uuid} --yes
```

---

### 8. Webhook Management (1 command) - Cloud Only

#### `webhooks`
Manage repository webhooks.

**Features**:
- List webhooks (filter by event, include statistics)
- Create webhook (requires `--yes`)
- Update webhook (name, URL, events, active/inactive)
- Delete webhook (requires `--yes`)

**Example**:
```bash
# List webhooks
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks list PROJECT_KEY REPO_SLUG \
  --filter-event "repo:push"

# Create webhook
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks create PROJECT_KEY REPO_SLUG \
  --name "CI Hook" --url "https://ci.example.com/bitbucket" \
  --event repo:push --event pr:opened --yes

# Update webhook
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks update PROJECT_KEY REPO_SLUG \
  --webhook-id 42 --name "Updated Hook" --set-inactive --yes

# Delete webhook
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket webhooks delete PROJECT_KEY REPO_SLUG \
  --webhook-id 42 --yes
```

---

### 9. Cloud Workspace Operations (1 command) - Cloud Only

#### `workspace`
Manage Cloud workspaces.

**Features**:
- List all workspaces
- Get workspace details
- Get workspace permissions
- Get repository permissions in workspace
- List projects in workspace
- Get specific project from workspace

**Example**:
```bash
# List workspaces
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace list

# Get workspace details
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace get --workspace-slug workspace1

# Get workspace permissions
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace permissions --workspace-slug workspace1

# List projects in workspace
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket workspace projects --workspace-slug workspace1
```

---

### 10. Repository Variables (1 command) - Cloud Only

#### `repo-variables`
Manage repository-level pipeline variables.

**Features**:
- List variables (`list` action)
- Get variable by UUID (`get` action)
- Create variable (`create` action, requires `--yes`)
- Update variable (`update` action, requires `--yes`)
- Delete variable (`delete` action, requires `--yes`)
- Support for secured variables

**Example**:
```bash
# List variables
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables list \
  --workspace team-slug --repo-slug repo-slug --no-markdown

# Create secured variable
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables create \
  --workspace team-slug --repo-slug repo-slug \
  --key API_TOKEN --value "super-secret" --secured true --yes --no-markdown

# Update variable
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-variables update \
  --workspace team-slug --repo-slug repo-slug \
  --uuid {variable-uuid} --value "rotate-me" --yes --no-markdown
```

---

### 11. Deployment Environments (1 command) - Cloud Only

#### `deployment-env`
Manage deployment environments and their variables.

**Features**:
- List environments (`list` action)
- Get environment (`get` action)
- Manage environment variables (`vars` sub-action):
  - List variables (`list`)
  - Create variable (`create`, requires `--yes`)
  - Update variable (`update`, requires `--yes`)
  - Delete variable (`delete`, requires `--yes`)

**Example**:
```bash
# List environments
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket deployment-env list \
  --workspace team-slug --repo-slug repo-slug

# Create environment variable
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket deployment-env vars create \
  --workspace team-slug --repo-slug repo-slug --env-uuid {env-uuid} \
  --key DB_HOST --value "db.example.com" --yes
```

---

### 12. Repository Issues (1 command) - Cloud Only

#### `issue`
Manage repository issues when Bitbucket Issues tracker is enabled.

**Features**:
- List issues (`list` action) with query/sort
- Get issue (`get` action)
- Create issue (`create` action)
- Update issue (`update` action: title, state, kind, priority, description)
- Delete issue (`delete` action, requires `--yes`)

**Example**:
```bash
# List issues
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue list \
  --workspace team-slug --repo-slug repo-slug \
  --query 'state = "open"' --sort -updated_on --no-markdown

# Create issue
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue create \
  --workspace team-slug --repo-slug repo-slug \
  --title "Production bug" --description "Steps to reproduce..." \
  --kind bug --priority critical --no-markdown

# Update issue
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket issue update \
  --workspace team-slug --repo-slug repo-slug --issue-id 123 \
  --state resolved --no-markdown
```

---

### 13. Pull Request Blockers (1 command) - Cloud Only

#### `pr-blocker`
Manage blocker comments on pull requests.

**Features**:
- List blockers (`list` action)
- Add blocker (`add` action) with optional reason/severity
- Delete blocker (`delete` action, requires `--yes`)

**Example**:
```bash
# List blockers
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker list \
  --workspace team-slug --repo-slug repo-slug --pull-request-id 123 --no-markdown

# Add blocker
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker add \
  --workspace team-slug --repo-slug repo-slug --pull-request-id 123 \
  --message "Pending security review" --reason "Security" --severity HIGH --no-markdown

# Delete blocker
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket pr-blocker delete \
  --workspace team-slug --repo-slug repo-slug --pull-request-id 123 \
  --blocker-uuid {blocker-uuid} --yes --no-markdown
```

---

### 14. Code Insights (1 command) - Cloud Only

#### `code-insights`
Manage Code Insights reports.

**Features**:
- Get report (`get` action)
- Create report (`create` action, requires `--yes`)
- Add annotations to report (`annotate` action, requires `--yes`)
- Delete report (`delete` action, requires `--yes`)

**Example**:
```bash
# Get report
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights get PROJECT_KEY REPO_SLUG COMMIT_ID \
  --report-key "test-report"

# Create report
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights create PROJECT_KEY REPO_SLUG COMMIT_ID \
  --report-key "coverage-report" --title "Coverage Report" \
  --reporter "coverage-tool" --result "PASSED" \
  --data-file coverage-data.json --report-type "COVERAGE" --yes

# Add annotations
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket code-insights annotate PROJECT_KEY REPO_SLUG COMMIT_ID \
  --report-key "test-report" --annotations-file annotations.json --yes
```

---

### 15. Repository Settings (1 command)

#### `repo-settings`
Manage repository settings.

**Features**:
- Branching model (`branching-model` sub-action):
  - Get model
  - Set model from JSON file
  - Enable/disable model
- Default branch (`default-branch` sub-action):
  - Get default branch
  - Set default branch
- Repository hooks (`hooks` sub-action):
  - List hooks
  - Enable/disable hooks
- Git LFS (`lfs` sub-action):
  - Get LFS status
  - Enable/disable LFS

**Example**:
```bash
# Get branching model
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings branching-model get PROJECT_KEY REPO_SLUG

# Set default branch
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings default-branch set PROJECT_KEY REPO_SLUG \
  --branch "main" --yes

# Enable hook
./scripts/worktree_uv.sh run --project vds_cli vds-cli bitbucket repo-settings hooks enable PROJECT_KEY REPO_SLUG \
  --hook-key "com.atlassian.bitbucket.server.bitbucket-bundle:force-push-hook" --yes
```

---

## Core Infrastructure Features

### Dual Mode Support
- **Bitbucket Server/Data Center**: Full support for on-premises deployments
- **Bitbucket Cloud**: Full support for cloud workspaces
- Automatic mode detection based on URL and configuration

### Authentication
- HTTP Basic Auth (username/password)
- Bearer Token authentication
- Automatic credential loading from the shared VDS env file (`VDS_ENV_FILE` or `<config-root>/.env`, with `~/.vds/.env` as the active Unix-like default)
- Secure credential handling (no exposure in logs)

### Error Handling
- Comprehensive error hierarchy:
  - `BitbucketClientError` (base)
  - `BitbucketAuthError` (401)
  - `BitbucketNotFoundError` (404)
  - `BitbucketConflictError` (409)
  - `BitbucketRateLimitedError` (429)
  - `BitbucketTransportError` (network)
  - `BitbucketRetryError` (retry exhaustion)
- Automatic retry with exponential backoff
- Context-aware error messages

### Output Formats
- **JSON Output**: Clean JSON via `--json-only` flag
- **Markdown Reports**: Automatic report generation (unless `--no-reports`)
- **Structured Logging**: Optional JSON logs via `--structured-logs`
- **Color Control**: `--no-color` / `--color` flags

### Agent-Friendly Features
- Non-interactive by default
- `--yes` flags required for destructive operations
- Consistent exit codes
- Machine-readable JSON output
- Comprehensive error messages

### Testing
- **289/289 tests passing** (scoped to `bitbucket_orchestrator/tests`)
- Comprehensive unit test coverage
- Integration test scenarios
- Error handling test coverage

---

## Summary Statistics

| Category | Commands | Status |
|----------|----------|--------|
| **Project Operations** | 2 | ✅ Complete |
| **Repository Operations** | 3 | ✅ Complete |
| **Pull Request Operations** | 12 | ✅ Complete (with enhancements) |
| **User/Group Management** | 3 | ✅ Complete |
| **Permission Management** | 3 | ✅ Complete |
| **Code Operations** | 2 | ✅ Complete |
| **Pipeline Operations** | 2 | ✅ Complete (Cloud only) |
| **Webhook Management** | 1 | ✅ Complete (Cloud only) |
| **Workspace Operations** | 1 | ✅ Complete (Cloud only) |
| **Repository Variables** | 1 | ✅ Complete (Cloud only) |
| **Deployment Environments** | 1 | ✅ Complete (Cloud only) |
| **Repository Issues** | 1 | ✅ Complete (Cloud only) |
| **PR Blockers** | 1 | ✅ Complete (Cloud only) |
| **Code Insights** | 1 | ✅ Complete (Cloud only) |
| **Repository Settings** | 1 | ✅ Complete |
| **Total CLI Commands** | **34** | ✅ **All Complete** |

---

## Best Practices

1. **Always use `--yes` for destructive operations** (merge, decline, delete)
2. **Use `--json-only` for automation** (clean JSON output, no reports)
3. **Use `--no-reports` for interactive use** (keeps console output, avoids filesystem writes)
4. **Check mergeability before merging** (`get-pr` shows conflicts/vetoes)
5. **Use best-effort features gracefully** (draft PRs, inline comments, unified diff may fallback)
6. **Leverage cross-project PRs** for complex workflows
7. **Use `--include-required-reviewers`** to respect branch policies automatically

---

## Documentation References

- **Main README**: `README.md` (this directory)
- **API Practices**: `BITBUCKET_API_PRACTICES.md`
- **Architecture Analysis**: `ARCHITECTURE_ANALYSIS.md`
- **PR Management Spec**: `../../../.kiro/specs/bitbucket-pr-management-cli/`

---

**Last Updated**: 2026-01-21
**Maintainer**: VDS Platform Team
