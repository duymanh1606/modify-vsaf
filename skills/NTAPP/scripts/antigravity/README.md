# Antigravity host for VSAF — PoC driver (`vsaf-agy-driver.cjs`)

Run NTAPP VSAF workflows through **Antigravity CLI (`agy -p`)** instead of Claude Code,
**deterministically**. Additive & hybrid: this does NOT touch the Claude path
(`/NTAPP-vsaf-run` MCP glue) — Claude stays primary, Antigravity is the fallback host.

## Why this design

VSAF's engine (`@vsaf/core`) is a **host-agnostic DAG orchestrator**. Today the step loop
is driven by an LLM following `NTAPP-vsaf-run/workflow.md` over the `vsaf_start`/`vsaf_next`
MCP tools — that LLM-driven loop is the consistency-weak link.

This driver replaces the loop with **code**: it imports `@vsaf/core`, runs
`DAGExecutor.step()` in a plain JS `while` loop, and executes each yielded AI node by
shelling out to `agy -p`. Orchestration (deps, fanout, concurrency caps, retries,
skip/idempotency) is deterministic engine code; only per-node *content* is model-driven.
Each AI node = one fresh `agy -p` process = a literal fresh context — exactly what VSAF
fanout sub-tasks want.

## What the PoC proves (run on this repo, June 2026)

- `ad-hoc-per-unit` (12 nodes): driver walked the full real DAG in dependency order to
  `done`, exit 0. Orchestration is host-free.
- `slice-loop` fanout: `dd-per-unit` (mc:5) yielded 4 parallel sub-nodes
  (`~fanout~0..3`); `ds-build-per-fe-unit` (mc:1) yielded one at a time. **The engine's
  `max_concurrency` is honored for free** — it only yields ≤ mc; the driver runs what it gets.

LIVE proven on agy **1.0.14**: the echo smoke workflow ran end-to-end through real agy
(Gemini), and `/NTAPP-agy-vsaf-slice-loop SLICE-01 --dry-run` invoked via `agy -p` drove the
full slice-loop DAG to `FINISHED: done`.

## Usage — 3 layers (simplest last)

```bash
# (a) raw driver
node scripts/antigravity/vsaf-agy-driver.cjs NTAPP/ad-hoc-per-unit --args "<intent>" --yolo

# (b) wrapper (auto-prefixes NTAPP/, default --yolo, --yolo off in dry-run)
./scripts/antigravity/vsaf-agy ad-hoc-per-unit "<intent>"
./scripts/antigravity/vsaf-agy slice-loop SLICE-01 --dry-run

# (c) slash command inside agy (after install-agy-skills.sh) — the requested UX
#     type in the agy TUI, or: agy -p "/NTAPP-agy-vsaf-slice-loop SLICE-01"
/NTAPP-agy-vsaf-slice-loop SLICE-01
/NTAPP-agy-vsaf-ad-hoc-per-unit "Thêm endpoint health-check"
```

Driver flags: `--args` `--project` `--dry-run` `--agy <bin>` `--model` `--print-timeout` `--yolo` `--max-parallel N` `--no-hooks`.
Wrapper env: `VSAF_AGY_MODEL`, `VSAF_AGY_NO_YOLO=1`. Hooks ON by default — see `hooks/README.md`; `--dry-run` prints the hook plan per node.

## Install (machine-local, idempotent)

```bash
bash scripts/antigravity/install-agy-skills.sh   # vsaf-agy -> ~/.local/bin ; glue skills -> ~/.gemini/config/skills
```

## Verified facts (agy 1.0.14) — flags in `buildAgyArgs()`

- `-p`/`--print` non-interactive (accepts large prompts as argv); **no `--output-format`** — print emits plain text, so the driver never sets `structuredOutput` (neither target workflow uses `outputFormat`).
- `--model "<display name>"` e.g. `"Gemini 3.1 Pro (High)"`, `"Gemini 3.5 Flash (Low)"` (from `agy models`).
- `--print-timeout` (agy default 5m; driver default 15m for long dev/review nodes).
- `--dangerously-skip-permissions` (YOLO) needed for headless; or add the repo to `trustedWorkspaces`.
- Driver `spawn` sets `stdio[0]='ignore'` — a default stdin pipe makes agy print mode hang.
- **Skill discovery**: agy 1.0.14 loads user skills only from global `~/.gemini/config/skills/`; in-repo `.agents/skills/` is NOT auto-discovered. Slash command = a skill activated by its `description`.
- **Native hooks**: agy 1.0.14 HAS hooks — 5 events `PreToolUse / PostToolUse / PreInvocation / PostInvocation / Stop` (proto `exa.hooks_pb`; entry `{name,command,args,event,matcher,timeout_millis}`; can block with a reason). No `agy hooks` CLI subcommand and no hooks file until you create one — managed via the interactive `/hooks` form. We use agy-native only for Hook 9 (per-edit PostToolUse); the workflow gate hooks live at driver node boundaries instead (see `hooks/README.md` for why).

## Remaining porting work (not in this PoC)

1. **Leaf skills** → the workflow nodes call `/ntapp-technical-design`, `/NTAPP-feature-design`,
   `/bmad-dev-story`, etc. (125 skills in `.agent/skills/`). For a non-dry-run run, expose these
   to agy's global dir `~/.gemini/config/skills/` (symlink per skill), EXCLUDING the Claude
   `NTAPP-vsaf-*` glue (agy uses the in-repo `agy-skills/` versions instead). Audit skills that
   spawn parallel sub-agents (NTAPP-feature-design F0–F4, NTAPP-ux-design, qa pipelines) —
   repoint their subagent step to Antigravity subagents. *(Glue slash commands: DONE — see
   `agy-skills/` + `install-agy-skills.sh`.)*
2. **Hooks** → **DONE for slice-loop + ad-hoc-per-unit** (see `hooks/README.md`). The 8 gate
   hooks those workflows reference (3,4,5,5b,6,7,8,10) fire at **driver node boundaries**
   (`hooks/run-hooks.cjs`, reusing `hooks/*.sh` verbatim) — a blocking gate halts the run.
   Hook 9 (build_loop, per-edit) runs as a driver post-node sweep AND as an **agy-native
   PostToolUse** hook (`hooks/agy-posttool-shim.cjs`, matcher `write_to_file|replace_file_content`).
   git pre-commit (Rules 1–9) reused unchanged. Per-unit `HOOK_TARGET_ID` removes the parallel
   fanout race (Claude path unchanged — `hooks/tests/run.sh` still 15/15).
   *Remaining*: the other ~7 event hooks (1,2,12,13,14,15,16) for the batch-phase workflows
   (create_prd_epics, reproduce_architecture, slice-planning, feature-triage) — same pattern.
3. **MCP** → move gitnexus/figma/etc. into `~/.gemini/config/mcp_config.json`.
4. **Engine** → optionally upstream this as a `provider: antigravity` patch under
   `scripts/engine-patches/` so `vsaf run` handles AI nodes headlessly (today it rejects them).
5. **Hardening** → convert `resolve-slice-units` / `resolve-slice-modules` (and ad-hoc's
   `.current-unit-id` plumbing) from `prompt:` → `bash:` nodes so the engine runs them
   directly (zero LLM) — removes fanout-prep flakiness regardless of host.
