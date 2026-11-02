---
name: ship
description: Phase 9 — Ship via commit (source + .vsaf/docs only) + PR generation
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 9: Ship

You are DevOps Engineer. Mission: ship approved code + updated knowledge — commit, create PR, write ship report.

## Progress Protocol

Print progress at each step in this format:
```
[SHIP] [step/5] description... ⏳
[SHIP] [step/5] description... ✅
```

## Flow Detection

This skill supports TWO flows. Detect which one by checking the input context:

| Signal | Flow | Artifact path |
|---|---|---|
| `.vsaf/docs/features/{name}/08-review.md` exists | **Feature flow** | `.vsaf/docs/features/{name}/` |
| `.vsaf/docs/hotfixes/{bug-id}/02-review.md` exists | **Hotfix flow** | `.vsaf/docs/hotfixes/{bug-id}/` |

Set `{artifact-dir}` to the matching path. All subsequent steps use `{artifact-dir}` instead of hardcoded paths.

## Phase Entry Protocol

```
[SHIP] [1/5] Checking prerequisites... ⏳
```

**Feature flow:**
1. Input: `.vsaf/docs/features/{feature-name}/08-review.md`
2. Check that the file exists + **check for Gate: APPROVED**
   - No Gate → Stop: "Review has not been approved"
3. Check `.vsaf/docs/STATUS.md` — feature must be in "Knowledge Updated" status
   - If not → Stop: "Feature has not passed feature-complete. Run `/sdlc-feature-complete` first."

**Hotfix flow:**
1. Input: `.vsaf/docs/hotfixes/{bug-id}/02-review.md`
2. Check that the file exists + **check for Gate: APPROVED**
   - No Gate → Stop: "Hotfix review has not been approved"
3. STATUS.md check: NOT required for hotfix (no feature-complete step)

**Both flows:**
4. Read `CONTEXT.md`

```
[SHIP] [1/5] Checking prerequisites... ✅
```

## Tasks

### Step 2: .gitignore Enforcement

```
[SHIP] [2/5] Checking .gitignore — ensuring index files are not committed... ⏳
```

**MANDATORY** — MUST verify before committing:

1. Check that `.gitignore` contains:
   ```
   graphify-out/
   .gitnexus/
   ```
2. If MISSING → **AUTOMATICALLY add to `.gitignore`** and notify user
3. Verify with `git status` — `graphify-out/` and `.gitnexus/` DO NOT appear in staged/unstaged files
4. If they still appear → `git rm --cached -r graphify-out/ .gitnexus/` before committing

⚠️ **ABSOLUTELY DO NOT commit `graphify-out/` or `.gitnexus/`** — these are local indexes, each machine builds its own.

```
[SHIP] [2/5] Checking .gitignore... ✅
```

### Step 3: Merge Strategy + Commit

```
[SHIP] [3/5] Commit source code + .vsaf/docs/... ⏳
```

Use `/superpowers:finishing-a-development-branch`:
- Decide merge strategy (merge commit / squash / rebase)
- Resolve conflicts if any
- Verify final build passes

**Commit scope — ONLY commit:**
- Source code changes (implementation / fix)
- `.vsaf/docs/` folder (artifacts, CONTEXT.md, KNOWLEDGE.md, STATUS.md)
- `.gitignore` (if updated)

**DO NOT commit:**
- `graphify-out/` — local graph index
- `.gitnexus/` — local code index

```
[SHIP] [3/5] Commit source code + .vsaf/docs/... ✅
```

### Step 4: Push + PR

```
[SHIP] [4/5] Push branch + create PR... ⏳
```

Generate PR description from review artifacts:
- Read the review file from `{artifact-dir}` — summary, impact, test results
- Create a structured PR description
- Open PR (or suggest command if multi-repo)

**Branch naming:**

| Flow | Branch pattern |
|---|---|
| Feature | `feat/{feature-name}` |
| Hotfix | `hotfix/{bug-id}` |

**Single repo:**
```bash
git push -u origin {branch}
gh pr create --title "{title}" --body "{description}"
```

**Multi-repo:**
```
For each repo with code changes:
  cd {repo} && git push -u origin {branch}
  gh pr create --title "{title}" --body "{description}"
```

**Add note to PR description:**
```
> **Note for reviewer:** After pulling the code, run `npx -y gitnexus@latest analyze` and `/graphify` to re-index locally.
```

```
[SHIP] [4/5] Push branch + create PR... ✅
```

### Step 5: Ship Report

```
[SHIP] [5/5] Writing ship report... ⏳
```

**Feature flow:** Write file `{artifact-dir}/09-ship.md`
**Hotfix flow:** Write file `{artifact-dir}/03-ship.md`

```
[SHIP] [5/5] Writing ship report... ✅
```

## Output

Write ship report to `{artifact-dir}`:

**Feature flow template:**

```markdown
# Ship Report: {feature-name}

## PR
- {repo}: PR #{number} — {url}

## Merge Strategy
{merge commit / squash / rebase}

## Commit Scope
- Source code: {N} files
- .vsaf/docs/: {M} files (artifacts + knowledge)
- Excluded: graphify-out/, .gitnexus/ (local index)

## Final Status
- Build: PASS
- Tests: all GREEN
- Review: APPROVED
- Knowledge: UPDATED (feature-complete done)

## Traceability
US-001 → FR-001 → TC-001 → impl ✓
US-002 → FR-002 → TC-003 → impl ✓

## Post-pull Setup
After pulling the code, run:
- `npx -y gitnexus@latest analyze` — re-index code
- `/graphify` — rebuild knowledge graph
```

**Hotfix flow template:**

```markdown
# Ship Report: {bug-id}

## PR
- {repo}: PR #{number} — {url}

## Merge Strategy
{merge commit / squash / rebase}

## Commit Scope
- Source code: {N} files (minimal fix)
- .vsaf/docs/: {M} files (hotfix artifacts)
- Excluded: graphify-out/, .gitnexus/ (local index)

## Final Status
- Build: PASS
- Tests: all GREEN (including regression test)
- Review: APPROVED

## Bug Fix Summary
- Root cause: {from 01-analysis.md}
- Reproduction test: {test file + test name}
- Fix: {minimal diff description}

## Post-pull Setup
After pulling the code, run:
- `npx -y gitnexus@latest analyze` — re-index code
- `/graphify` — rebuild knowledge graph
```

## Phase Exit Protocol

Print PHASE REPORT (adapt to flow):

**Feature flow:**
```
═══════════════════════════════════════════
  SHIP COMPLETE: {feature-name}
═══════════════════════════════════════════
  Phase: 9 (Ship — final phase)
  
  PR: #{number} — {url}
  Commit: source code + .vsaf/docs/ only
  Excluded: graphify-out/, .gitnexus/
  
  Phases completed: 1→2→3→4→5→6→7→8→9
  Artifacts: {artifact-dir} (9 files)
  
  Feature DONE.
═══════════════════════════════════════════
```

**Hotfix flow:**
```
═══════════════════════════════════════════
  SHIP COMPLETE: {bug-id}
═══════════════════════════════════════════
  Phase: Ship (hotfix final phase)
  
  PR: #{number} — {url}
  Commit: source code + .vsaf/docs/ only
  Excluded: graphify-out/, .gitnexus/
  
  Phases completed: Analyze → RED → GREEN → Review → Ship
  Artifacts: {artifact-dir} (3 files)
  
  Hotfix DONE.
═══════════════════════════════════════════
```

**Both flows:** Update `.vsaf/docs/STATUS.md`:
- Feature flow → move to "Completed Features"
- Hotfix flow → move to "Completed Hotfixes"

## Rules

- DO NOT review code — that is the review phase's job
- Feature flow: only ship code that is APPROVED + knowledge UPDATED (feature-complete done)
- Hotfix flow: only ship code that is APPROVED (no feature-complete step)
- PR description MUST be self-contained (reading the PR alone should be enough to understand the feature without reading artifacts)
- **ABSOLUTELY DO NOT commit `graphify-out/` or `.gitnexus/`** — verify .gitignore first
- **ONLY commit source code + `.vsaf/docs/`**
- Add re-index note to PR description for team members
