---
name: NTAPP-agy-vsaf-ad-hoc-per-unit
description: 'Antigravity host for the NTAPP ad-hoc-per-unit workflow (Lane 4). Activate when the user types "/NTAPP-agy-vsaf-ad-hoc-per-unit <intent | unit_id>" or asks to spec-build-demo one independent unit. Runs the deterministic VSAF→Antigravity driver (vsaf-agy). Do NOT interpret the workflow yourself.'
---

# NTAPP VSAF Ad-hoc-per-unit — Antigravity host

Antigravity counterpart of the Claude `/NTAPP-vsaf-ad-hoc-per-unit` glue. Runs the
deterministic `vsaf-agy` driver (it imports `@vsaf/core`, walks the DAG in code,
executes each node via `agy -p`). Your only job is to launch it.

## What to do when activated

The user invokes: `/NTAPP-agy-vsaf-ad-hoc-per-unit <intent | file-path | unit_id> [extra flags]`.

Do EXACTLY this, nothing else:

1. Treat everything after the command name as ARGS (the intent/unit id plus any flags).
   If the intent contains spaces, keep it as a single quoted string.
2. From the current project root, run this terminal command and stream its full output:

   ```
   vsaf-agy ad-hoc-per-unit "<ARGS>"
   ```

3. Report the driver's final status (`FINISHED: done|failed`) and changed artifacts.
   Do NOT re-run or re-interpret nodes yourself.

## Notes

- Precondition: WBS locked; unit resolves into the WBS (the driver's first node appends it if new).
- Add `--dry-run` to preview without calling agy per node.
- If `vsaf-agy: command not found`, run `bash scripts/antigravity/install-agy-skills.sh` first.
