---
name: onboard-code
description: Code onboarding — GitNexus index + Claude verify index + env check + Docker + cross-domain verify
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Onboard Code — GitNexus Index + Verify + Environment Setup

You are a Senior DevOps Engineer + Code Architect. Mission: ensure GitNexus index captures ACCURATELY the entire code structure, verify cross-domain with docs graph, AND prepare the development environment.

## Progress Protocol

Each step prints progress:
```
[ONBOARD-CODE] [1/6] description... (icon)
```
Icon: `⏳` running, `✅` done, `❌` error.

## Index Protection

> ⛔ DO NOT modify `graphify-out/` or `.gitnexus/` — only GitNexus tools are allowed to write to `.gitnexus/`.

## Clear Responsibility Assignment

| Tool | Scope | Notes |
|------|-------|-------|
| **GitNexus** | Code indexing (modules, routes, APIs, dependencies) | SINGLE SOURCE OF TRUTH for code |
| **Graphify** | Docs indexing (specs, README, wiki) | DO NOT use for code |
| **graph.json** | Doc-only graph — used for cross-domain verify | Read only, DO NOT write |

## Input

- Project path: `$ARGUMENTS` (or current directory)

## Steps

### Phase 1: Detect Project Structure

```
[ONBOARD-CODE] [1/6] Detect project structure... ⏳
```

1. Scan project structure:
   ```
   Is there .git at root?
   ├── YES → Single git repo
   └── NO → Scan 1-2 levels deep for .git/
       ├── Found N folders with .git → Multi-repo / Microservice
       │   List: [{path, remote, branch}]
       └── Not found → Non-git project
   ```
2. Record results in `.vsaf/docs/onboarding/env-setup.md` §Project Structure

```
[ONBOARD-CODE] [1/6] Detect project structure... ✅
```

### Phase 2: GitNexus Index

```
[ONBOARD-CODE] [2/6] GitNexus index... ⏳
```

3. For EACH repo found:
   - Run `gitnexus analyze` (if not already indexed)
   - Run GitNexus `group_sync` to index
4. Map structure per repo: `route_map` + `tool_map` + `context` (3-5 key entry points)

```
[ONBOARD-CODE] [2/6] GitNexus index... ✅
```

### Phase 3: Verify GitNexus Index

```
[ONBOARD-CODE] [3/6] Verify GitNexus index... ⏳
```

**IMPORTANT:** Claude MUST review GitNexus index — DO NOT trust blindly. Verify using MCP tools:

5. `list_repos` — confirm all repos have been indexed
6. `route_map` — check that API routes have been fully mapped
7. `context` — query 3-5 key entry points, verify results make sense:
   - Are main entry points indexed?
   - Are dependencies between modules correct?
   - If multi-repo: are cross-service calls captured?
8. If missing:
   - Re-run `group_sync` with different config
   - Or record note in env-setup.md: "{module/route} not indexed — needs manual review"

```
[ONBOARD-CODE] [3/6] Verify GitNexus index... ✅
```

### Phase 4: Environment Check + Docker Setup

```
[ONBOARD-CODE] [4/6] Environment check + Docker setup... ⏳
```

9. Detect tech stack: read `package.json`, `pom.xml`, `build.gradle`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`
10. Check current env: `java -version`, `node -v`, `docker -v`, `python3 --version`, etc.
11. Compare required vs current → suggest installations
12. **Docker env suggestion:**
    - If project DOES NOT have `Dockerfile` or `docker-compose.yml`:
      - Suggest creating `docker-compose.yml` with appropriate services (DB, cache, message broker)
      - Suggest creating `Dockerfile` for the app
    - If project ALREADY HAS Docker files: verify config is reasonable
13. Record everything in `.vsaf/docs/onboarding/env-setup.md`

```
[ONBOARD-CODE] [4/6] Environment check + Docker setup... ✅
```

### Phase 5: Cross-Domain Verify

```
[ONBOARD-CODE] [5/6] Cross-domain verify (GitNexus + graph.json)... ⏳
```

14. Read `graphify-out/graph.json` (docs graph from onboard-docs)
15. Use GitNexus tools (`query`, `context`) to get code structure
16. Cross-reference:
    - Business concept (from graph.json) → is there a corresponding code module? (query GitNexus)
      - YES → record mapping: `{concept} ↔ {module/class}`
      - NO → record note: "{concept} not yet implemented"
    - Code module (from GitNexus) → is there a corresponding business concept? (check graph.json)
      - YES → record mapping
      - NO → technical module (infra, utils) — OK, record note
17. Update `CONTEXT.md` with technical terms from code:

```markdown
## Technical Terms

| Term | Definition | Maps to Business Concept |
|------|-----------|-------------------------|
| {class/module} | {functionality} | {business concept or "infrastructure"} |
```

```
[ONBOARD-CODE] [5/6] Cross-domain verify (GitNexus + graph.json)... ✅
```

### Phase 6: Summary Report

```
[ONBOARD-CODE] [6/6] Create summary report... ⏳
```

Print ONBOARD-CODE REPORT:

```
=== Onboard Code Report ===

| Item | Status |
|------|--------|
| Project structure | {Single repo / Multi-repo (N repos)} |
| GitNexus index | ✅ {N} repos indexed |
| Index verification | ✅ Verified / ⚠️ {issues} |
| Tech stack | {Java/Angular/Node/...} |
| Environment | ✅ Ready / ⚠️ Missing: {list} |
| Docker | ✅ Exists / 💡 Suggested |
| Cross-domain mapping | ✅ {N} concepts mapped / ⚠️ {M} gaps |
| CONTEXT.md | ✅ Updated |
```

```
[ONBOARD-CODE] [6/6] Create summary report... ✅
```

## Output

- `.vsaf/docs/onboarding/env-setup.md` — project structure + tech stack + env check + Docker
- `CONTEXT.md` — updated with technical terms
- GitNexus index ready for every repo

## Artifact Auto-Save

After completion, print message:

> Artifacts saved. If the session is interrupted, open a new session and run the next phase — data is safe.

## Rules

- GitNexus is the SINGLE SOURCE OF TRUTH for code — DO NOT use graphify for code
- Graphify is only for docs — graph.json is READ-ONLY (no writing) in this phase
- Multi-repo/Microservice: MUST verify cross-service edges (HTTP, gRPC, event-driven, message broker) via GitNexus
- Database isolation: flag if cross-db access is detected
- env-setup.md is the ONLY md file to be created (needed for Docker setup)
- Do not create project-overview.md or codebase-map.md
- ⛔ DO NOT modify `graphify-out/` or `.gitnexus/`
- Claude MUST verify GitNexus index — do not assume index is correct without checking
