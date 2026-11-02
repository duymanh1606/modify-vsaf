# NTAPP hooks → Antigravity host (slice-loop + ad-hoc-per-unit)

Ports the NTAPP event hooks (`hooks/*.sh`) so they enforce when `slice-loop.yaml` and
`ad-hoc-per-unit.yaml` run through the **Antigravity driver** (`vsaf-agy-driver.cjs`)
instead of Claude Code. The hook *scripts* are reused **verbatim** — only the wiring that
Claude's event bus provided is rebuilt here.

## Why the wiring had to be rebuilt

The hooks were bound to Claude Code events (`UserPromptSubmit`, `SubagentStop`,
`PostToolUse`). The driver runs **one `agy -p` process per DAG node**, so there is no Claude
event bus. Two enforcement planes replace it, each owning what it is actually good at:

| Plane | Owns | Why there |
|---|---|---|
| **Driver node-boundary** (`run-hooks.cjs`) | gate Hooks **3, 4, 5, 5b, 6, 7, 8, 10** | Only the driver has the whole-DAG view → a blocking gate can halt the *workflow*. An agy in-node hook can only re-prompt its own node. |
| **agy-native PostToolUse** (`agy-posttool-shim.cjs`) | Hook **9** build_loop (per-edit) | Fires mid-node, per file write — the driver only sees node boundaries. |
| **git pre-commit** (unchanged) | Rules **1–9** at commit | Commit-time hard backstop. |

agy *does* have native hooks (5 events: `preToolHooks`/`postToolHooks`/`preInvocationHooks`/
`postInvocationHooks`/`stopHooks`; entry = `{name,command,args,event,matcher,timeout_millis}`;
can block with a reason). But mapping the *gates* onto agy `Stop`/`PreInvocation` is worse than
the driver: `PreInvocation` fires before *every* LLM turn (too broad for slash-command gates),
and a `Stop` hook cannot stop the cross-node DAG. So only the genuinely per-edit Hook 9 lives
in agy-native; everything else lives in the driver.

## Event mapping

| NTAPP hook | Claude event | Driver phase | Blocking |
|---|---|---|---|
| 3 stage3-input-gate | UserPromptSubmit | `pre` (techspec / ux / dd) | yes |
| 4 stage4a-completeness | SubagentStop | `post` (dd) | warn |
| 5 ds-delta-router | SubagentStop | `post` (ui-schema) | warn (recorder) |
| 5b ds-build-approval-gate | UserPromptSubmit | `pre` (ds-build) | yes |
| 6 build-component-verify | SubagentStop | `post` (ds-build) | yes |
| 7 story-bridge-gate | SubagentStop | `post` (story-bridge) | yes |
| 8 atdd-classifier | UserPromptSubmit | `pre` (dev) | warn (advisory) |
| 9 build-loop | PostToolUse | `post` sweep + agy-native | yes |
| 10 verification-gate | UserPromptSubmit | `post` (dev, slice-loop only) | yes |

Lane fidelity: `ad-hoc-per-unit` is the **relaxed** lane — no Hook 3 (skips Stage 3, no slice
plan) and no Hook 10 (test+lint only), matching each node's YAML comment and CLAUDE.md.

## Determinism win over Claude

Claude's `SubagentStop` gates pick *"the newest artifact in the last 5 min"* — racy across a
parallel fanout (mc:5). The driver knows each node's exact unit id (from the fanout marker path
or `.current-unit-id`) and passes **`HOOK_TARGET_ID`**, so hooks 4/5/6/7 resolve *that* unit's
file. Backward-compatible: when the env is unset the hooks fall back to the `-mmin` heuristic →
the Claude path is unchanged (proven by `hooks/tests/run.sh`, 15/15 pass).

## Files

| File | Role |
|---|---|
| `workflow-hooks.js` | declarative node → {pre, post} hook map for both workflows |
| `run-hooks.cjs` | executor: synth stdin, run `hooks/*.sh`, exit 2 = block, build_loop sweep, target resolution |
| `agy-posttool-shim.cjs` | agy PostToolUse event JSON → build_loop.sh stdin (per-edit Hook 9) |
| `install-agy-hooks.sh` | chmod shim + emit reference JSON + print `/hooks` form values |
| `agy-hooks.reference.json` | schema reference (generated) |
| `test-driver-hooks.cjs` | harness: 10 cases (target resolve, block/pass gates, sweep, disable) |

## Run

```bash
node scripts/antigravity/hooks/test-driver-hooks.cjs   # unit: executor + targeting + sweep
bash hooks/tests/run.sh                                 # regression: Claude path still 15/15

# Hooks are ON by default in the driver:
./scripts/antigravity/vsaf-agy slice-loop SLICE-01      # gates fire at node boundaries
./scripts/antigravity/vsaf-agy slice-loop SLICE-01 --dry-run   # prints the hook plan per node
```

Disable: `--no-hooks` · `NTAPP_AGY_NO_HOOKS=1` · `DISABLE_HOOK_<NAME>=1` · `DISABLE_HOOKS_ALL=1`.
Hooks dir resolution: `NTAPP_HOOKS_DIR` → `<project>/hooks` → `<project>/.claude/hooks`.

## Known limits

- **Hook 10 timing**: Claude fires it on the `--commit` action (pre-commit). The driver can't
  intercept the commit *inside* the opaque agy node, so it runs as a **post-node** verification
  (tests/sonar/review-recency). It detects + halts the run if the suite fails, but the inner
  commit may already have landed — git pre-commit is the prevention point for Rules 1–9.
- **agy-native Hook 9** must be added via the `/hooks` TUI form (1.0.14 has no import CLI). It
  is optional: the driver post-node sweep + git pre-commit already cover Hook 9 without it.
