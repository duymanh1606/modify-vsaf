<!-- diátaxis: how-to -->

# Install And Bootstrap WHO Scripts And Skills

Use this guide when you need a clean, explicit setup path for the WHO scripts workspace and the WHO skills catalog.
It is written for both human contributors and AI agents.

## 1. Choose the right working mode

- **Dedicated `vds-scripts` worktree**: prefer `./scripts/worktree_uv.sh ...` for all `uv` commands.
- **Main `vds-scripts` checkout**: `uv sync` and `uv run --project ...` are acceptable.
- **External clone**: set explicit `VDS_SCRIPTS_PATH` / `VDS_SKILLS_PATH` values and do not assume monorepo-relative defaults.

## 2. Install prerequisites

### Required for scripts workspace

- `git`
- `uv`
- a supported shell environment

Install `uv`:

- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- or use the package-manager workflow approved in your environment

### Optional but recommended for skill workflows

- `python3` (or `python`) for running `vds-skills-sync`

This is required when you want `vds-skills-sync` to generate `AGENTS.md` from
`registry.yaml`. It is not required when you only need to read canonical skill
files directly.

## 3. Set canonical paths

Add these to `VDS_ENV_FILE` or `<config-root>/.env` for persistence when appropriate.
`<config-root>` resolves from `VDS_CONFIG_DIR` when set, otherwise from the user-home VDS default.

```bash
export VDS_SCRIPTS_PATH="${VDS_SCRIPTS_PATH:-./WHO-project/vds-scripts}"
export VDS_SKILLS_PATH="${VDS_SKILLS_PATH:-./WHO-project/vds-skills/skills}"
```

## 4. Bootstrap the scripts workspace

### Dedicated `vds-scripts` worktree

```bash
cd "$VDS_SCRIPTS_PATH"
./scripts/worktree_uv.sh sync --all-packages
```

### Non-worktree checkout

```bash
cd "$VDS_SCRIPTS_PATH"
uv sync --all-packages
```

## 5. Verify the scripts workspace

Run the minimum verification set before deeper work:

```bash
cd "$VDS_SCRIPTS_PATH"
./scripts/worktree_uv.sh run --project vds_cli vds-cli --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
./scripts/worktree_uv.sh run --project vds_cli vds-cli audit --help
./scripts/worktree_uv.sh run --project vds_cli vds-cli spec --help
```

If you are not in a dedicated worktree, use `uv run --project ...` equivalents.

If `vds-cli env status` reports missing credentials, configure `~/.vds/.env` per §11 below before continuing. The same section covers the canonical git credential helper (`vds-cli env install-git-helper`).

## 6. Verify the skills catalog

```bash
ls -la "$VDS_SKILLS_PATH/"
```

Canonical maintained skills live under:

- `WHO-project/vds-skills/skills/`

Do not treat `.agent/skills/` as an independent authoring source.

## 7. Human workflow: OpenSkills usage

When `node`/`npx` is available and OpenSkills is configured for the workspace:

```bash
ls WHO-project/vds-skills/skills/
cat WHO-project/vds-skills/skills/vds-scripts-skill
cat WHO-project/vds-skills/skills/audit-orchestrator-skill
```

Use OpenSkills when you want the standard install/read/sync workflow.

## 8. AI-agent workflow: direct fallback when OpenSkills is unavailable

If `cat WHO-project/vds-skills/skills/<skill-name>` fails because the current shell context does not resolve the workspace skill configuration correctly, fall back to the canonical skill files directly.

Read from:

- `WHO-project/vds-skills/skills/<skill-name>/SKILL.md`

Examples:

- `WHO-project/vds-skills/skills/vds-scripts-skill/SKILL.md`
- `WHO-project/vds-skills/skills/audit-orchestrator-skill/SKILL.md`
- `WHO-project/vds-skills/skills/spec-creation-skill/SKILL.md`

This fallback is valid because the canonical source of truth is the WHO skills repository, not the mirror/symlink surfaces.

## 9. Minimum agent-readiness checklist

Before an AI agent proceeds, confirm:

- `VDS_SCRIPTS_PATH` points to the intended scripts workspace
- `VDS_SKILLS_PATH` points to the canonical skills directory
- routed help works: `vds-cli --help`
- specialist help works: `vds-audit --help`, `vds-cli spec --help`
- evolution loop works: `.venv/bin/vds-cli evolution status` (or `vds-cli evolution status`)
- the agent knows whether it is using OpenSkills loading or direct canonical skill-file reads
- `.agent/skills/` is treated as compatibility-only, not as the maintained source

## 10. OpenSpace evolution loop runtime (when using `vds_evolution`)

If you intend to use the WHO ecosystem evolution loop with a real OpenSpace runtime,
prefer repo-local runtime paths under the scripts workspace and keep durable env
configuration in the shared VDS env layer.

Recommended durable env placement:
- `VDS_ENV_FILE`
- or the default shared env file: `~/.vds/.env`

Recommended variables:

```bash
OPENSPACE_WORKSPACE="$VDS_SCRIPTS_PATH/.openspace"
OPENSPACE_HOST_SKILL_DIRS="$VDS_SCRIPTS_PATH/.openspace/shadow/skills"
OPENSPACE_TRANSPORT=stdio
OPENSPACE_AUTONOMOUS_ENABLED=false
```

Notes:
- Keep autonomy disabled until the OpenSpace runtime is verified healthy.
- Prefer repo-local `.openspace/` over ad hoc host-only directories so the setup is part of the workspace.
- Refresh the shadow skill mirror from the canonical skills catalog before enabling automated evolution.
- Ensure `openspace-mcp` is installed and callable in the active shell before relying on stdio transport.
- Treat the official HKUDS/OpenSpace repository as the reference for runtime startup and env semantics; prefer the officially documented `stdio` and `sse` transports for real setup.

### vds-cli evolution script execution

The `vds-cli evolution` script works from any CWD due to a spec_from_file_location workaround that bypasses the openspace `__path_hook__` issue in mixed venv environments.

**Available entry points:**

| Entry | Location | Usage |
|-------|----------|-------|
| Standalone | `.venv/bin/vds-cli evolution` | Direct execution from scripts repo |
| Tracked shell | `vds-cli evolution-mono.sh` | For monorepo compatibility |
| Via router | `vds-cli evolution ...` | Through the unified CLI |

**Typical commands:**

```bash
# Standalone (works from any CWD)
.venv/bin/vds-cli evolution status
.venv/bin/vds-cli evolution list

# Via router
vds-cli evolution status
vds-cli evolution list

# OpenSpace bootstrap
vds-cli evolution openspace-bootstrap
vds-cli evolution openspace-doctor
```

**Root cause note:** When the monorepo `.venv` contains both `openspace` and `vds-cli evolution` packages installed via `uv pip install -e`, the openspace editable installer registers a custom `PathEntryFinder` in `sys.path_hooks`. This causes `importlib.util.find_spec()` to return `None` for `vds-cli evolution` from certain CWDs. The script workaround uses `spec_from_file_location` + `module_from_spec` to bypass the hook entirely and directly load from known file paths.

## 11. Configure credentials in `~/.vds/.env`

This section defines the canonical shape of `~/.vds/.env` per `who-ecosystem-alignment` Phase 5 FR-18..FR-25. The file is the single source of credentials for all VDS orchestrators. Values shown below are placeholders — replace them with your real credentials. NEVER commit real credential values anywhere (NFR-12).

### 11.1 Required keys (Atlassian shared identity)

The three Atlassian orchestrators (`bitbucket_orchestrator`, `confluence_orchestrator`, `jira_orchestrator`) share the corporate SSO identity per FR-18 (Atlassian shared-identity model). Both keys are mandatory:

```dotenv
VDS_USERNAME=<your-corporate-username>
VDS_PASSWORD=<your-corporate-password>
```

Removing either key simultaneously breaks Bitbucket SDK, Confluence SDK, and JIRA SDK access — see the Credential Consumer Inventory in `.gpt-5.4/specs/who-ecosystem-alignment/design.md` Phase 5 §Credential Consumer Inventory.

### 11.2 Optional per-product tokens (token-preference asymmetry)

Per FR-19, each Atlassian product accepts an additional per-product token. The resolution order is **asymmetric by product**:

| Orchestrator | Token env var | Resolution priority |
|---|---|---|
| `bitbucket_orchestrator` | `BITBUCKET_TOKEN` | **Token preferred** over basic auth when both present |
| `jira_orchestrator` | `JIRA_TOKEN` | **Token preferred** over basic auth when both present |
| `confluence_orchestrator` | `INTERNAL_CONFLUENCE_TOKEN`, `EXTERNAL_CONFLUENCE_TOKEN` | **Basic auth primary** per `.claude/rules/sdk-and-auth-rules.md`; tokens are fallback |

Configure tokens only if you've been issued one:

```dotenv
BITBUCKET_TOKEN=<your-bbdc-pat>
JIRA_TOKEN=<your-jira-pat>
INTERNAL_CONFLUENCE_TOKEN=<your-internal-confluence-token>
EXTERNAL_CONFLUENCE_TOKEN=<your-external-confluence-token>
```

A token set to an empty string or whitespace is treated as absent per AC-19.5 — the SDK and the git credential helper both fall back to basic auth.

### 11.3 Isolated-prefix orchestrators (non-Atlassian)

Per FR-18 AC-18.2, non-Atlassian orchestrators use isolated credential prefixes and MUST NOT bind `VDS_PASSWORD`:

```dotenv
# Grafana
VDS_GRAFANA_USER=<your-grafana-user>
VDS_GRAFANA_PASSWORD=<your-grafana-password>
VDS_GRAFANA_TOKEN=<your-grafana-pat>          # optional; preferred when set

# SonarQube
VDS_SONAR_USER=<your-sonar-user>
VDS_SONAR_PASSWORD=<your-sonar-password>
VDS_SONAR_TOKEN=<your-sonar-pat>              # optional; preferred when set

# Elasticsearch (basic only — no token alternative in current SDK)
VDS_ELASTIC_USER=<your-elastic-user>
VDS_ELASTIC_PASSWORD=<your-elastic-password>
```

These prefixes can be rotated independently of the Atlassian shared identity.

### 11.4 Endpoint URLs

Per-orchestrator endpoint URLs are environment-specific:

```dotenv
VDS_BITBUCKET_URL=<your-bitbucket-base-url>
VDS_CONFLUENCE_URL=<your-confluence-base-url>
VDS_GRAFANA_URL=<your-grafana-url>
# ... add one per orchestrator you intend to use
```

### 11.5 Install the git credential helper (`vds-cli env install-git-helper`)

Per FR-23 (helper lifecycle via vds-cli) + FR-24 (single canonical artifact), the operator git credential helper is installed and managed exclusively via `vds-cli env`. NEVER install or upgrade the helper by manual `cp` / `chmod` / `git config` (FR-23 AC-23.1).

```bash
# Install the canonical helper at $HOME/.vds/bin/git-credential-vds (mode 0o700)
# and configure git credential.helper to use it. Removes any pre-FR-24 artifacts
# (signature-checked per AC-24.6 — user-authored files are preserved with a warning).
./scripts/worktree_uv.sh run --project vds_cli vds-cli env install-git-helper

# Verify install state (exit 0 ⇔ all checks pass)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env verify-git-helper

# If a Bitbucket account-lock cooldown is active, reset after fixing creds:
./scripts/worktree_uv.sh run --project vds_cli vds-cli env verify-git-helper --reset-cooldown

# Uninstall (idempotent — safe to call when nothing is installed)
./scripts/worktree_uv.sh run --project vds_cli vds-cli env remove-git-helper

# Uninstall + delete cooldown state file
./scripts/worktree_uv.sh run --project vds_cli vds-cli env remove-git-helper --purge
```

The helper enforces three contracts:

- **Host allowlist** (FR-20 AC-20.1): credentials emitted ONLY for `bitbucket.digital.vn`. Extensible via `VDS_BITBUCKET_HOSTS` in `~/.vds/.env` (comma-separated). Never readable from shell env per AC-20.6 — extension requires `~/.vds/.env` edit. Other git hosts get silent fall-through to the next configured helper (e.g., osxkeychain).
- **Lockout prevention** (FR-21): 3 failed-auth events within 60 seconds trigger a 300-second silent cooldown. State file at `$HOME/.vds/.git-credential-helper-cooldown.json` (mode `0o600` per AC-21.7). Reset via `verify-git-helper --reset-cooldown`.
- **Token preference** (mirrors FR-19 for Bitbucket per AC-20.3): emits `BITBUCKET_TOKEN` over `VDS_PASSWORD` when both are configured.

### 11.6 Verification

Confirm the full credential + helper stack:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli env status
./scripts/worktree_uv.sh run --project vds_cli vds-cli env verify-git-helper
./scripts/worktree_uv.sh run --project vds_cli vds-cli doctor
```

`vds-cli doctor` includes a "Git credential helper" status row (`installed` / `missing` / `broken`) per FR-23 AC-23.5, with a remediation hint pointing to `vds-cli env install-git-helper`.

### 11.7 Canonical credential model

The full credential resolution invariants — which orchestrators share `VDS_PASSWORD`, why the per-product token preference is asymmetric (Bitbucket/JIRA prefer token; Confluence keeps basic primary), what the helper lifecycle contract is, what file modes are required — live in:

**Canonical credential model: `who-ecosystem-alignment` Phase 5 FR-18..FR-25** at `.gpt-5.4/specs/who-ecosystem-alignment/`.

Refer to that spec when:

- Adding a new orchestrator → declare its credential model (Atlassian-shared vs isolated-prefix) per AC-18.3 and update `design.md` Phase 5 §Credential Consumer Inventory.
- Proposing changes to `~/.vds/.env` shape → audit which orchestrators read each key.
- Modifying the git credential helper → AC-25.4 requires paired updates if `BitbucketSettings.get_auth_kwargs` or `vds_cli_common.env._parse_env_file` change.

## 12. Related references

- `../reference/portable-paths-and-config.md`
- `../reference/cli-help-matrix.md`
- `../tutorials/who-skills-and-scripts-onboarding.md`
- `choose-the-right-command-or-skill.md`
- `.gpt-5.4/specs/who-ecosystem-evolution-loop/`
- `.gpt-5.4/specs/who-ecosystem-alignment/` (canonical credential model — Phase 5 FR-18..FR-25)
