# VDS JIRA Orchestrator

Python toolkit for JIRA operations using the `atlassian-python-api` SDK. Provides a unified CLI interface for issue
tracking, project management, and JIRA automation.

## Quick Start

```bash
cd WHO-project/vds-scripts
# Optional: sync all orchestrators once
./scripts/bootstrap_uv.sh

# Package-specific sync & tests
uv sync --project jira_orchestrator --extra dev
uv run --project jira_orchestrator pytest
```

Run the CLI directly (uv automatically loads the project environment once it has been synced at least once):

```bash
# Using uv run (console script)
uv run --project jira_orchestrator vds-jira-cli --help

# Using the unified VDS CLI
./scripts/worktree_uv.sh run --project vds_cli vds-cli env load
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --limit 20
uv run --project jira_orchestrator vds-jira-cli search "project = NTTC" --limit 20 --json-only
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue NTTC-123
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira projects --limit 50
```

**Agent-friendly output**
- When using `vds-cli`, put Typer flags after `--` (e.g. `vds-cli jira -- --json-only projects`).
- `--json-only` emits clean JSON only (no reports/markdown, logs suppressed).
- `--no-reports` keeps normal console output but avoids writing report files.

## Available Commands

### Read Operations

- **`projects`** - List all JIRA projects

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira projects --limit 50
  # Optional filters:
  #   --search "keyword"   (matches name or key, case-insensitive)
  #   --limit 10           (applied after filtering)
  ```

- **`search`** - Search issues using JQL

  ```bash
  # Basic search
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC AND status = Open" --limit 50
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "assignee = currentUser()" --fields "summary,status,priority"

  # Advanced search with pagination
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --advanced --start 10 --limit 25
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search "project = NTTC" --start 0 --limit 50 --fields "summary,status"
  ```

  > **Cloud requirement**: Atlassian's May 2025 change requires `enhanced_jql` for all Cloud tenants. The CLI detects
  > `*.atlassian.net` base URLs and automatically routes searches through the enhanced endpoint (see announcement:
  > <https://support.atlassian.com/cloud-migration/docs/changes-to-search-api-july-2024/>).\
  > **Advanced search**: Use `--advanced` flag or `--start` parameter to enable pagination support. The `--start`
  > parameter automatically enables advanced search mode.

- **`search-by-filter`** - Search issues using a saved filter

  ```bash
  # Search using filter ID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search-by-filter 10000 --limit 50

  # Search with pagination
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira search-by-filter 10000 --start 20 --limit 25 --fields "summary,status,priority"
  ```

  > **Note**: Uses the JQL from the saved filter to perform the search. Supports pagination and field selection.

- **`issue`** - Get issue details

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue NTTC-123
  ```

- **`bulk-update`** - Bulk update multiple issues

  ```bash
  # Bulk update with JSON fields
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira bulk-update \
    --issue-keys "NTTC-1,NTTC-2,NTTC-3" \
    --fields '{"summary":"Updated summary"}' \
    --yes

  # Bulk update with fields file
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira bulk-update \
    --issue-keys "NTTC-1,NTTC-2" \
    --fields-file ./fields.json \
    --yes

  # Bulk update all fields (default)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira bulk-update \
    --issue-keys "NTTC-1,NTTC-2" \
    --yes
  ```

  > **Notes**:
  >
  > - Requires `--yes` flag for confirmation
  > - `--fields` accepts JSON string or `"*all"` (default) for all fields
  > - `--fields-file` accepts a JSON file containing field updates
  > - Multiple issue keys should be comma-separated

- **`field-append`** - Append value to issue field (for multi-select fields)

  ```bash
  # Append value with JSON string
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira field-append \
    --issue-key NTTC-123 \
    --field customfield_10000 \
    --value '{"name":"value"}' \
    --yes

  # Append value with file
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira field-append \
    --issue-key NTTC-123 \
    --field customfield_10000 \
    --value-file ./value.json \
    --yes

  # Append without notifying users
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira field-append \
    --issue-key NTTC-123 \
    --field customfield_10000 \
    --value '{"name":"value"}' \
    --no-notify \
    --yes
  ```

  > **Notes**:
  >
  > - Requires `--yes` flag for confirmation
  > - `--value` must be a JSON object (dict)
  > - `--value-file` accepts a JSON file containing the value object
  > - Use `--no-notify` to prevent user notifications
  > - Primarily used for multi-select custom fields

- **`issue-archive`** - Archive an issue

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-archive --issue-key NTTC-123 --yes
  ```

  > **Warning**: Archiving an issue removes it from normal views. Use `issue-restore` to restore archived issues.

- **`issue-restore`** - Restore an archived issue

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-restore --issue-key NTTC-123 --yes
  ```

  > **Notes**:
  >
  > - Requires `--yes` flag for confirmation
  > - Restores previously archived issues back to normal state

- **`property`** - Manage JIRA application properties

  ```bash
  # Get property by key
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira property get --key "jira.lf.date.dmy"

  # Get property with filters
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira property get \
    --key "jira.lf.*" \
    --permission-level SYSTEM \
    --key-filter "jira.lf.*"

  # Set property
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira property set \
    --property-id "jira.lf.date.dmy" \
    --value "true" \
    --yes
  ```

  > **Notes**:
  >
  > - `get` action supports optional `--key`, `--permission-level`, and `--key-filter` parameters
  > - `set` action requires `--property-id`, `--value`, and `--yes` flag

- **`settings`** - Manage JIRA settings

  ```bash
  # Get advanced settings
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira settings advanced
  ```

  > Returns advanced JIRA configuration settings.

- **`createmeta`** - Get create metadata for issue creation

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira createmeta --project NTTC --issuetype Task
  ```

- **`custom-fields`** - List custom fields

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira custom-fields --search "Story Points" --limit 10
  ```

- **`board`** - Agile board operations

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board list --project NTTC --limit 10
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board get --board-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board create --name "Sprint Board" --type scrum --filter-id 100 --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board issues --board-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board properties --board-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira board velocity --board-id 1
  ```

- **`epic`** - Epic operations

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira epic issues --epic-key NTTC-100
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira epic list --board-id 1 --limit 20
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira epic issues-for-epic --board-id 1 --epic-id 100
  ```

- **`sprint`** - Sprint operations

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint list --board-id 1 --limit 10
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint issues --board-id 1 --state active
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint versions --board-id 1
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint create --name "Sprint 1" --board-id 1 --start-date "2025-01-01" --end-date "2025-01-14" --goal "Complete features" --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint rename --sprint-id 100 --name "Updated Sprint" --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira sprint add-issues --sprint-id 100 --issues "NTTC-123,NTTC-124" --yes
  ```

- **`reindex`** - Reindex operations

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira reindex status
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira reindex start --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira reindex with-type BACKGROUND --yes
  ```

- **`worklog`** - Worklog operations (time tracking)

  ```bash
  # Get worklogs for an issue
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira worklog get --issue-key NTTC-123

  # Add worklog entry
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira worklog add \
    --issue-key NTTC-123 \
    --time-spent "2h 30m" \
    --comment "Implemented feature X" \
    --started "2025-11-12T10:00:00Z" \
    --yes

  # Add worklog with time in seconds
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira worklog add \
    --issue-key NTTC-123 \
    --time-sec 7200 \
    --comment "Code review" \
    --yes

  # Get updated worklogs since timestamp
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira worklog updated --since "2025-11-12 10:00:00"

  # Get deleted worklogs since timestamp
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira worklog deleted --since "2025-11-12 10:00:00"
  ```

- **`transitions`** - Get available transitions for an issue

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira transitions NTTC-123
  ```

- **`changelog`** - Get issue change history

  ```bash
  # Get complete changelog
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira changelog get NTTC-123

  # Get changelog with pagination
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira changelog get NTTC-123 --start 0 --limit 50

  # Get status change history only
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira changelog status NTTC-123
  ```

- **`dashboard`** - Dashboard operations

  ```bash
  # Get dashboard by ID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira dashboard get --dashboard-id 10000

  # List dashboards
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira dashboard list

  # List dashboards with filter and pagination
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira dashboard list --filter "project" --start 0 --limit 50
  ```

- **`filter`** - Filter management operations

  ```bash
  # List all filters
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter list

  # List filters by owner
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter list --owner username

  # Get filter by ID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter get --filter-id 10000

  # Create a new filter
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter create \
    --name "My Filter" \
    --jql "project = NTTC AND status = Open" \
    --description "Open issues in NTTC project" \
    --favourite \
    --yes

  # Update filter (name, JQL, description, or favourite status)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter update \
    --filter-id 10000 \
    --name "Updated Filter Name" \
    --yes

  # Delete filter
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira filter delete --filter-id 10000 --yes
  ```

  > **Notes**:
  >
  > - Write operations (create, update, delete) require `--yes` flag for confirmation
  > - `update` requires at least one of: `--name`, `--jql`, `--description`, or `--favourite`
  > - If `--jql` is not provided in `update`, the existing JQL is preserved

- **`link-type`** - Issue link type operations

  ```bash
  # List all issue link types
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type list

  # Get specific link type by ID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type get --link-type-id 10000

  # Create new link type
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type create \
    --name "Tests" \
    --inward "is tested by" \
    --outward "tests" \
    --yes

  # Create link type from JSON file
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type create \
    --data-file link_type.json \
    --yes

  # Update link type
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type update \
    --link-type-id 10000 \
    --name "Tests Updated" \
    --inward "is tested by" \
    --outward "tests" \
    --yes

  # Delete link type
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira link-type delete --link-type-id 10000 --yes
  ```

- **`remote-link`** - Issue remote link operations

  ```bash
  # List remote links for an issue
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira remote-link list --issue-key NTTC-123

  # Create a remote link (with confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira remote-link create \
    --issue-key NTTC-123 \
    --url https://status.example.com/NTTC-123 \
    --title "Status Page" \
    --relationship "is documented by" \
    --yes

  # Update an existing remote link
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira remote-link update \
    --issue-key NTTC-123 \
    --remote-link-id 10 \
    --url https://status.example.com/NTTC-123?updated=true \
    --yes

  # Delete a remote link
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira remote-link delete --issue-key NTTC-123 --remote-link-id 10 --yes
  ```

- **`issue-property`** - Issue property operations

  ```bash
  # List property keys for an issue
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-property list --issue-key NTTC-123

  # Get a specific property
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-property get --issue-key NTTC-123 --property-key deploy.info

  # Set a property using inline JSON (requires confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-property set \
    --issue-key NTTC-123 \
    --property-key deploy.info \
    --value '{"env": "prod", "version": "1.2.3"}' \
    --yes

  # Set a property from JSON file
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-property set \
    --issue-key NTTC-123 \
    --property-key deploy.info \
    --data-file deploy_info.json \
    --yes

  # Delete a property
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-property delete --issue-key NTTC-123 --property-key deploy.info --yes
  ```

- **`watcher`** - Issue watcher operations

  ```bash
  # List watchers
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira watcher list --issue-key NTTC-123

  # Add watcher (username/accountId) with confirmation
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira watcher add --issue-key NTTC-123 --account user@example.com --yes

  # Remove watcher
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira watcher remove --issue-key NTTC-123 --account user@example.com --yes
  ```

- **`component`** - Project component operations

  ```bash
  # Get a component
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira component get --component-id 10000

  # Create a component (requires confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira component create \
    --project-key NTTC \
    --name "Payments" \
    --description "Handles payment flows" \
    --yes

  # Update a component
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira component update \
    --component-id 10000 \
    --name "Payments Core" \
    --yes

  # Delete a component
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira component delete --component-id 10000 --yes
  ```

- **`user`** - User management operations

  ```bash
  # Search for users (Cloud: email/displayName, DC: username)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira user search --query "test@example.com"
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira user search --query "John Doe" --start 0 --limit 20
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira user search --query "test" --include-inactive

  # Get user groups (Cloud only - requires account ID)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira user groups --account-id "5d5f5e5d5e5d5e5d5e5d5e5d"

  # Deactivate a user (Jira 8.3.0+, requires confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira user deactivate --username "testuser" --yes
  ```

  > **Cloud/DC Differences**:
  >
  > - `user search`: In Cloud, searches by email/displayName/accountId. In DC, searches by username.
  > - `user groups`: **Cloud only** - requires account ID (not username). Returns error on Server/DC.
  > - `user deactivate`: Requires Jira 8.3.0+ and `--yes` flag for confirmation.

- **`version`** - Project version management operations

  ```bash
  # List project versions with pagination and filtering
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version list --project-key NTTC
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version list --project-key NTTC --start 0 --limit 20
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version list --project-key NTTC --order-by name --query "1.0" --status released

  # Create a new version (requires confirmation)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version create \
    --project-key NTTC \
    --project-id 10000 \
    --name "1.0.0" \
    --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version create \
    --project-key NTTC \
    --project-id 10000 \
    --name "1.0.0" \
    --archived \
    --released \
    --yes

  # Update a version (requires confirmation and at least one field)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version update \
    --version-id 10000 \
    --name "1.0.1" \
    --yes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira version update \
    --version-id 10000 \
    --description "Updated description" \
    --archived \
    --start-date "2025-01-01" \
    --release-date "2025-01-31" \
    --yes
  ```

  > **Notes**:
  >
  > - `version list`: Supports pagination (`--start`, `--limit`), sorting (`--order-by`: `sequence`, `name`,
  >   `startDate`, `releaseDate`), and filtering (`--query`, `--status`).
  > - `version create`: Requires `--project-key`, `--project-id`, `--name`, and `--yes` flag. Use `--archived` and
  >   `--released` flags to set version state.
  > - `version update`: Requires `--version-id`, `--yes` flag, and at least one update field (`--name`, `--description`,
  >   `--archived`, `--released`, `--start-date`, `--release-date`).

- **`security-scheme`** - Issue security scheme operations

  ```bash
  # List all security schemes
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira security-scheme list

  # Get specific security scheme by ID
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira security-scheme get --scheme-id 10000

  # Get security scheme with only levels
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira security-scheme get --scheme-id 10000 --only-levels
  ```

- **`permissions`** - Permission operations

  ```bash
  # Get all permission types
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permissions all

  # Check permissions (global)
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permissions check --permissions "ADMINISTER_PROJECTS,BROWSE_PROJECTS"

  # Check permissions in project context
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permissions check \
    --permissions "ADMINISTER_PROJECTS" \
    --project-key NTTC

  # Check permissions in issue context
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permissions check \
    --permissions "EDIT_ISSUES" \
    --issue-key NTTC-123
  ```

- **`permission-scheme`** - Get project permission scheme

  ```bash
  # Get project permission scheme
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permission-scheme NTTC

  # Get with expanded fields
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira permission-scheme NTTC --expand "permissions,user,group"
  ```

- **`issue-security-scheme`** - Get project issue security scheme

  ```bash
  # Get project issue security scheme
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-security-scheme NTTC

  # Get with only levels
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira issue-security-scheme NTTC --only-levels
  ```

### Write Operations

- **`create`** - Create a new issue

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira create \
    --project NTTC \
    --issuetype Task \
    --summary "Implement feature X" \
    --description "Detailed description here" \
    --assignee username \
    --labels "backend,high-priority" \
    --set customfield_12345=10001 \
    --yes
  ```

- **`update`** - Update issue fields

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira update NTTC-123 \
    --set summary="Updated summary" \
    --add-label "urgent" \
    --remove-label "low-priority" \
    --yes
  ```

- **`comment`** - Add comment to issue

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira comment NTTC-123 \
    --message "This is a comment" \
    --yes
  ```

- **`transition`** - Transition issue status

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira transition NTTC-123 \
    --to "In Progress" \
    --admin \
    --yes
  ```

- **`delete`** - Delete an issue (requires --yes and --force)

  ```bash
  ./scripts/worktree_uv.sh run --project vds_cli vds-cli jira delete NTTC-123 --yes --force
  ```

## Working with Custom Fields

### Discovering Fields

When creating issues, you may need to provide mandatory custom fields. Use `discover-fields` to find the correct IDs and allowed values for your project and issue type. By default, it returns custom fields only; use `--include-system` to include system fields.

```bash
# List custom fields for a project/issuetype (default)
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira discover-fields --project NTTC --issuetype Task

# Include system fields
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira discover-fields --project NTTC --issuetype Task --include-system

# Filter for a specific field name or ID
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira discover-fields --project NTTC --issuetype Task --field "Vai trò"

# Fallback to editmeta using an existing issue key
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira discover-fields --project NTTC --issuetype Task --issue-key NTTC-123
```

**Output Example:**
```json
{
  "project": "NTTC",
  "issueType": "Task",
  "count": 1,
  "duration_ms": 1035,
  "fields": [
    {
      "id": "customfield_15200",
      "name": "Vai trò - Công đoạn",
      "required": true,
      "type": "option-with-child",
      "is_custom": true,
      "allowedValues": [
        {"id": "14901", "value": "SA"},
        {"id": "14902", "value": "BA"}
      ]
    }
  ]
}
```

`duration_ms` captures how long field discovery took and is used for performance warnings.

### Providing Complex Values

Some custom fields (like dropdowns, cascading selects) require a JSON object structure rather than a simple string. The `--set` parameter supports JSON values.

**Syntax:** `--set 'field_id={"key": "value"}'`

**Note:** By default, `--set` only parses JSON objects/arrays. Use `--set-json` if you need scalar JSON values (e.g., `true`, `1`, `null`).

**Examples:**

1.  **Select List (Single Choice):**
    ```bash
    --set 'customfield_15200={"value": "SA"}'
    ```

2.  **Select List (Multiple Choice):**
    ```bash
    --set 'customfield_12345=[{"value": "Option A"}, {"value": "Option B"}]'
    ```

3.  **Cascading Select:**
    ```bash
    --set 'customfield_98765={"value": "Parent Option", "child": {"value": "Child Option"}}'
    ```

### Validation (Dry Run)

Use the `--dry-run` flag to validate your payload and check for missing required fields without creating a ticket.

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli jira create \
  --project NTTC \
  --issuetype Task \
  --summary "Test Ticket" \
  --dry-run
```

**Output:**
```text
[DRY RUN] Validating payload for NTTC / Task...
[DRY RUN] ⚠️  Warning: The following REQUIRED fields appear missing:
  - Vai trò - Công đoạn (customfield_15200)
Tip: Use --set to provide them.
```

The JSON response also includes `field_name_map` to help map field IDs to display names.

## Configuration

The orchestrator uses environment variables from the shared VDS env file:

```bash
# Required for authentication
VDS_USERNAME=your-username
VDS_PASSWORD=your-password

# Optional: Use token instead of username/password
JIRA_TOKEN=your-api-token

# JIRA base URL (defaults to https://jira.digital.vn)
JIRA_BASE_URL=https://jira.digital.vn
```

## Project Layout

- `src/vds_jira_orchestrator/config.py` – Environment configuration and settings
- `src/vds_jira_orchestrator/adapter.py` – JIRA adapter using atlassian-python-api SDK
- `src/vds_jira_orchestrator/cli.py` – Typer CLI interface
- `src/vds_jira_orchestrator/errors.py` – Custom error types
- `src/vds_jira_orchestrator/reporting.py` – JSON/Markdown run reports
- `tests/` – pytest test suite

## Feature Coverage

The orchestrator implements **120+ methods** covering core JIRA operations. For a complete feature coverage reference
and SDK comparison, see [`ATLASSIAN_FEATURES_REFERENCE.md`](../ATLASSIAN_FEATURES_REFERENCE.md).

**Current Coverage**: ~90% of atlassian-python-api SDK features

**Recently Added**:

- ✅ Application Properties (property get/set, settings advanced) - **NEW**
- ✅ Issue Archiving (issue-archive, issue-restore) - **NEW**
- ✅ Bulk Operations (bulk-update, field-append) - **NEW**
- ✅ Version Management (list, create, update) - **NEW**
- ✅ User Management (search, groups, deactivate) - **NEW**
- ✅ Issue Link Types management (list, get, create, update, delete) - **NEW**
- ✅ Issue Security Schemes (list, get) - **NEW**
- ✅ Advanced Permission Operations (permissions all/check, permission-scheme, issue-security-scheme) - **NEW**
- ✅ Agile/Scrum operations (boards, epics) - **NEW**
- ✅ Board properties and velocity management - **NEW**
- ✅ Sprint management - **NEW**
- ✅ Backlog operations - **NEW**
- ✅ Worklog management (time tracking) - **NEW**
- ✅ Issue transitions & changelog - **NEW**
- ✅ Advanced search operations (search with pagination, search-by-filter) - **NEW**
- ✅ Filter management (list, get, create, update, delete) - **NEW**
- ✅ Dashboard operations - **NEW**
- ✅ Reindexing operations - **NEW**

**Missing High-Priority Features**:

- None (all high-priority features complete)

## Advanced Features

The `JiraAdapter` class provides many additional methods beyond the CLI:

- **Attachments**: `add_attachment()`, `get_attachments()`, `download_attachments()`
- **Project Operations**: `get_project()`, `get_project_components()`, `get_project_versions()`
- **Version Management**: `get_project_versions_paginated()`, `add_version()`, `update_version()`
  - CLI: `jira version list`, `jira version create`, `jira version update`
- **User Management**: `get_user()`, `find_users()`, `get_myself()`, `get_user_groups()` (Cloud only),
  `deactivate_user()` (Jira 8.3.0+)
  - CLI: `jira user search`, `jira user groups`, `jira user deactivate`
- **Application Properties**: `get_property()`, `set_property()`, `get_advanced_settings()`
  - CLI: `jira property get`, `jira property set`, `jira settings advanced`
- **Issue Archiving**: `issue_archive()`, `issue_restore()`
- **Bulk Operations**: `bulk_update_issue_field()`, `issue_field_value_append()`, `match_jql()`
  - CLI: `jira bulk-update`, `jira field-append`
- **Custom Fields**: `get_custom_fields()`, `get_issue_field_value()`
- **Group Management**: `create_group()`, `remove_group()`, `add_user_to_group()`
- **Agile Boards**: `get_all_agile_boards()`, `create_agile_board()`, `get_agile_board()`, `get_issues_for_board()`
- **Board Properties**: `get_agile_board_properties()`, `set_agile_board_property()`,
  `get_agile_board_refined_velocity()`
- **Epics**: `epic_issues()`, `get_epics()`, `get_issues_for_epic()`
- **Sprints**: `get_all_sprints_from_board()`, `create_sprint()`, `rename_sprint()`, `add_issues_to_sprint()`
- **Reindexing**: `reindex()`, `reindex_status()`, `reindex_with_type()`

These can be accessed programmatically by importing the adapter:

```python
from vds_jira_orchestrator.adapter import JiraAdapter
from vds_jira_orchestrator.config import JiraSettings

settings = JiraSettings()
adapter = JiraAdapter(
    url=str(settings.base_url),
    username=settings.username,
    password=settings.password
)
issues = adapter.jql("project = NTTC", limit=100)
```

## Run Reports

Run reports are written to `WHO-project/vds-scripts/reports/jira_runs/YYYY/MM/DD/<timestamp>.json` (plus Markdown unless
`--no-markdown` is used).

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
uv run --extra dev pytest --cov=src/vds_jira_orchestrator
```

## Error Handling

The orchestrator provides structured error types:

- `JiraAuthError` - Authentication failures
- `JiraNotFound` - Resource not found (404)
- `JiraRateLimited` - Rate limit exceeded (429)
- `JiraConflictError` - Conflict errors (409)
- `JiraResponseError` - Server errors (500)
- `JiraTransportError` - Network/connection errors
- `JiraAdapterError` - General adapter errors

All errors include context information for debugging.
 errors include context information for debugging.
