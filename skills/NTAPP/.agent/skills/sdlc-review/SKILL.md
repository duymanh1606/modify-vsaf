---
name: review
description: Phase 7 — Review via Superpowers verification + BMAD code review + SonarQube re-check + GitNexus impact + debate
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 7: Review

You are Tech Lead + QA Lead. Mission: verify code against SRS, adversarial review, impact assessment.

## Progress Protocol

Print progress at each step in this format:
```
[REVIEW] [step/5] description... ⏳
[REVIEW] [step/5] description... ✅
```

## Index Protection

⛔ DO NOT modify `graphify-out/` or `.gitnexus/` in this phase.

## Artifact Auto-save

All artifacts are automatically saved to `.vsaf/docs/features/{feature-name}/` to ensure session continuity. If the session is interrupted, you can resume from the last artifact.

## Phase Entry Protocol

```
[REVIEW] [1/5] Checking prerequisites... ⏳
```

1. Input:
   - `.vsaf/docs/features/{feature-name}/05-srs.md`
   - Code diff on feature branch
2. Check that SRS file exists
3. Check that feature branch exists
4. Read `.vsaf/docs/STATUS.md`
5. Read `CONTEXT.md`
6. Query `graph.json` for impact verification

```
[REVIEW] [1/5] Checking prerequisites... ✅
```

## Tasks

### Step 2: System Verification

```
[REVIEW] [2/5] System verification — build, tests, scope... ⏳
```

Use `/superpowers:verification-before-completion`:
- Build passes
- All tests GREEN
- No uncommitted files
- Scope matches SRS
Write to `08-review.md` §Verification.

```
[REVIEW] [2/5] System verification... ✅
```

### Step 3: Code Review

```
[REVIEW] [3/5] Adversarial code review... ⏳
```

Use `/bmad-code-review` — adversarial code review on the feature branch diff with parallel review layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor).

Ensure the review covers:

1. **Security scan** — SQL injection, XSS, command injection, hardcoded secrets, insecure deserialization
2. **Data integrity** — null dereference, resource leaks, race conditions, missing transactions
3. **SOLID violations** — god classes, leaky abstractions, interface segregation
4. **Naming consistency** — verify against CONTEXT.md terminology
5. **SRS compliance** — every FR/NFR implemented? Any extra scope not in SRS?

Classify each finding: MUST FIX / SHOULD FIX / NOTED.
Write to `08-review.md` §Code Review.

#### Quality Gate Re-check (SonarQube)

**IMPORTANT:** SonarQube rules were already applied in Phase 6 (Implementation). The Review phase only RE-CHECKS — confirming that code still meets standards after all changes.

Verify that code meets SonarQube Quality Gate thresholds:

**Conditions on New Code (new code in the feature):**

| Metric | Threshold |
|--------|-----------|
| Issues | = 0 |
| Security Hotspots Reviewed | = 100% |
| Coverage | ≥ 0% |
| Duplicated Lines | ≤ 45% |
| Maintainability Rating | ≥ A |
| Blocker Issues | = 0 |
| Code Smells | ≤ 20 |
| Critical Issues | = 0 |
| Major Issues | = 0 |
| Vulnerabilities | = 0 |
| Reliability Rating | ≥ A |
| Security Rating | ≥ A |

**Conditions on Overall Code (the entire codebase):**

| Metric | Threshold |
|--------|-----------|
| Blocker Issues | = 0 |
| Bugs | = 0 |
| Code Smells | ≤ 50 |
| Critical Issues | = 0 |
| Duplicated Lines | ≤ 45% |
| Maintainability Rating | ≥ A |
| Major Issues | = 0 |
| Reliability Rating | ≥ A |
| Security Rating | ≥ A |
| Vulnerabilities | = 0 |

**How to execute:**
- If the project has SonarQube → run `sonar-scanner` and check the report
- If there is NO SonarQube → Claude performs a manual re-check against the metrics above:
  - Scan for security vulnerabilities (SQL injection, XSS, command injection, hardcoded secrets)
  - Scan for bugs (null dereference, resource leaks, concurrency issues)
  - Scan for code smells (long methods, deep nesting, duplicated blocks)
  - Verify naming conventions, SOLID principles
  - Check duplicated code blocks
- Write results to `08-review.md` §Quality Gate

**Quality Gate FAIL** → classify each issue as MUST FIX / SHOULD FIX / NOTED per the triage rules below.

```
[REVIEW] [3/5] Adversarial code review + Quality Gate re-check... ✅
```

### Step 4: Impact Assessment

```
[REVIEW] [4/5] Impact assessment via GitNexus... ⏳
```

Use GitNexus `detect_changes` + `impact`:
- Confirm only expected files changed
- Blast radius confidence scoring
Write to `08-review.md` §Impact.

```
[REVIEW] [4/5] Impact assessment... ✅
```

### Step 5: Debate (complex features only)

```
[REVIEW] [5/5] Multi-agent debate (if needed)... ⏳
```

Use `/bmad-party-mode` — multi-agent debate:
- Security vs Performance vs Maintainability
Write to `08-review.md` §Debate.

```
[REVIEW] [5/5] Multi-agent debate... ✅
```

## Gate

MUST FIX = 0, Human approve.

Triage:
- **MUST FIX**: Security, data loss, SRS FR/NFR not satisfied, crash → Blocks ship
- **SHOULD FIX**: Performance, maintainability → Fix if time allows
- **NOTED**: Style, minor naming → Log only

If MUST FIX > 0 → return to Phase 6 (Implementation) with specific issues.

## Output

Write file: `.vsaf/docs/features/{feature-name}/08-review.md`

```markdown
# Review: {feature-name}

## Verification
- Build: PASS/FAIL
- Tests: {X}/{Y} passed
- Uncommitted files: none
- Scope: matches SRS ✓

## Code Review
### MUST FIX
- (none)
### SHOULD FIX
- {issue description}
### NOTED
- {minor items}

## Quality Gate (Re-check)
- SonarQube: {available / manual re-check}
- New Code: {PASS/FAIL} — Issues={N}, Blocker={N}, Critical={N}, Major={N}, Smells={N}, Vulns={N}, Duplication={N}%
- Overall: {PASS/FAIL} — Bugs={N}, Blocker={N}, Critical={N}, Major={N}, Smells={N}, Vulns={N}, Duplication={N}%
- Compile: PASS/FAIL
- Runtime: PASS/FAIL

## Impact
- Files changed: {N}
- Blast radius: {low/medium/high}
- Confidence: {%}

## Debate (if applicable)
{party-mode findings}

## Gate: {PENDING / APPROVED by {name} on {date}}
```

## Phase Exit Protocol

Print PHASE REPORT:
- Results: MUST FIX = {N}, SHOULD FIX = {N}, NOTED = {N}
- Output files: `08-review.md`
- Suggestion: [1] `/sdlc-feature-complete` (if APPROVED) [2] Return to Phase 6 (if MUST FIX > 0)

Update `.vsaf/docs/STATUS.md`.

## Rules

- Review against SRS (spec), NOT against code implementation
- Max 2 review rounds — if still failing → escalate to human
- MUST FIX items MUST be resolved before feature-complete
- **Quality Gate FAIL = MUST FIX** — Blocker, Critical, Vulnerability all block ship
- **Code does not compile = MUST FIX** — hard gate, no exceptions
- If there is no SonarQube, Claude performs a manual quality gate re-check
- **SonarQube only RE-CHECKS** — rules were applied in Phase 6, review only confirms compliance
