---
name: sdlc-health
description: SDLC health check — verify all skills, plugins, MCP tools, deps, and binaries are installed and working
version: 1.1.0
author: "@ngocsangairvds/vsaf"
---

# SDLC Health Check

Run a comprehensive diagnostic of the SDLC toolchain. Check all 8 categories and print a summary table.

## Procedure

Execute ALL checks below in order, then print the summary table.

### Check 1: SDLC Skills (filesystem)

Use the Read tool to check each of these 17 skill files (sdlc-health is excluded — if you're running this, it's installed). If the file exists, mark ✓. If Read returns an error, mark ✗.

```
.claude/skills/sdlc-init/SKILL.md
.claude/skills/sdlc-onboard-docs/SKILL.md
.claude/skills/sdlc-onboard-code/SKILL.md
.claude/skills/sdlc-discovery/SKILL.md
.claude/skills/sdlc-prd/SKILL.md
.claude/skills/sdlc-architecture/SKILL.md
.claude/skills/sdlc-srs/SKILL.md
.claude/skills/sdlc-test-design/SKILL.md
.claude/skills/sdlc-implement/SKILL.md
.claude/skills/sdlc-review/SKILL.md
.claude/skills/sdlc-feature-complete/SKILL.md
.claude/skills/sdlc-ship/SKILL.md
.claude/skills/sdlc-hotfix-analyze/SKILL.md
.claude/skills/sdlc-hotfix-prd/SKILL.md
.claude/skills/sdlc-hotfix-implement/SKILL.md
.claude/skills/sdlc-hotfix-ship/SKILL.md
.claude/skills/sdlc-hotfix-review/SKILL.md
```

### Check 2: BMAD Skills (filesystem)

Check these 17 BMAD skills — required by discovery, prd, architecture, srs, test-design, review:

```
.claude/skills/bmad-advanced-elicitation/SKILL.md
.claude/skills/bmad-brainstorming/SKILL.md
.claude/skills/bmad-domain-research/SKILL.md
.claude/skills/bmad-prfaq/SKILL.md
.claude/skills/bmad-create-prd/SKILL.md
.claude/skills/bmad-validate-prd/SKILL.md
.claude/skills/bmad-review-adversarial-general/SKILL.md
.claude/skills/bmad-create-architecture/SKILL.md
.claude/skills/bmad-create-epics-and-stories/SKILL.md
.claude/skills/bmad-check-implementation-readiness/SKILL.md
.claude/skills/bmad-agent-analyst/SKILL.md
.claude/skills/bmad-review-edge-case-hunter/SKILL.md
.claude/skills/bmad-code-review/SKILL.md
.claude/skills/bmad-party-mode/SKILL.md
.claude/skills/bmad-qa-generate-e2e-tests/SKILL.md
.claude/skills/bmad-checkpoint-preview/SKILL.md
.claude/skills/bmad-correct-course/SKILL.md
```

### Check 3: mattpocock Skills (filesystem)

Check these 5 skills — lean alternative for bugfix/known-domain flows:

```
.claude/skills/grill-me/SKILL.md
.claude/skills/diagnose/SKILL.md
.claude/skills/zoom-out/SKILL.md
.claude/skills/tdd/SKILL.md
.claude/skills/improve-codebase-architecture/SKILL.md
```

### Check 4: Plugins (Claude-only)

Check if these plugins are available by looking at the available skills list in the current session:

- **superpowers** — look for any skill starting with `superpowers:` in available skills. If found → ✓, else → ✗ MISSING
  - Fix: `/install-plugin superpowers`
  - Required by: implement, review, ship, hotfix-analyze

### Check 5: MCP tools (Claude-only)

Test MCP server connectivity by calling these tools:

- **VSAF MCP** — call `vsaf_status` with `runId: "health-check"`. If the tool exists (even with "run not found" error), the server is connected → ✓. If "unknown tool" → ⚠ NOT CONNECTED (optional — only required for coroutine engine).
  - Fix: check `.mcp.json` has vsaf entry, restart Claude

- **GitNexus MCP** — call `mcp__gitnexus__list_repos`. If the tool exists → ✓. If "unknown tool" → ✗ NOT CONNECTED.
  - Fix: run `vsaf install sdlc` then restart Claude

### Check 6: npm deps (Bash)

Run this command via Bash tool:

```bash
ls node_modules/gitnexus/package.json 2>/dev/null && echo "OK" || echo "MISSING"
```

### Check 7: Binaries (Bash)

Run via Bash tool:

```bash
gh --version 2>/dev/null | head -1 || echo "MISSING"
graphify --help 2>/dev/null | head -1 || echo "MISSING"
docker --version 2>/dev/null | head -1 || echo "MISSING"
sonar-scanner --version 2>/dev/null | head -1 || echo "MISSING"
```

- `gh` and `graphify` are **required**. `docker` and `sonar-scanner` are **optional**.
- If `graphify` is missing: `pipx install graphifyy && graphify install --platform claude`

### Check 8: VSAF project (filesystem)

Check via Bash tool:

```bash
ls -d .vsaf/ 2>/dev/null && echo "OK" || echo "MISSING"
ls .vsaf/config.yaml 2>/dev/null && echo "OK" || echo "MISSING"
ls .vsaf/workflows/*.yaml 2>/dev/null | wc -l
ls -d .vsaf/docs/ 2>/dev/null && echo "OK" || echo "MISSING"
```

Read `.mcp.json` in the current project directory. Check:
- `mcpServers.gitnexus` exists → ✓
- `mcpServers.vsaf` exists → ✓
- File not found → ✗ Run `vsaf init`

## Output

After completing all checks, print this summary:

```markdown
## SDLC Health Check

| Category             | Status | Details                                 |
|----------------------|--------|-----------------------------------------|
| SDLC Skills (17)     |   {s}  | {deployed}/{17} deployed                |
| BMAD Skills (17)     |   {s}  | {deployed}/{17} deployed                |
| mattpocock Skills (5)|   {s}  | {deployed}/{5} deployed                 |
| Plugins              |   {s}  | superpowers {s}                         |
| MCP tools            |   {s}  | vsaf {s}, gitnexus {s}               |
| npm deps             |   {s}  | gitnexus {s}                            |
| Binaries             |   {s}  | gh {s}, graphify {s}, docker {s}, sonar {s} |
| VSAF project      |   {s}  | .vsaf/ {status}, .mcp.json {status}  |

### Issues
{list any ✗ items with fix instructions}

### Optional missing
{list any ⚠ items}

### Missing skills
{list specific missing skills, or "(none)"}
```

Replace `{s}` with: ✓ (pass), ✗ (required missing), ⚠ (optional missing).

**Severity rules:**
- ✓ = pass
- ✗ = required missing → must fix before using SDLC
- ⚠ = optional missing → SDLC works but some features unavailable

**Required:** all 17 SDLC skills, all 17 BMAD skills, all 5 mattpocock skills, superpowers plugin, gh binary, graphify binary + skill, gitnexus MCP, .mcp.json entries
**Optional:** docker, sonar-scanner, vsaf MCP (only for coroutine engine)
