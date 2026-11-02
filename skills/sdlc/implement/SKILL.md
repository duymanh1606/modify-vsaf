---
name: implement
description: Phase 6 — TDD Implementation via subagent-driven development + SonarQube-during-code + GitNexus impact verification
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Phase 6: Implementation (TDD + Subagent-Driven + SonarQube-In-Loop)

You are a Senior Software Engineer. Your mission: implement code following TDD — RED → GREEN → REFACTOR. Do not write code without a failing test first.

**TWO important changes compared to the old process:**
1. **MANDATORY use of subagent-driven development** — dispatch parallel subagents for stories/epics
2. **Apply SonarQube rules DURING coding** — do not wait for review phase to check

## Index Protection

⛔ **DO NOT modify** `graphify-out/` or `.gitnexus/` — READ only, never WRITE.

## Phase Entry Protocol

```
[IMPLEMENT] [1/8] Checking input artifacts... ⏳
```

1. Input:
   - `.vsaf/docs/features/{feature-name}/06-testcases.md`
   - `.vsaf/docs/features/{feature-name}/03-adr.md`
   - `.vsaf/docs/features/{feature-name}/04-epics.md`
2. Verify ALL 3 files exist:
   - Any file missing → Ask: "File not found. Have you pulled it yet?"
3. Read `.vsaf/docs/STATUS.md`
4. Read `CONTEXT.md`
5. Query `graph.json` for code structure

```
[IMPLEMENT] [1/8] Checking input artifacts... ✅
```

**Note:** This phase MUST run via `/superpowers:subagent-driven-development` — dispatch parallel subagents for each epic according to the Conflict Map in `04-epics.md`.

## Subagent-Driven Development Protocol

```
[IMPLEMENT] [2/8] Initializing subagent-driven development... ⏳
```

**MANDATORY** — Check and activate `/superpowers:subagent-driven-development`:
1. If not already in subagent mode → **switch immediately**
2. Analyze `04-epics.md` → identify Conflict Map
3. Dispatch each epic/story as a separate subagent running in parallel
4. Each subagent follows the Conflict Map — only modify files assigned to its epic

```
[IMPLEMENT] [2/8] Initializing subagent-driven development... ✅
```

## SonarQube Quality Gate — Apply DURING Coding

⚠️ **DO NOT wait for review phase.** Each subagent MUST self-check these thresholds WHILE writing code:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Issues | = 0 | Do not create new issues |
| Blocker Issues | = 0 | STOP immediately if detected |
| Critical Issues | = 0 | STOP immediately if detected |
| Major Issues | = 0 | Fix before continuing |
| Vulnerabilities | = 0 | Scan security for each function |
| Security Rating | ≥ A | No hardcoded secrets, no injection |
| Duplicated Lines | ≤ 45% | Extract common code immediately |
| Maintainability Rating | ≥ A | SOLID, clean code, short methods |
| Reliability Rating | ≥ A | Null-safe, resource management, error handling |

**How to apply during coding:**
- **After each function is written** → self-review: security vulnerabilities? code smells? duplication?
- **After each class is written** → check SOLID violations, naming conventions, interface segregation
- **Before each commit** → scan all changed files for: SQL injection, XSS, command injection, hardcoded secrets, null dereference, resource leaks, concurrency issues, duplicated blocks
- If the project has SonarQube → run `sonar-scanner` incremental
- If the project does NOT have SonarQube → Claude self-reviews against the metrics above

**Goal:** Review phase should only need to RE-CHECK, not find bugs for the first time.

## Tasks

### Step 3: Task Planning

```
[IMPLEMENT] [3/8] Task planning from testcases + ADR... ⏳
```

Use `/superpowers:writing-plans` — create granular task plan from testcases + ADR.
Each task maps to ≥1 FR/NFR.
Write to `07-impl-plan.md`.

```
[IMPLEMENT] [3/8] Task planning from testcases + ADR... ✅
```

### Step 3.5: Checkpoint Review (every 3-5 tasks)

```
[IMPLEMENT] [3.5/8] Checkpoint review... ⏳
```

After every 3-5 completed tasks: invoke `/bmad-checkpoint-preview` (human-in-the-loop walkthrough).

Purpose: pause and let the user review progress before continuing.

The checkpoint will:
- Summarize: what was done, which files changed, current tests status
- Highlight: points of concern, potential issues
- Ask user: continue / adjust / stop?

**Skip checkpoint if** the total plan has fewer than 5 tasks — checkpoint only at the end in that case.

```
[IMPLEMENT] [3.5/8] Checkpoint review... ✅
```

### Step 4: TDD Cycle (per subagent)

```
[IMPLEMENT] [4/8] TDD cycle — RED → GREEN → REFACTOR... ⏳
```

Use `/superpowers:test-driven-development`:

For each test case in `06-testcases.md`:
1. **RED**: Write test → run → MUST FAIL
2. **GREEN**: Write minimal code → run → MUST PASS
   - ⚠️ **While writing GREEN code** → apply SonarQube rules immediately:
     - Do not create security vulnerabilities
     - No code smells (long method, deep nesting)
     - No duplicated code
     - Null-safe, proper error handling
3. **REFACTOR**: Clean code, do not change behavior
   - Refactor MUST improve SonarQube metrics, not degrade them

Use `/superpowers:executing-plans` — execute plan in order.

```
[IMPLEMENT] [4/8] TDD cycle — RED → GREEN → REFACTOR... ✅
```

### Step 5: Debug (if needed)

```
[IMPLEMENT] [5/8] Debug (if there are test failures)... ⏳
```

Use `/superpowers:systematic-debugging` — when a test does not turn GREEN:
- Hypothesis → Experiment → Conclusion
- If it fails 3 times → STOP, escalate

**Scope-drift detection:**

If during implementation you detect the feature requires CHANGES NOT IN THE SRS:
1. Invoke `/bmad-correct-course` — assess impact + propose adjustments
2. If requirements have genuinely changed:
   - STOP implementation
   - Update SRS first via `/sdlc-srs` EDIT mode
   - Re-run `/sdlc-test-design` to generate new test cases
   - Restart Phase 6 from Step 3
3. If only minor adjustments needed: document the adjustment in `07-impl-plan.md` §Scope Adjustments and continue
4. If unclear whether scope changed: STOP and present to user — let them decide

```
[IMPLEMENT] [5/8] Debug (if there are test failures)... ✅
```

### Step 6: Impact Verification

```
[IMPLEMENT] [6/8] Impact verification via GitNexus... ⏳
```

Use GitNexus `impact` — verify no other code is broken.
Use GitNexus `rename` — safe multi-file refactoring if needed.

```
[IMPLEMENT] [6/8] Impact verification via GitNexus... ✅
```

### Step 7: Build & Run Verification

```
[IMPLEMENT] [7/8] Build & run verification... ⏳
```

**MANDATORY** — code MUST compile and run successfully before exiting the phase.

1. **Compile check**: Build the entire project → MUST have 0 errors
   - Java: `mvn compile` or `gradle build`
   - Node: `npm run build` / `tsc --noEmit`
   - Angular: `ng build`
   - Go: `go build ./...`
   - If FAIL → fix immediately, DO NOT skip

2. **Run verification**: Start application → MUST start successfully
   - If the project has `docker-compose.yml` → `docker compose up`
   - If not → use native run command
   - Check health endpoint / startup log OK

3. **Environment check**:
   - Detect required runtime (JDK, Node, Python, Go, etc.)
   - If runtime missing → ⚠️ **WARNING**: "Missing {runtime}. Cannot verify build."
   - **Recommend Docker**: "Recommend using Docker to ensure a consistent environment. Create a Dockerfile if one does not exist."
   - If Docker available → prefer building in container

4. **Test suite run**: `npm test` / `mvn test` / equivalent → All tests PASS

5. **Final SonarQube sweep**: Scan all new code one last time before exiting
   - Confirm: Issues=0, Blocker=0, Critical=0, Major=0, Vulns=0
   - If FAIL → fix immediately, this is a hard gate

⚠️ **DO NOT exit the phase if code does not compile.** This is a hard gate — no exceptions.

```
[IMPLEMENT] [7/8] Build & run verification... ✅
```

## Multi-machine Branching

```
Single repo:
  main → feat/{feature} → feat/{feature}/epic-1 (Subagent A)
                         → feat/{feature}/epic-2 (Subagent B)

Multi-repo:
  Subagent A: cd user-service && git checkout -b feat/{feature}
  Subagent B: cd payment-service && git checkout -b feat/{feature}
```

## Output

- `.vsaf/docs/features/{feature-name}/07-impl-plan.md` — task plan + TDD log
- Code changes on feature branch
- All tests GREEN
- SonarQube metrics PASS (verified during coding)

## Phase Exit Protocol

In PHASE REPORT:
- Done: N tasks completed, M tests written, K subagents dispatched
- Result: all tests PASS/FAIL
- SonarQube: Issues=0, Blocker=0, Critical=0, Major=0, Vulns=0, Duplication={N}%
- Output files: `07-impl-plan.md`
- Code changes: {list files changed}
- Suggestions: [1] Phase 7 Review (`/sdlc-review`) [2] Save artifacts

Update `.vsaf/docs/STATUS.md`.

**Notify the user:**
> Artifacts have been saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- DO NOT write code without a failing test first (#2 TDD)
- **MANDATORY** use `/superpowers:subagent-driven-development` — do not run sequential
- **SonarQube rules apply DURING coding** — do not wait for review
- Follow the Conflict Map — only modify files assigned to your epic
- 3-strike rule: task fails 3 times → STOP, escalate
- Impact analysis MUST run before each commit
- Smart Zone: clear context every 5 tasks (#4)
- **Code MUST compile successfully** — hard gate, no exceptions
- **Recommend Docker** if runtime is missing or containerization is not set up
- ⛔ DO NOT modify `graphify-out/` or `.gitnexus/`
