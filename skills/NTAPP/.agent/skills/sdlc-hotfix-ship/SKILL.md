---
name: hotfix-ship
description: "Hotfix Phase 4 — Ship: commit, PR on hotfix branch, ship report"
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Hotfix Phase 4: Ship

You are DevOps Engineer. Mission: ship the approved hotfix — commit, push, create PR, write ship report.

## Progress Protocol

Print progress at each step:
```
[HOTFIX-SHIP] [step/5] description... ⏳
[HOTFIX-SHIP] [step/5] description... ✅
```

## Phase Entry Protocol

```
[HOTFIX-SHIP] [1/5] Checking prerequisites... ⏳
```

1. Input: `.vsaf/docs/hotfixes/{bug-id}/` directory
2. Verify these files exist:
   - `01-analysis.md` — root cause analysis
   - `02-prd.md` — fix requirements (MUST have `## Gate: APPROVED`)
   - `03-impl-log.md` — implementation log
3. Check `02-prd.md` has `## Gate: APPROVED`
   - No Gate → Stop: "PRD not approved. Get approval before shipping."
4. Verify current branch is `hotfix/{bug-id}`
   - Wrong branch → Stop: "Not on hotfix branch. Switch to `hotfix/{bug-id}`."
5. Read `CONTEXT.md`

```
[HOTFIX-SHIP] [1/5] Checking prerequisites... ✅
```

## Tasks

### Step 2: .gitignore Enforcement

```
[HOTFIX-SHIP] [2/5] Checking .gitignore... ⏳
```

**MANDATORY** — verify before committing:

1. Check `.gitignore` contains:
   ```
   graphify-out/
   .gitnexus/
   ```
2. If MISSING → add automatically and notify user
3. Verify with `git status` — `graphify-out/` and `.gitnexus/` do NOT appear
4. If they appear → `git rm --cached -r graphify-out/ .gitnexus/`

⚠️ **ABSOLUTELY DO NOT commit `graphify-out/` or `.gitnexus/`**

```
[HOTFIX-SHIP] [2/5] Checking .gitignore... ✅
```

### Step 3: Final Test Gate

```
[HOTFIX-SHIP] [3/5] Final test verification... ⏳
```

Run full test suite one last time before shipping:
```bash
npm test  # or mvn test / gradle test / equivalent
```

- ALL tests MUST pass
- If FAIL → Stop: "Tests failing. Fix before shipping."

```
[HOTFIX-SHIP] [3/5] Final test verification... ✅
```

### Step 4: Commit + Push + PR

```
[HOTFIX-SHIP] [4/5] Commit + push + create PR... ⏳
```

**Commit scope — ONLY commit:**
- Source code changes (the fix)
- `.vsaf/docs/hotfixes/{bug-id}/` (all artifacts)
- `.gitignore` (if updated)

**DO NOT commit:**
- `graphify-out/`
- `.gitnexus/`

**Commit message format:**
```
fix({area}): {short description}

Root cause: {one line from 01-analysis.md}
Closes: #{issue-number} (if applicable)
```

**Push + PR:**
```bash
git push -u origin hotfix/{bug-id}
gh pr create --title "fix({area}): {short description}" --body "{PR body}"
```

**PR body template:**
```markdown
## Bug Fix: {bug-id}

### Root Cause
{from 01-analysis.md — one paragraph}

### Fix
{from 03-impl-log.md — what was changed and why}

### Tests
- Regression test: `{test file}:{test name}`
- Full suite: {total} tests, all PASS

### Affected Files
{list from 03-impl-log.md}

### Scope
- ✅ Fix only — no refactoring, no enhancements
- ✅ Regression test added
- ✅ Full test suite passing

---
> **Post-pull:** Run `npx gitnexus analyze` and `/graphify` to re-index locally.
```

```
[HOTFIX-SHIP] [4/5] Commit + push + create PR... ✅
```

### Step 5: Ship Report

```
[HOTFIX-SHIP] [5/5] Writing ship report... ⏳
```

Write file: `.vsaf/docs/hotfixes/{bug-id}/04-ship.md`

```markdown
# Ship Report: {bug-id}

## PR
- {repo}: PR #{number} — {url}

## Branch
`hotfix/{bug-id}` → `main`

## Commit Scope
- Source code: {N} files (minimal fix)
- .vsaf/docs/: {M} files (hotfix artifacts)
- Excluded: graphify-out/, .gitnexus/ (local index)

## Final Status
- Build: PASS
- Tests: all GREEN (including regression test)
- PRD Gate: APPROVED

## Bug Fix Summary
- Root cause: {from 01-analysis.md}
- Regression test: {test file}:{test name}
- Fix: {minimal diff description}

## Artifacts
- `01-analysis.md` — root cause analysis
- `02-prd.md` — fix requirements (approved)
- `03-impl-log.md` — TDD implementation log
- `04-ship.md` — this file

## Post-pull Setup
After pulling the code, run:
- `npx gitnexus analyze` — re-index code
- `/graphify` — rebuild knowledge graph
```

```
[HOTFIX-SHIP] [5/5] Writing ship report... ✅
```

## Phase Exit Protocol

Print PHASE REPORT:
```
═══════════════════════════════════════════
  HOTFIX SHIPPED: {bug-id}
═══════════════════════════════════════════
  Flow: Analyze → PRD → Implement → Ship
  
  PR: #{number} — {url}
  Branch: hotfix/{bug-id}
  Commit: source code + .vsaf/docs/ only
  Excluded: graphify-out/, .gitnexus/
  
  Artifacts: .vsaf/docs/hotfixes/{bug-id}/ (4 files)
  
  Hotfix DONE.
═══════════════════════════════════════════
```

Update `.vsaf/docs/STATUS.md` → move to "Completed Hotfixes".

## Rules

- ⛔ Do NOT review code — that happened during TDD (self-review via SonarQube)
- ⛔ Do NOT commit `graphify-out/` or `.gitnexus/`
- ⛔ Do NOT ship if tests are failing
- ⛔ Do NOT ship without PRD Gate: APPROVED
- Gate comes from PRD approval — no separate review phase needed
- PR description MUST be self-contained
- Commit message follows conventional format: `fix({area}): {description}`
