---
name: hotfix-implement
description: "Hotfix Phase 3 — TDD implementation: RED → GREEN → REFACTOR, minimal fix, SonarQube-in-loop"
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Hotfix Phase 3: Implementation (TDD)

You are a Senior Software Engineer performing a surgical fix. Mission: implement the fix using strict TDD — write failing test first, make it pass with minimal code, refactor. No subagents, no parallel epics — hotfixes are focused single-area changes.

## Progress Protocol

Print progress at each step:
```
[HOTFIX-IMPL] [step/6] description... ⏳
[HOTFIX-IMPL] [step/6] description... ✅
```

## Index Protection

⛔ Do NOT modify `graphify-out/` or `.gitnexus/` — READ only.

## Phase Entry Protocol

```
[HOTFIX-IMPL] [1/6] Checking input artifacts... ⏳
```

1. Input:
   - `.vsaf/docs/hotfixes/{bug-id}/02-prd.md`
   - `.vsaf/docs/hotfixes/{bug-id}/01-analysis.md`
2. Verify BOTH files exist:
   - Missing → Stop: "Run previous phases first."
3. Check `02-prd.md` has `## Gate: APPROVED`
   - No Gate → Stop: "PRD not approved. Get approval first."
4. Extract from PRD: FRs, acceptance criteria, scope boundary
5. Extract from analysis: root cause (file:line), affected files, fix strategy
6. Read `CONTEXT.md`

```
[HOTFIX-IMPL] [1/6] Checking input artifacts... ✅
```

## Tasks

### Step 2: Branch Setup

```
[HOTFIX-IMPL] [2/6] Creating hotfix branch... ⏳
```

```bash
git checkout -b hotfix/{bug-id}
```

If branch already exists → switch to it.

```
[HOTFIX-IMPL] [2/6] Creating hotfix branch... ✅
```

### Step 3: TDD Cycle — `/tdd` Methodology

```
[HOTFIX-IMPL] [3/6] TDD cycle — RED → GREEN → REFACTOR... ⏳
```

Use `/tdd` methodology — behavior-based, vertical slice:

**For each FR in the PRD:**

1. **RED — Write failing test FIRST**
   - Test the BEHAVIOR described in the acceptance criteria
   - Test the PUBLIC INTERFACE, not internals
   - Include the regression test: reproduce the original bug → MUST FAIL before fix
   - Run test → confirm it FAILS (red)
   - ⚠️ If test passes without code changes → the test is wrong or the bug is already fixed

2. **GREEN — Write MINIMAL code to pass**
   - Change ONLY what is needed to make the test pass
   - Stay within the scope boundary from PRD
   - Apply SonarQube rules while writing (see below)
   - Run test → confirm it PASSES (green)

3. **REFACTOR — Clean without changing behavior**
   - Remove duplication introduced by the fix
   - Improve naming if needed
   - Run ALL tests → still green

**Repeat for each FR.** Typically 1-3 cycles for a hotfix.

```
[HOTFIX-IMPL] [3/6] TDD cycle complete ✅
```

### Step 4: SonarQube Self-Check

```
[HOTFIX-IMPL] [4/6] SonarQube quality check... ⏳
```

Apply DURING Step 3 (not after). After the fix is complete, final sweep:

| Metric | Threshold |
|--------|-----------|
| New Issues | = 0 |
| Blocker/Critical | = 0 |
| Vulnerabilities | = 0 |
| Duplicated Lines (new) | ≤ 3% |

- If project has SonarQube → run `sonar-scanner` incremental
- If not → Claude self-reviews changed files against metrics above

```
[HOTFIX-IMPL] [4/6] SonarQube quality check... ✅
```

### Step 5: Build & Test Verification

```
[HOTFIX-IMPL] [5/6] Build & test verification... ⏳
```

**MANDATORY — hard gate:**

1. **Compile**: Build entire project → 0 errors
   - Java: `mvn compile` / `gradle build`
   - Node: `npm run build` / `tsc --noEmit`
   - Angular: `ng build`
   - Go: `go build ./...`
   - FAIL → fix immediately

2. **Full test suite**: Run ALL tests (not just new ones)
   - `npm test` / `mvn test` / equivalent
   - ALL tests MUST pass — no regressions
   - FAIL → use `/diagnose` to find the issue

3. **Regression test confirmation**: The specific test from Step 3 RED phase → now PASSES

⚠️ DO NOT exit if build fails or tests fail. This is a hard gate.

```
[HOTFIX-IMPL] [5/6] Build & test verification... ✅
```

### Step 6: Impact Verification

```
[HOTFIX-IMPL] [6/6] Impact verification via GitNexus... ⏳
```

Use GitNexus `impact` — verify the fix did not break anything outside blast radius.

If unexpected impact detected → evaluate:
- Within scope boundary → OK, note in impl log
- Outside scope boundary → STOP, escalate to user

```
[HOTFIX-IMPL] [6/6] Impact verification... ✅
```

## Output

Write file: `.vsaf/docs/hotfixes/{bug-id}/03-impl-log.md`

```markdown
# Implementation Log: {bug-id}

## Branch
`hotfix/{bug-id}`

## TDD Cycles

### FR-001: {title}
- RED: {test file}:{test name} — FAILED ✓
- GREEN: {changed files} — PASSED ✓
- REFACTOR: {what was cleaned}

### FR-002: {title} (if applicable)
...

## Files Changed
| File | Change type | Lines |
|------|-------------|-------|
| {file} | Modified / Added | +{n} -{m} |

## Test Results
- New tests: {count}
- Regression test: {test name} — PASS
- Full suite: {total} tests, all PASS

## SonarQube
- Issues: 0
- Vulnerabilities: 0
- Duplication: {n}%

## Build
- Compile: PASS
- Full test suite: PASS
```

## Phase Exit Protocol

Print PHASE REPORT:
- Bug: {bug-id}
- Status: IMPLEMENTATION COMPLETED
- Branch: `hotfix/{bug-id}`
- Tests: {new} new, {total} total — all PASS
- Files changed: {count}
- Output: `.vsaf/docs/hotfixes/{bug-id}/03-impl-log.md`
- Next step: `/sdlc-hotfix-ship`

Update `.vsaf/docs/STATUS.md`.

> Artifacts saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- ⛔ Do NOT write code without a failing test first (TDD)
- ⛔ Do NOT modify `graphify-out/` or `.gitnexus/`
- ⛔ Do NOT exceed scope boundary defined in PRD
- ⛔ Do NOT use subagent-driven development — hotfixes are sequential, focused
- Code MUST compile — hard gate, no exceptions
- Full test suite MUST pass — no regressions allowed
- If fix fails 3 times → STOP, escalate to user
- If scope drift detected → STOP, go back to PRD
