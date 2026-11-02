---
name: NTAPP-agy-vsaf-slice-loop
description: 'Antigravity host for the NTAPP slice-loop workflow. Activate when the user types "/NTAPP-agy-vsaf-slice-loop <slice_id>" or asks to run / build a slice end-to-end (e.g. SLICE-01). Runs the deterministic VSAF→Antigravity driver (vsaf-agy); it orchestrates Stage 3→4→5 for the slice. Do NOT interpret the workflow yourself.'
---

# NTAPP VSAF Slice Loop — Antigravity host

This is the Antigravity counterpart of the Claude `/NTAPP-vsaf-slice-loop` glue.
Difference: it does NOT drive the `vsaf_start`/`vsaf_next` MCP loop. It runs a
**deterministic code driver** (`vsaf-agy`) that imports `@vsaf/core`, walks the DAG
in code, and executes each node via `agy -p`. Your only job is to launch it.

## What to do when activated

The user invokes: `/NTAPP-agy-vsaf-slice-loop <slice_id> [extra flags]`
(e.g. `/NTAPP-agy-vsaf-slice-loop SLICE-01`, or `... SLICE-01 --dry-run`).

Do EXACTLY this, nothing else:

1. Treat everything after the command name as ARGS (the slice id plus any flags).
2. From the current project root, run this terminal command and stream its full output:

   ```
   vsaf-agy slice-loop <ARGS>
   ```

   `vsaf-agy` is on PATH (installed by `scripts/antigravity/install-agy-skills.sh`).
   It runs `scripts/antigravity/vsaf-agy-driver.cjs` which owns all orchestration
   (dependencies, fanout, max_concurrency, idempotent skip, resume).

3. When it finishes, report the driver's final status line (`FINISHED: done|failed`)
   and any changed artifacts. Do NOT re-run, re-order, or re-interpret nodes yourself —
   the driver is the source of truth.

## Notes

- Preconditions (same as Claude lane): WBS locked + slice plan approved + `<slice_id>` exists.
- Add `--dry-run` to preview the DAG without calling agy per node.
- If `vsaf-agy: command not found`, run `bash scripts/antigravity/install-agy-skills.sh` first.
