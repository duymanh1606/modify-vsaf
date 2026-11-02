# VDS Scripts

This directory contains operational and workspace scripts for the VDS monorepo.

---

## Worktree Wrapper Scripts (Phase 220.V, ADR-93)

Two idempotent wrappers replace bare `git worktree add`/`git worktree remove`
for vds-scripts:

| Script | Purpose | Replaces |
|---|---|---|
| `worktree-add.sh` | Create worktree → auto-lock iCloud paths → `uv sync --all-packages --all-extras` → stamp `.uv-sync-stamp` | `git worktree add` + manual `uv sync` (Phase 206/219 found `--all-extras` is mandatory) |
| `worktree-remove.sh` | Unlock → inventory husks → `git worktree remove` → `rm -rf .claude/.gitnexus/graphify-out/__pycache__` → prune metadata → verify | `git worktree remove` + manual husk cleanup |

### Usage

```bash
# Add (idempotent — safe to re-run)
./scripts/worktree-add.sh ../worktrees/vds-scripts-vai-phaseN-purpose vai-phaseN/purpose

# Remove (idempotent — safe to re-run)
./scripts/worktree-remove.sh ../worktrees/vds-scripts-vai-phaseN-purpose
```

Branch-prefix convention: `<spec-prefix>-phase<N>` (per `CLAUDE.md` §Phase Numbering & Branch Naming). The wrappers do not enforce naming.

### Output contract

All steps emit single-line JSON to stdout via the `emit_json` helper (`python3 json.dumps` for safe escaping). Steps that succeeded report `"result": "ok"`; idempotent skips report `"[idempotent] ..."`; failures report `"result": "fail"` with a `"reason"` field and exit non-zero (codes 2/3/4 documented in script headers).

### When to use bare `git worktree`

Only for vds-skills paths (no wrapper currently) or for vds-scripts checkouts predating Phase 220.V. After bare `git worktree add`, MUST run `uv sync --all-packages --all-extras` manually. Bare `git worktree remove` leaves `.claude/`, `.gitnexus/`, `graphify-out/` orphans — clean with `rm -rf "$WT"/{.claude,.gitnexus,graphify-out}`.

See `vds-skills/skills/git-worktree-skill/SKILL.md` for full reference.

---

## UV Contract — Canonical Usage

All maintained scripts that invoke Python tools should route through the
worktree-safe UV wrapper or the shared shell helpers rather than calling `uv`
directly. This prevents virtualenv inheritance bugs when scripts are called
from shell sessions that already have an active `VIRTUAL_ENV` from a different
worktree or checkout.

### Wrapper stack

```/dev/null/scripts-stack.txt#L1-3
scripts/bootstrap_uv.sh      # one-time / CI setup: sync workspace packages or full workspace
scripts/worktree_uv.sh       # low-level exec wrapper: clears VIRTUAL_ENV then execs uv
scripts/vds_sh_helpers.sh    # runtime helpers: bind --directory and resolve package names
```

### When to use each helper function

| Function | Use when |
|----------|----------|
| `vds_uv_run_package <member-or-package> [args...]` | Running a CLI command from a workspace package at runtime; helper resolves directory names like `vds_cli` to uv project names like `vds-cli` |
| `vds_uv_sync_package <member-or-package> [flags...]` | Syncing one workspace package environment (dev/CI); helper resolves directory names to uv project names |
| `vds_uv_sync_all [flags...]` | Syncing the entire workspace (dev/CI) |
| `vds_resolve_scripts_root` | Resolving the workspace root path for constructing other paths |
| `vds_worktree_uv <uv args...>` | Delegating raw `uv` invocations when none of the above fit |

### Sourcing the helper in a script

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=WHO-project/vds-scripts/scripts/vds_sh_helpers.sh
source "$SCRIPT_DIR/../vds_sh_helpers.sh"   # adjust depth as needed
```

The helper uses `BASH_SOURCE[0]` internally so the relative path in the
`source` call must resolve to where `vds_sh_helpers.sh` actually lives on
disk — not where the calling script lives.

### Running a package command (most common pattern)

```/dev/null/scripts-run-examples.sh#L1-5
# CORRECT — worktree-safe, helper resolves directory name -> uv project name
vds_uv_run_package vds_cli vds-cli doctor

# WRONG — path-coupled, breaks in worktrees and alternate checkouts
./scripts/worktree_uv.sh run --project vds_cli vds-cli schema convert ...
```

### Syncing environments

```/dev/null/scripts-sync-examples.sh#L1-10
# Sync one package/member (fast — only that package's deps)
scripts/bootstrap_uv.sh --package audit_orchestrator

# Sync one package/member with extra uv flags
scripts/bootstrap_uv.sh --package vds_cli --frozen

# Full workspace sync (all members; preferred integrated baseline: Python 3.14+)
scripts/bootstrap_uv.sh

# From within a script (not for interactive setup)
vds_uv_sync_package audit_orchestrator
```

### Self-healing / editable-install exception

Some scripts intentionally deviate from the standard wrapper pattern for
local-dev convenience (e.g., editable installs with `uv pip install -e .`).
Any such script must carry a header comment explaining the deviation and
referencing `scripts/vds_sh_helpers.sh` as the canonical path. Do not migrate
these scripts without evaluating whether the editable-install semantics are
still required.

### Workspace member names and uv package names

The helper accepts either:

- a workspace member directory name such as `vds_cli`, `audit_orchestrator`, or `markdown_orchestrator`, or
- an explicit uv project/package name such as `vds-cli` or `vds-spec-orchestrator`

For maintained scripts, prefer passing the directory/member name to the helper and let it resolve the uv project name from the member `pyproject.toml`. Do not pass filesystem paths like `WHO-project/vds-scripts/vds_cli`.

---

<a id="canonical-vds-cli-editable-install"></a>

## Canonical vds-cli Editable Install

This section defines the MANDATORY install command for local-dev `vds-cli` so the `__file__`-walk in `vds_cli/src/vds_cli/cli.py` correctly resolves the workspace root.

### Install command

```bash
uv tool install --editable ./WHO-project/vds-scripts/vds_cli
```

### Why `--editable` is MANDATORY

uv PR #18891 (2026-04-14) changed `uv tool install` default to non-editable. Without `--editable`, uv builds an sdist at `$HOME/.local/share/uv/tools/vds-cli/` — then `Path(__file__).parent.parent.parent.parent` resolves OUTSIDE the monorepo and SCRIPT_DIR dispatch fails. With `--editable`, uv writes a `.pth` file pointing at `./WHO-project/vds-scripts/vds_cli/src` — `__file__` resolves to live source and the walk lands in the monorepo root.

### SCRIPT_DIR walk

```python
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent
```

The 4 `parent` calls walk from `cli.py` → `vds_cli/` → `src/` → `vds_cli/` → `WHO-project/vds-scripts/` → monorepo root.

### Verification (AC-9.5)

```bash
# Confirm editable install (should print the source path in .pth)
cat "$HOME/.local/share/uv/tools/vds-cli/lib/python"*"/site-packages"/*.pth

# Confirm CLI resolves
which vds-cli
vds-cli --help
```

### Rollback recipe (AC-9.6)

```bash
# If an older non-editable install is present, remove and reinstall:
uv tool uninstall vds-cli
uv tool install --editable ./WHO-project/vds-scripts/vds_cli
```

See also: `skills/vds-scripts-skill/references/platform-bootstrap.md#canonical-vds-cli-editable-install` (the byte-identical mirror maintained by T-13).

---

## PATH Contract for vds-cli

This section documents the minimum PATH components required for `vds-cli` dispatch (including the `shutil.which` call inside `vds_agent_core`).

### Required PATH components

1. `$HOME/.local/bin` — where `uv tool install` places the `vds-cli` shim (entrypoint script).
2. The active workspace `.venv/bin/` — where `uv sync` places per-package CLI shims (e.g. inside the worktree).
3. Normal `$PATH` passthrough — for system utilities `vds-cli` internally calls (`git`, `uv`, etc.).

### Reproducer (AT-1)

```bash
# Simulate narrow PATH (exclude ~/.local/bin and venv bin):
env -i HOME="$HOME" PATH="/usr/bin:/bin" bash -c 'which vds-cli || echo "NOT FOUND (expected)"'

# With full PATH:
bash -c 'which vds-cli'
```

Expected result: the narrow invocation prints `NOT FOUND (expected)` while the full-PATH invocation prints `$HOME/.local/bin/vds-cli`.

### Consumer contract

Any Python module calling `shutil.which("vds-cli")` depends on this PATH contract. If `vds-cli` is not discoverable, the caller MUST raise a diagnostic `RuntimeError` naming `uv tool install --editable ./WHO-project/vds-scripts/vds_cli` as the cure (see T-11).

---

## IntelliJ IDEA Workspace Scripts

This section covers scripts to help set up and maintain the VDS project as a multi-project workspace in IntelliJ IDEA.

## Scripts

### generate_intellij_modules.py

This script generates IntelliJ IDEA module files (`.iml`) for all projects in the VDS monorepo. It helps IntelliJ IDEA recognize each project as a separate module within the workspace.

To run:
```bash
cd vds-scripts/scripts
python generate_intellij_modules.py
```

The script will:
1. Create `.iml` files for each project in the monorepo
2. Properly configure module types (Java, Python, Web) based on project files
3. Place the module files in the appropriate project directories

### update_modules_xml.py

This script updates the IntelliJ IDEA `modules.xml` file to include all projects in the monorepo. This file tells IntelliJ IDEA which modules are part of the workspace.

To run:
```bash
cd vds-scripts/scripts
python update_modules_xml.py
```

The script will:
1. Update the `.idea/modules.xml` file with all projects
2. Organize modules by project groups (LEP, INSURANCE, SAVING, etc.)
3. Preserve existing non-VDS module entries

## Usage

To set up the VDS project as a multi-project workspace in IntelliJ IDEA:

1. Run the module generation script:
   ```bash
   cd vds-scripts/scripts
   python generate_intellij_modules.py
   ```

2. Run the modules.xml update script:
   ```bash
   python update_modules_xml.py
   ```

3. Open the VDS project in IntelliJ IDEA
4. The project should now be organized with all modules grouped by project type

## Benefits

Using these scripts provides several benefits:

1. **Better Organization**: Projects are grouped logically in the IntelliJ IDEA project view
2. **Easier Navigation**: Quickly jump between different services and projects
3. **Independent Builds**: Each module can be built and run independently
4. **Resource Management**: Only load modules you're actively working on
5. **Search Improvements**: Search across all modules simultaneously

## Troubleshooting

If modules don't appear in IntelliJ IDEA:

1. Refresh the project (Ctrl+Alt+Y / Cmd+Alt+Y)
2. Check that the `.iml` files were generated in each project directory
3. Verify the `.idea/modules.xml` file includes all projects
4. Re-import modules through File → Project Structure → Modules