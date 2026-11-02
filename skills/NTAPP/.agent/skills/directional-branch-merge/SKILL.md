---
name: directional-branch-merge
description: Use when merging one git branch into another (feature→staging, feature→release, feature→master, branch→branch) where code must flow ONE direction only — the target branch must never leak back into the source branch, merge conflicts must be resolved without breaking either branch's business logic, and the merged result must still build. Triggers on "merge A into B", "merge feature into staging/master", "promote branch".
---

# Directional Branch Merge

## Overview

Merge source branch **A** into target branch **B** so A's work lands on B, while **B's content never contaminates A**. Conflicts are resolved on B, preserving the business intent of BOTH branches. After merging, verify B still builds. **Nothing is pushed** — stop for human review.

**Core principle: data flows A → B, never B → A.**
The ONE exception: when B is the repo's trunk (`master`/`main`), you MAY pull trunk down into A to resolve — because trunk is the shared baseline everyone syncs from.

## When to Use

- Merge feature → staging / release / develop / another feature.
- Merge feature → master / main.
- Any "promote / bring branch A onto branch B" request.

**Inputs:** source `A` and target `B` (ask if not given). Operate on the current git repo (`cwd` root). One repo per run — for multi-repo, run once per repo.

## The Direction Rule (most important — do not violate)

Determine the trunk first: `git symbolic-ref --short refs/remotes/origin/HEAD` (fallback: `master` or `main`).

| Situation | Allowed | Forbidden |
|---|---|---|
| **B is NOT trunk** | `git switch B` then `git merge A`. Resolve conflicts on B. | Anything that adds B's commits/content to A: `git merge B` / `git rebase B` / `git merge origin/B` while on A. Resolving by "merge B into A first, then A into B". |
| **B IS trunk** (master/main) | All of the above, PLUS you MAY `git switch A; git merge <trunk>` (or rebase A onto trunk) first to resolve, then merge A→B. | — |

**Violating the letter of this rule is violating the spirit.** "It was faster to merge staging into feature to fix the conflict" is exactly the forbidden move when B is not trunk.

## Workflow

1. **Confirm inputs & repo.** Know A, B, the repo root, and which is trunk. Verify both branches exist (local or `origin/`).
2. **Clean tree.** `git status` — if the working tree is dirty, **STOP** and ask the user to commit or stash. Never merge over uncommitted work.
3. **Fetch latest.** `git fetch --all --prune`.
4. **Sync A to latest.** `git switch A`. If behind `origin/A` and fast-forwardable → `git pull --ff-only`. If **diverged** from `origin/A` → **STOP**, ask the user (do not auto-reconcile). Local-ahead of origin is fine.
5. **Sync B to latest.** Same procedure for B against `origin/B`.
6. **Record undo point.** Save B's pre-merge SHA: `git rev-parse B`. To undo later: `git merge --abort` (mid-conflict) or `git reset --hard <sha>` (after commit).
7. **Merge.** `git switch B` then `git merge --no-ff A`. Clean → go to step 9. Conflicts → step 8.
8. **Resolve conflicts** (see below).
9. **Build check** (see below).
10. **Report & stop.** Summarize what merged, conflicts + how resolved, build result. **Do not push.** Remind the user to review, then push manually; give the undo command from step 6.

## Conflict Resolution

- List conflicts with `git status`. For each file, read BOTH sides (`ours` = B, `theirs` = A) and use `git log`/`git diff` to understand **why** each side changed.
- Resolve to keep the **business behavior of BOTH branches**. Do not blind-pick a side.
- **When the correct merge is unclear** — you cannot tell whether combining the two sides breaks logic on either branch — **STOP and ask the user**, showing the file, both versions, and exactly what you're unsure about. Do not guess.
- Never resolve by merging B into A (unless B is trunk — see Direction Rule).
- Avoid `git checkout --ours/--theirs <file>` on a whole file unless you have read it and are certain that side is fully correct.
- After resolving all: `git add <files>`, then `git merge --continue`.

## Build Check

Detect the build tool at the repo root, then run it:

| Marker | Build command |
|---|---|
| `pom.xml` | `mvn -q clean install -DskipTests` (fast alt: `mvn -q clean compile`) |
| `package.json` + `angular.json` | `npm ci` if `node_modules` missing/stale, then `npm run build` (or `ng build`) |
| `package.json` (other) | `npm ci` then `npm run build` |
| `build.gradle` | `./gradlew build -x test` |
| none / ambiguous | **Ask the user** for the build command |

If the build **fails**: report the errors, keep the merge local, help diagnose (broken merge is a likely cause — re-inspect resolved files). **Do not push.**

## Red Flags — STOP

- About to run `git merge B` / `git rebase B` / `git merge origin/B` while on A, and **B is not trunk**.
- "I'll merge the target into the source first, it's easier" (B not trunk).
- `git checkout --theirs/--ours` on a whole file without reading it.
- Proceeding through a conflict when unsure of the business impact.
- Working tree was dirty and you merged anyway.
- Build passed → tempted to push. **This skill stops before push.**

## Common Mistakes

| Mistake | Fix |
|---|---|
| Merging without fetching first | Always `git fetch --all` and sync both branches to latest before merging. |
| Auto-resolving a diverged source branch | Diverged local vs origin → STOP and ask; never silently pick a side. |
| Resolving conflicts by contaminating A | Resolve on B only. B→A is forbidden unless B is trunk. |
| Skipping build check | A clean merge can still break the build (semantic conflicts). Always build. |
| Pushing after build passes | Not this skill's job. Stop and hand back to the user. |
