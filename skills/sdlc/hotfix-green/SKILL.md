---
name: hotfix-green
description: "Hotfix Phase 3 — TDD GREEN — write the minimal fix to make the failing test pass"
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Hotfix Phase 3: TDD GREEN — Minimal Fix

You are a Senior Developer applying a surgical fix. Mission: write the SMALLEST possible code change to make the failing test pass. Nothing more.

## Progress Protocol

Print progress at each step:
```
[HOTFIX-GREEN] [step/3] description... ⏳
[HOTFIX-GREEN] [step/3] description... ✅
```

## Index Protection

⛔ Do NOT modify `graphify-out/` or `.gitnexus/` — READ only.

## Phase Entry Protocol

```
[HOTFIX-GREEN] [1/3] Verifying failing test... ⏳
```

1. Read `.vsaf/docs/hotfixes/{bug-id}/01-analysis.md` — understand root cause and fix strategy
2. Locate the test file written in the RED phase
3. Run the test — confirm it FAILS (if it passes, something changed — STOP and investigate)
4. Read the production code that needs to be fixed

```
[HOTFIX-GREEN] [1/3] Verifying failing test... ✅
```

## Tasks

### Step 2: Apply Minimal Fix

```
[HOTFIX-GREEN] [2/3] Applying minimal fix... ⏳
```

1. Apply the fix strategy from the analysis
2. Change ONLY what is necessary to fix the bug
3. Rules for the fix:
   - Smallest possible diff
   - Do NOT refactor surrounding code
   - Do NOT fix other issues you notice
   - Do NOT add features
   - Do NOT change formatting of untouched code
   - 1 bug = 1 focused fix
4. Apply SonarQube rules on the changed code:
   - Issues = 0, Blocker = 0, Critical = 0
   - Security Hotspots = 0
   - No new code smells introduced

```
[HOTFIX-GREEN] [2/3] Applying minimal fix... ✅
```

### Step 3: Run Tests — MUST PASS

```
[HOTFIX-GREEN] [3/3] Running tests... ⏳
```

1. Run the specific reproduction test — it MUST PASS now
2. If it still FAILS → read the error, adjust the fix, try again
3. Run the FULL test suite — check for regressions
4. If any existing test FAILS → the fix introduced a regression
   - Analyze which test failed and why
   - Adjust the fix to not break existing behavior
   - Re-run until all tests pass

```
[HOTFIX-GREEN] [3/3] Running tests... ✅ (reproduction test PASS + full suite PASS)
```

## Phase Exit Protocol

Print PHASE REPORT:
- Bug: {bug-id}
- Status: TDD GREEN COMPLETED
- Fix applied: {one-line description of what changed}
- Files changed: {list of changed files}
- Reproduction test: PASS
- Full test suite: PASS ({N}/{N} tests)
- Next step: test-gate (automatic) → `/hotfix-review`

## Rules

- ⛔ MINIMAL fix only — do NOT refactor, do NOT fix other things
- ⛔ Do NOT modify `graphify-out/` or `.gitnexus/`
- ⛔ Do NOT change any test file from the RED phase (the test must stay as-is)
- If the fix requires changing more than 3 files → STOP and verify with user that this is still a hotfix scope
- The reproduction test must pass WITHOUT modifying the test
- All existing tests must continue to pass (zero regressions)
