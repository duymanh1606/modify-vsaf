# UV Workspace Alignment Verification — 2026-04-18

Spec: `.gpt-5.4/specs/scripts-uv-workspace-alignment/` v0.5.0
Branch: `phase/frs-9-11-vds-cli-consistency`
Tasks: T-9, T-10, T-11, T-12, T-13

## AC-9.5 — Editable Install Evidence (5 rows)

### Row 1: `.pth` file contents

```
File: /Users/vds-ai/.local/share/uv/tools/vds-cli/lib/python3.14/site-packages/_editable_impl_vds_google_sheets_orchestrator.pth
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts/google_sheets_orchestrator/src

File: /Users/vds-ai/.local/share/uv/tools/vds-cli/lib/python3.14/site-packages/_vds_cli.pth
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts/vds_cli/src

File: /Users/vds-ai/.local/share/uv/tools/vds-cli/lib/python3.14/site-packages/_virtualenv.pth
import _virtualenv

File: /Users/vds-ai/.local/share/uv/tools/vds-cli/lib/python3.14/site-packages/_vds_cli_common.pth
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts/vds_cli_common/src

File: /Users/vds-ai/.local/share/uv/tools/vds-cli/lib/python3.14/site-packages/_editable_impl_vds_bitbucket_orchestrator.pth
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts/bitbucket_orchestrator/src
```

Interpretation: `.pth` files point at live source trees under `WHO-project/vds-scripts/` — editable install confirmed across all workspace members (vds_cli, vds_cli_common, google_sheets_orchestrator, bitbucket_orchestrator).

### Row 2: `which vds-cli`

```
/Users/vds-ai/.local/bin/vds-cli
```

Interpretation: Shim installed at `~/.local/bin/vds-cli` per uv tool convention. Executable is on PATH without any workspace-root coupling.

### Row 3: `vds_cli.cli.__file__`

```
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts/vds_cli/src/vds_cli/cli.py
```

Interpretation: Python imports live source under monorepo `WHO-project/vds-scripts/vds_cli/src/` (not sdist cache). Editable install resolves to the development source tree.

### Row 4: SCRIPT_DIR walk resolves to monorepo root

```
/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds/WHO-project/vds-scripts
```

Interpretation: The 4-parent walk at `cli.py:31` (`Path(__file__).resolve().parent.parent.parent.parent`) lands in `WHO-project/vds-scripts` — the workspace root. SCRIPT_DIR dispatch is functional for routing sub-orchestrators.

### Row 5: subcommand count

```
31
```

Command: `vds-cli --help 2>&1 | grep "^│ [a-z]" | wc -l`

Interpretation: 31 registered subcommands, well above the `>= 25` spec acceptance threshold. All registered subcommands match expected router shape.

## AT-2 — shutil.which dispatch from outside workspace root

### From umbrella monorepo root

```
umbrella_root: /Users/vds-ai/.local/bin/vds-cli
```

Command: `cd "/Users/vds-ai/Library/Mobile Documents/com~apple~CloudDocs/project/vds" && python3 -c "import shutil; print('umbrella_root:', shutil.which('vds-cli'))"`

### From `$HOME`

```
home_dir: /Users/vds-ai/.local/bin/vds-cli
```

Command: `cd "$HOME" && python3 -c "import shutil; print('home_dir:', shutil.which('vds-cli'))"`

### From filesystem root

```
fs_root: /Users/vds-ai/.local/bin/vds-cli
```

Command: `cd / && python3 -c "import shutil; print('fs_root:', shutil.which('vds-cli'))"`

Interpretation: `shutil.which("vds-cli")` resolves identically (`/Users/vds-ai/.local/bin/vds-cli`) from any CWD — umbrella root, `$HOME`, and filesystem root. PATH-based dispatch is CWD-independent. This confirms FR-11 modern-only posture (no `uv run` fallback, no path-coupling). The executor pattern using `shutil.which` is safe for all agent invocation contexts.

## Closure

- T-9 canonical block: committed in 55f35c9 (scripts/README.md)
- T-10 PATH contract: committed in e5066df (scripts/README.md)
- T-11 shutil.which executor: committed in 4bb8dc6 (vds_agent_core/skills/executor.py + tests)
- T-12 this verification note: committed in this change
- T-13 byte-mirror: committed in c9aba41 (vds-skills/.../platform-bootstrap.md)

All AC-9.5 and AT-2 requirements fulfilled. Spec v0.5.0 closure criteria met.
