# VSAF

DAG-based workflow engine for AI coding agents. Define multi-step workflows in YAML, execute them with AI providers, and monitor runs in realtime through a web dashboard.

## What It Does

VSAF orchestrates complex AI workflows as directed acyclic graphs (DAGs). Each node in a DAG can be a prompt (sent to an AI provider), a bash command, or a reusable command template. Nodes declare dependencies, conditional execution rules, and context isolation — VSAF handles the rest.

```
vsaf run fix-issue --args "fix #42"
```

```
extract-issue-number ✓  1.2s
fetch-issue          ✓  0.8s
classify             ✓  2.1s
investigate          ●  running...
plan                 ⊘  skipped
bridge-artifacts     ○  pending
implement            ○  pending
validate             ○  pending
```

## Features

- **YAML workflow definitions** — declarative DAGs with prompt, bash, and command node types
- **Dependency-based execution** — wave-based parallel scheduling, conditional branching, trigger rules
- **Variable resolution** — reference outputs from upstream nodes (`$classify.output.issue_type`)
- **Workspace isolation** — each run executes in an ephemeral temp directory, changes applied on success
- **Run persistence** — run state saved to JSON after each node, supports resume on failure
- **Provider-agnostic** — pluggable AI provider adapters (Claude Code adapter included)
- **Web dashboard** — Angular SPA with workflow management and realtime SSE monitoring
- **REST API** — Fastify server for programmatic access to workflows and runs
- **MCP server** — Model Context Protocol integration for Claude Code
- **Skill pack system** — 40 bundled skills (18 SDLC + 17 BMAD + 5 mattpocock lean)
- **AJV validation** — JSON Schema validation for workflow definitions
- **Cycle detection** — DAG cycle detection prevents infinite loops
- **Error recovery** — configurable retry backoff strategies for failed nodes

---

## Installation

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Node.js | >= 20.0.0 | `node -v` |
| npm | >= 9.0.0 | `npm -v` |
| git | any | `git --version` |
| Claude Code CLI | latest | `claude --version` |
| GitHub CLI (optional) | any | `gh --version` |

**Claude Code CLI** is required for prompt and command nodes. **GitHub CLI** is required only for workflows that interact with GitHub (e.g., `fix-issue` uses `gh issue view`).

### Option 1: Global Install (Recommended)

```bash
npm install -g @ngocsangairvds/vsaf
vsaf --version
```

### Option 2: Project-Local Install

```bash
npm install -D @ngocsangairvds/vsaf
npx vsaf --version
```

### Option 3: Install from Source

```bash
git clone https://github.com/YOUR_USERNAME/vsaf.git
cd vsaf
npm install && npm run build
npm link
vsaf --version
```

---

## Quick Start

```bash
# Initialize in your project (directories only — no flow yet)
cd /path/to/your/project
vsaf init

# Install a flow: its skills, workflows and slash commands
vsaf install sdlc

# Check environment
vsaf doctor

# List available workflows
vsaf list

# Run a workflow
vsaf run fix-issue --args "fix #42"

# Start the web dashboard
vsaf serve --port 3000 --open
```

`vsaf init` creates the `.vsaf/` directory — and nothing else. Workflows, commands
and skills arrive with `vsaf install <flow>`, which is the command that knows which
flow you asked for:

```
.vsaf/
├── config.yaml          ← Project configuration
├── docs/                ← Artifact tree the phases read and write
├── workflows/           ← Empty. Filled by `vsaf install <flow>`
├── commands/            ← Empty. Filled by `vsaf install <flow>`
└── storage/             ← Run state persistence (add to .gitignore)
```

---

## CLI Commands

| Command | Description |
|---|---|
| `vsaf init` | Initialize the `.vsaf/` directory and project config — installs no flow |
| `vsaf run <workflow>` | Execute a workflow by name |
| `vsaf run <workflow> --resume <runId>` | Resume an interrupted run |
| `vsaf list` | List available workflows |
| `vsaf status` | Show recent run statuses |
| `vsaf doctor` | Check environment and dependencies |
| `vsaf serve` | Start API server and web dashboard |
| `vsaf mcp` | Start MCP server for Claude Code integration |
| `vsaf install <pack>` | Install a skill pack globally (e.g. `vsaf install sdlc`) |
| `vsaf skill` | Manage skills: `add`, `list`, `info`, `remove`, `init` |

### `vsaf serve`

```bash
vsaf serve [--port 3000] [--open]
```

Starts a Fastify server exposing a REST API and the Angular dashboard.

### `vsaf mcp`

Starts a Model Context Protocol (MCP) server that exposes VSAF workflows and skills to Claude Code. Configure in `.mcp.json` for automatic integration.

### `vsaf install`

```bash
vsaf install sdlc    # Deploy 39 skills to .claude/skills/
vsaf install NTAPP   # Deploy the NTAPP delivery pack (55 skills, 11 workflows)
```

NTAPP has its own setup guide: [docs/install-NTAPP.md](docs/install-NTAPP.md).

### `vsaf skill`

```bash
vsaf skill list              # List installed skills
vsaf skill info <name>       # Show skill details
vsaf skill add <path>        # Add a skill from file
vsaf skill remove <name>     # Remove a skill
vsaf skill init              # Scaffold a new skill template
```

---

## Writing Workflows

### Basic Workflow

Create `.vsaf/workflows/my-workflow.yaml`:

```yaml
name: my-workflow
description: A custom workflow

provider: claude
model: sonnet

nodes:
  - id: step1
    prompt: |
      Analyze this request: $ARGUMENTS
      Output a summary.

  - id: step2
    bash: |
      echo "Step 1 output was: $step1.output"
    depends_on: [step1]

  - id: step3
    prompt: |
      Based on: $step2.output
      Generate a final report.
    depends_on: [step2]
```

Run it:

```bash
vsaf run my-workflow --args "analyze the auth module"
```

### Node Types

| Type | Field | Description |
|---|---|---|
| **prompt** | `prompt:` | Send text to the AI provider |
| **bash** | `bash:` | Run a shell command |
| **command** | `command:` | Execute a reusable command template from `.vsaf/commands/` |

### Node Fields

| Field | Required | Description |
|---|---|---|
| `id` | yes | Unique node identifier |
| `description` | no | Human-readable note; documentation only |
| `prompt` / `bash` / `command` | yes | Node content (exactly one) |
| `depends_on` | no | List of node IDs that must complete first |
| `when` | no | Condition expression — node skipped if false |
| `trigger_rule` | no | `all_success` (default) or `one_success` |
| `context` | no | `fresh` (new AI session) or `inherit` (default) |
| `model` | no | Override the workflow-level model |
| `allowed_tools` | no | Restrict AI tool access (empty array = no tools) |
| `output_format` | no | JSON Schema for structured output |
| `ledger` | no | Path to a read-only file whose tail is prepended to the prompt |
| `fanout` | no | Run this node once per file matched by a glob |

### Variables

| Pattern | Description | Example |
|---|---|---|
| `$ARGUMENTS` | Args passed to `vsaf run --args` | `"fix #42"` |
| `$node-id.output` | Text output of a completed node | `"bug"` |
| `$node-id.output.field` | Field from structured output | `"enhancement"` |
| `$ARTIFACTS_DIR` | Shared directory for file passing | `/tmp/vsaf-run-abc/artifacts` |
| `${ITEM}` / `${<as>}` | Current item inside a `fanout` node | `units/a.md` |

> **In a `bash` node every variable is already shell-quoted.** Writing `"${UNIT}"` puts a
> literal quote inside the value — write `${UNIT}` bare. The one exception is
> `$CONFIG.<key>`, which is left unquoted because it holds a command to run, not data.

### Fanout — one node, many items

`fanout` expands a single node into one sub-task per file matched by `over`. Each sub-task
sees its own item as `${ITEM}` and under the name chosen by `as`.

```yaml
nodes:
  - id: build-each-unit
    fanout:
      over: "work/units/*"     # glob, relative to the node's cwd
      as: UNIT                 # ${UNIT} inside this node
      max_concurrency: 5       # omit to run them all at once
    prompt: |
      Implement the unit described in ${UNIT}.
```

The parent node completes once every sub-task has finished, and fails if any of them did.
A glob matching nothing is not an error — the node simply completes with no work.

### Ledger — carrying lessons between iterations

`ledger` points at a file the engine **reads** before each run of the node, prepending its
last 16 KB to the prompt. It is how a later iteration learns what an earlier one found.

```yaml
  - id: implement
    ledger: out/ledgers/slice-ledger.md
    prompt: Implement the next slice.
```

The engine never writes this file — another node in the workflow appends to it. A missing
or empty file is fine and adds nothing to the prompt.

### Conditional Branching

```yaml
nodes:
  - id: classify
    prompt: |
      Classify this as 'bug' or 'feature': $ARGUMENTS
    output_format:
      type: object
      properties:
        type:
          type: string
          enum: [bug, feature]
      required: [type]

  - id: fix-bug
    prompt: Fix this bug: $ARGUMENTS
    depends_on: [classify]
    when: "$classify.output.type == 'bug'"

  - id: build-feature
    prompt: Implement this feature: $ARGUMENTS
    depends_on: [classify]
    when: "$classify.output.type == 'feature'"

  - id: finalize
    prompt: Wrap up the work.
    depends_on: [fix-bug, build-feature]
    trigger_rule: one_success  # Only need one branch to succeed
```

### Using Commands (Reusable Prompts)

Create `.vsaf/commands/my-command.md`:

```markdown
---
description: A reusable prompt template
argument-hint: The task description
---

You are an expert engineer. Your task:

$ARGUMENTS

Previous analysis: $classify.output

Write your implementation to the codebase. Save notes to $ARTIFACTS_DIR/notes.md.
```

Reference it in a workflow:

```yaml
  - id: implement
    command: my-command
    depends_on: [classify]
    context: fresh    # Start a new AI session
    model: opus       # Use a stronger model
```

### Structured Output

Force JSON output from AI nodes:

```yaml
  - id: analyze
    prompt: Analyze this code and rate its quality.
    output_format:
      type: object
      properties:
        score:
          type: string
          enum: ["A", "B", "C", "D", "F"]
        issues:
          type: string
      required: [score, issues]

  - id: report
    prompt: |
      The code scored: $analyze.output.score
      Issues: $analyze.output.issues
    depends_on: [analyze]
```

### Passing Files Between Nodes

Nodes can share files via `$ARTIFACTS_DIR`:

```yaml
nodes:
  - id: investigate
    prompt: |
      Investigate the issue. Write findings to $ARTIFACTS_DIR/investigation.md

  - id: plan
    bash: cat $ARTIFACTS_DIR/investigation.md
    depends_on: [investigate]

  - id: implement
    prompt: |
      Here is the investigation: $plan.output
      Now implement the fix.
    depends_on: [plan]
```

### Resume Failed Runs

If a workflow fails mid-execution, resume from where it left off:

```bash
vsaf status                                     # Find the run ID
vsaf run fix-issue --resume run-a1b2c3d4e5f6    # Skip completed nodes
```

**MCP mode:** run state lives in the engine process, so an engine restart (machine reboot, resumed Claude Code session via `claude -r`) loses in-flight runs. `vsaf_next` rehydrates them: pass `projectPath` along with the usual `runId`/`results` and the engine rebuilds the run from `.vsaf/storage/<runId>/state.json` — completed nodes are never re-executed, the reattached workspace keeps its changes, and telemetry starts a fresh trace marked `vsaf.run.resumed: true`, linked to the pre-restart trace by `vsaf.run.id`.

---

## SDLC Skill Pack

VSAF ships with a complete SDLC skill pack — 40 skills organized into workflows for building features and fixing bugs with TDD discipline.

> **Upgrading from an older version?** The `sdlc` pack's E2E track was slimmed down to 9 core skills (mobile/CI/test-planning moved to the standalone `autotest-skill` pack). See [MIGRATION.md](./MIGRATION.md) for what changed and how to clean up orphaned skills left behind by `vsaf init --force`.

### Setup

```bash
# 1. Initialize VSAF in your project (directories and config)
cd /path/to/your/project
vsaf init

# 2. Install the flow: its skills, workflows and slash commands
vsaf install sdlc

# 3. Inside Claude Code — bootstrap SDLC documentation layer
/sdlc-init

# 4. Onboard project knowledge
/sdlc-onboard-docs    # Build docs knowledge graph (graphify)
/sdlc-onboard-code    # Index code (GitNexus) + environment check
```

> **Steps 1 and 2 are both required, for every flow, and in this order.** `vsaf
> init` writes `.vsaf/config.yaml`, the SessionStart hook and `.mcp.json`; `vsaf
> install <flow>` deploys the flow's skills, workflows and slash commands, and
> tops the config's telemetry section up with the paths that flow writes its
> deliverables to. Skip step 1 and the install has nowhere to put the workflows
> and says so; skip step 2 and the project has a config but no flow.
>
> **Installing a flow other than `sdlc`?** Name it in step 2 — `vsaf install
> NTAPP`. `vsaf init` takes no flow name at all; the old `--pack` flag now stops
> with a line saying which command to use instead. On a project that already has
> a `config.yaml`, `vsaf init --force` *appends* a missing telemetry section
> instead of leaving the file alone; existing content is never rewritten, and an
> unparseable file is skipped with a warning.

After setup, the project should have:

```
your-project/
├── .vsaf/              ← Engine config, skills, workflows, storage
│   └── docs/              ← STATUS.md, KNOWLEDGE.md, features/
├── .mcp.json              ← VSAF + GitNexus MCP servers
├── CONTEXT.md             ← Shared domain language
├── .gitnexus/             ← Code index
└── graphify-out/          ← Docs knowledge graph
```

### Workflows

#### Full Pipelines

| Workflow | Command | Description |
|---|---|---|
| `master-sdlc` | `/vsaf master-sdlc --args "feature description"` | Full 9-phase feature pipeline |
| `hotfix` | `/vsaf hotfix --args "path/to/bug-report.md"` | TDD-driven hotfix from bug report |
| `onboarding` | `/vsaf onboarding` | Docs + code knowledge indexing |

#### Sub-workflows (crash-safe, run independently)

| Workflow | Command | Phases |
|---|---|---|
| `sdlc-thinking` | `/vsaf sdlc-thinking` | Discovery → PRD |
| `sdlc-design` | `/vsaf sdlc-design` | Architecture → SRS |
| `sdlc-testcase` | `/vsaf sdlc-testcase` | Test Design |
| `sdlc-build` | `/vsaf sdlc-build` | Implement → Test Gate (loop 3x) |
| `sdlc-qa` | `/vsaf sdlc-qa` | Review → Feature Complete → Ship |
| `hotfix-tdd` | `/vsaf hotfix-tdd` | TDD RED → GREEN → Test Gate (loop 3x) |

### Master-SDLC Flow (New Feature)

9 phases, each produces artifacts on disk for session continuity:

```
/vsaf master-sdlc --args "Add OAuth2 authentication to REST API"
```

| Phase | Skill | Output | Description |
|---|---|---|---|
| 1 | `discovery` | `01-discovery.md` | Scan system → grill user with questions → brainstorm |
| 2 | `prd` | `02-prd.md` | PRD via BMAD elicitation + adversarial review |
| 3 | `architecture` | `03-adr.md` | Grill constraints → architecture design + epics |
| 4 | `srs` | `05-srs.md` | Detailed SRS + edge cases + interface verification |
| 5 | `test-design` | `06-testcases.md` | Test cases from SRS (tests before code — TDD) |
| 6 | `implement` | code changes | Subagent-driven TDD implementation |
| 6b | `test-gate` | npm test | Automated test verification (loop 3x on fail) |
| 7 | `review` | `08-review.md` | Code review + quality gate + impact analysis |
| 8 | `feature-complete` | KNOWLEDGE.md | Update shared knowledge before shipping |
| 9 | `ship` | git commit + PR | Commit source code + create pull request |

Artifacts saved to `.vsaf/docs/features/{feature-name}/`. Each phase checks prerequisites — if the session crashes, resume from the last completed phase.

### Hotfix Flow (Bug Fix)

TDD-driven: receives a bug report, analyzes, writes failing test, fixes, reviews, ships.

```
/vsaf hotfix --args "path/to/bug-report.md"
```

| Phase | Skill | Description |
|---|---|---|
| 1 | `hotfix-analyze` | Read bug report → GitNexus impact → root cause |
| 2 | `hotfix-red` | TDD RED — write test that reproduces the bug (MUST FAIL) |
| 3 | `hotfix-green` | TDD GREEN — minimal fix to pass the test (MUST PASS) |
| 3b | `test-gate` | Full test suite — loop back to green on fail (max 3x) |
| 4 | `hotfix-review` | Minimality check + test quality + impact |
| 5 | `ship` | Git commit + PR |

Artifacts saved to `.vsaf/docs/hotfixes/{bug-id}/`.

### Crash Recovery

Long sessions can crash (context overflow, network). Sub-workflows let you resume without restarting the full pipeline:

```bash
# Session 1: thinking phase
/vsaf sdlc-thinking --args "Add OAuth2"
# → crash during PRD → 01-discovery.md already saved

# Session 2: resume just the PRD skill
/sdlc-prd
# → PRD completed, 02-prd.md saved

# Session 3: continue with design
/vsaf sdlc-design

# Session 4: build
/vsaf sdlc-build

# Session 5: ship
/vsaf sdlc-qa
```

Each phase reads input from files on disk — **no data is lost between sessions**.

### Individual Skills

Every SDLC phase can be invoked directly as a Claude skill:

```
/sdlc-init              # Setup
/sdlc-onboard-docs      # Index docs
/sdlc-onboard-code      # Index code
/sdlc-discovery         # Phase 1
/sdlc-prd               # Phase 2
/sdlc-architecture      # Phase 3
/sdlc-srs               # Phase 4
/sdlc-test-design       # Phase 5
/sdlc-implement         # Phase 6
/sdlc-review            # Phase 7
/sdlc-feature-complete  # Phase 8
/sdlc-ship              # Phase 9
/sdlc-sdlc-health       # Health check
/hotfix-analyze         # Hotfix Phase 1
/hotfix-red             # Hotfix Phase 2
/hotfix-green           # Hotfix Phase 3
/hotfix-review          # Hotfix Phase 4
```

### SDLC Skills (18)

| Skill | Purpose |
|---|---|
| `setup` | Install dependencies and configure environment |
| `init` | Bootstrap .vsaf/docs/, .mcp.json, CONTEXT.md |
| `onboard-docs` | Docs scan → graphify → CONTEXT.md |
| `onboard-code` | GitNexus index + Claude review + env check |
| `discovery` | Grill questions → brainstorm + GitNexus |
| `prd` | PRD with BMAD elicitation + adversarial review |
| `architecture` | Grill constraints → architecture + epics |
| `srs` | SRS + edge cases + GitNexus shape_check |
| `test-design` | Test design from SRS (TDD: tests before code) |
| `implement` | Subagent-driven TDD + SonarQube rules |
| `review` | Code review + quality gate + impact analysis |
| `feature-complete` | Update CONTEXT.md, KNOWLEDGE.md, re-index |
| `ship` | Git commit + PR via gh CLI |
| `sdlc-health` | Health check — verify all prerequisites |
| `hotfix-analyze` | Bug report → GitNexus + deep thinking → root cause |
| `hotfix-red` | TDD RED — write failing test that reproduces bug |
| `hotfix-green` | TDD GREEN — minimal fix to pass the test |
| `hotfix-review` | Quick review — minimality + test quality |

### Bundled BMAD Skills (17)

Used by discovery, prd, architecture, srs, test-design, and review phases:

| Skill | Purpose |
|---|---|
| `bmad-advanced-elicitation` | Push LLM to reconsider and deepen analysis |
| `bmad-brainstorming` | Facilitate interactive brainstorming |
| `bmad-domain-research` | Conduct domain and industry research |
| `bmad-prfaq` | Working Backwards PRFAQ challenge |
| `bmad-create-prd` | Create a PRD from scratch |
| `bmad-validate-prd` | Validate a PRD against standards |
| `bmad-review-adversarial-general` | Cynical review and challenge assumptions |
| `bmad-create-architecture` | Create architecture solution design |
| `bmad-create-epics-and-stories` | Break requirements into epics and stories |
| `bmad-check-implementation-readiness` | Validate PRD, UX, Architecture completeness |
| `bmad-agent-analyst` | Strategic business analyst |
| `bmad-review-edge-case-hunter` | Walk every branching path for edge cases |
| `bmad-code-review` | Review code changes adversarially |
| `bmad-party-mode` | Orchestrate group discussion simulations |
| `bmad-qa-generate-e2e-tests` | Generate end-to-end automated tests |
| `bmad-checkpoint-preview` | LLM-assisted human-in-the-loop checkpoint |
| `bmad-correct-course` | Manage significant changes during epic |

### Bundled Mattpocock Lean Skills (5)

Lean alternative for bugfix and known-domain flows:

| Skill | Purpose |
|---|---|
| `grill-me` | Interview relentlessly to extract requirements |
| `diagnose` | Disciplined diagnosis loop for bugs |
| `zoom-out` | Step back and evaluate broader context |
| `tdd` | Test-driven development with strict RED/GREEN |
| `improve-codebase-architecture` | Find deepening opportunities in architecture |

---

## Configuration

`.vsaf/config.yaml`:

```yaml
provider: claude          # AI provider (only 'claude' currently)
model: sonnet             # Default model: haiku, sonnet, opus

isolation:
  type: ephemeral         # Workspace strategy
  cleanup: after_success  # after_success | after_always | never
  exclude:                # Directories excluded from workspace copy
    - node_modules
    - .git
    - dist
    - build
    - .vsaf/storage
  max_workspaces: 5
```

**Cleanup policies:**
- `after_success` — keep workspace on failure for debugging
- `after_always` — always delete
- `never` — never delete (fills disk)

Add to `.gitignore`:

```
.vsaf/storage/
.vsaf/.claude-session
```

---

## Telemetry (OpenTelemetry / OTLP)

VSAF emits **standard OpenTelemetry** data over OTLP (http/protobuf): one trace per run (root span `vsaf:<workflow>`), one span per node execution with its **real wall-clock duration**, the [GenAI semantic-convention](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) attribute `gen_ai.request.model` on AI nodes, plus three run-total **metrics** (`vsaf.run.artifacts_created`, `.files_created`, `.loc_added`) keyed by `{workflow, user.id}`. Point it at any OTLP endpoint — an OTel Collector, Grafana/Tempo, SigNoz, Jaeger, or Langfuse's OTLP endpoint.

Telemetry is **disabled by default** and never fails a run — export errors are swallowed silently (set `VSAF_TELEMETRY_DEBUG=1` to see them and mirror spans to the console). Force-disable with `VSAF_TELEMETRY=off`. Flush at run end is bounded (≤5s) even when the endpoint is dead.

### Enable

Via standard OTel environment variables (recommended — keeps secrets out of the repo):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4318"   # /v1/traces + /v1/metrics appended
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <token>"  # optional auth
```

`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` / `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` are honored verbatim (no path appended). Note: the protocol is fixed to **http/protobuf** — `OTEL_EXPORTER_OTLP_PROTOCOL` has no effect.

Or in `.vsaf/config.yaml` (env vars take precedence):

```yaml
telemetry:
  otlp:
    endpoint: http://otel-collector:4318
```

### Migrating from the old Langfuse config (deprecated, still works)

Existing `telemetry.langfuse` configs (and `LANGFUSE_*` env vars) are **auto-mapped** to Langfuse's OTLP endpoint (`<host>/api/public/otel/v1/traces`, Basic auth, requires Langfuse ≥ v3.22 self-hosted) — traces keep flowing without any change. Two differences: metrics are not sent to Langfuse (its OTLP endpoint rejects them), and the old numeric **scores** are no longer emitted (they became OTel metrics). `vsaf doctor` prints a deprecation notice with this table:

| Old (`telemetry.langfuse`) | New (`telemetry.otlp`) |
|---|---|
| `host: https://lf.example.com` | `endpoint: https://lf.example.com/api/public/otel` (or any collector) |
| `public_key` + `secret_key` | `OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic base64(pk:sk)"` |
| Langfuse scores | OTel counters `vsaf.run.*` — build dashboards in your metrics backend |

### Privacy note

Traces carry `user.id` (from `VSAF_USER` → `git config user.name` → OS username), the run args (truncated at 4KB), and model names — all sent to whatever endpoint is configured, exactly as with the previous Langfuse SDK. Only point telemetry at infrastructure you trust.

### Session grouping (MCP mode) — SessionStart hook

VSAF stamps the Claude Code session id onto each trace (`session.id` on the root span) so vsaf traces and the gateway's own traces group into one session on your backend. To know the current session id, VSAF reads `.vsaf/.claude-session`, written by a SessionStart hook. **`vsaf init` adds this hook automatically** — for projects initialized before that, add it to your project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "node -e \"let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);require('fs').mkdirSync('.vsaf',{recursive:true});require('fs').writeFileSync('.vsaf/.claude-session',j.session_id||'')}catch{}})\""
      }]
    }]
  }
}
```

`vsaf doctor` reports telemetry status.

### What you'll see on your backend (MCP mode)

- **`vsaf:<workflow>` traces** — the semantic layer: one span per node execution (AI nodes named `invoke_agent <node>` with GenAI attributes; re-runs get `vsaf.attempt` 2, 3, … — the basis for rework metrics), durations, and statuses. Spans are exported as each node finishes.
- **Session grouping** — the root span carries `session.id` (the Claude Code session) and `user.id`; Langfuse maps both natively, other backends can group by attribute.
- **Run-total metrics** — counters `vsaf.run.{artifacts_created,files_created,loc_added}` by `{workflow, user.id}`: "who ships the most artifacts" dashboards live in your metrics backend (Grafana/SigNoz/…). Token and cost numbers come from the gateway's own telemetry.
- **Output metrics per AI node** (`metadata.outputMetrics`) — files/LOC the node produced, measured by diffing git state of the project dir at node start vs end: `filesCreated`, `filesModified`, `locAdded`, `locRemoved`, `artifactsCreated` (created files under `.vsaf/docs/`), and up to 20 `createdPaths`. Requires the project to be a git repo; anything else touching the repo during the node window is attributed to that node.
- **Dual-repo projects** — a project whose code lives in separate repos is measured across all of them, so design output and working code are both counted. The repos come from the workspace file `vsaf install` writes, or from `telemetry.artifacts.code_roots` when you name them yourself. Totals stay the sum; the split is reported as `vsaf.output.{spec,code}.*` span attributes and, once a run touches a code repo, as `{spec,code}_loc_added` / `_net_loc` / `_files_created` scores. Sum those scores rather than averaging them — a docs-only node contributes no entry instead of an explicit zero. Each repo needs at least one commit to be measurable.

---

## REST API

All endpoints prefixed with `/api`. Start with `vsaf serve`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/workflows` | List workflows |
| `GET` | `/api/workflows/:name` | Workflow detail (full DAG as JSON) |
| `POST` | `/api/runs` | Start a run → `202 { runId }` |
| `GET` | `/api/runs` | List runs |
| `GET` | `/api/runs/:runId` | Run detail (status + node results) |
| `GET` | `/api/runs/:runId/events` | SSE stream (realtime events) |

`POST /api/runs` returns `202 Accepted` immediately — the workflow runs async. Subscribe to SSE events for realtime progress.

### SSE Events

```
event: node:start
data: {"nodeId":"classify","timestamp":"..."}

event: node:complete
data: {"nodeId":"classify","durationMs":2100,"output":"bug"}

event: node:skip
data: {"nodeId":"plan","reason":"condition not met"}

event: run:complete
data: {"success":true,"totalMs":45200}
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Browser (Angular SPA)                  │
│   Dashboard ──── Workflow Detail ──── Run Execution      │
│    (HTTP)           (HTTP)           (EventSource)       │
└──────────┬───────────┬────────────────┬──────────────────┘
           ▼           ▼                ▼
┌──────────────────────────────────────────────────────────┐
│                  Fastify Server (packages/cli)            │
│   /api/health   /api/workflows/*   /api/runs/* + SSE     │
│                              ExecutionManager             │
│   @fastify/static ──→ Angular dist/ (SPA fallback)       │
└──────────────────────────┬───────────────────────────────┘
                           ▼
┌──────────────────────────────────────────────────────────┐
│                  Core Engine (packages/core)              │
│   DAG Parser → DAG Executor → Node Runner                │
│   Variable Resolver · Condition Evaluator                │
│   Workspace Manager · Run Store · Provider Registry      │
│   AJV Validation · Contract Checks · Cycle Detection     │
└──────────────────────────────────────────────────────────┘
```

Strict dependency direction: **web → (HTTP) → cli → core**. Published as a single npm package `@ngocsangairvds/vsaf`.

| Package | Responsibility |
|---|---|
| `packages/core` | Engine library: parsing, execution, providers, isolation, persistence |
| `packages/cli` | CLI commands + Fastify API server + MCP server |
| `packages/web` | Angular SPA dashboard (private, not published separately) |

### Design Decisions

| Decision | Choice | Why |
|---|---|---|
| DAG scheduling | Wave-based parallel scan | Simple, no topological sort, natural parallelism |
| Workspace isolation | Copy project to temp dir | Prevents partial changes on failure, safe rollback |
| Run persistence | JSON files, one per run | No database, human-readable, easy to debug |
| API framework | Fastify 5 | TypeScript-first, fast, built-in `inject()` for testing |
| Realtime | SSE (not WebSocket) | One-way sufficient, simpler protocol |
| Frontend | Angular 19 standalone | Strong TypeScript integration, lazy-loaded routes |
| AI adapter | Shell out to `claude` CLI | No SDK dependency, simple to test |
| Schema validation | AJV | Industry standard JSON Schema |
| MCP integration | Stdio-based MCP server | Native Claude Code protocol, zero network config |
| Skill distribution | `vsaf install` → `.claude/skills/` | Project-local install, available to Claude Code |

### Tech Stack

| Layer | Technology |
|---|---|
| Language | TypeScript 6 |
| Runtime | Node.js >= 20 |
| Build | tsc (project references) |
| API Server | Fastify 5 |
| Frontend | Angular 19 + Tailwind CSS 4 |
| Realtime | Server-Sent Events (SSE) |
| Testing | Vitest |
| AI Provider | Claude Code (extensible) |
| AI Integration | Model Context Protocol (MCP) |
| Schema Validation | AJV |

---

## Programmatic Usage

Use `@ngocsangairvds/vsaf` as a library:

```typescript
import { parseWorkflow, DAGExecutor, ProviderRegistry, ClaudeCodeAdapter } from '@ngocsangairvds/vsaf';
import { readFileSync } from 'fs';

// Parse workflow
const yaml = readFileSync('.vsaf/workflows/fix-issue.yaml', 'utf-8');
const graph = parseWorkflow(yaml);

console.log(graph.name);           // "fix-issue"
console.log(graph.nodes.size);     // 10

// Execute with provider
const registry = new ProviderRegistry();
registry.register(new ClaudeCodeAdapter());
const provider = registry.get('claude');

const executor = new DAGExecutor(provider, workspacePath, projectPath, graph, {
  onNodeStart: (id) => console.log(`▶ ${id}`),
  onNodeComplete: (id, r) => console.log(`✓ ${id} (${r.durationMs}ms)`),
  onNodeSkip: (id, reason) => console.log(`⊘ ${id}: ${reason}`),
  onNodeFail: (id, err) => console.error(`✗ ${id}: ${err}`),
});

const result = await executor.execute('fix #42', artifactsPath);
```

---

## Development

```bash
npm install          # Install dependencies
npm test             # Run tests
npm run test:watch   # Watch mode
npm run lint         # Type check
npm run build        # Build all packages
```

```
vsaf/
├── packages/core/     ← Engine library
├── packages/cli/      ← CLI + API server + MCP
├── packages/web/      ← Angular dashboard
├── skills/            ← Skill pack definitions
├── workflows/         ← Default workflow YAML files
├── commands/          ← Default command templates
└── tests/             ← Vitest test suites
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `vsaf: command not found` | `npm install -g @ngocsangairvds/vsaf` or use `npx vsaf` |
| `claude: command not found` | Install Claude Code CLI |
| `gh: command not found` | Install GitHub CLI: `brew install gh` or https://cli.github.com |
| `.vsaf/ already exists` | `rm -rf .vsaf/` then `vsaf init` |
| `Workflow not found` | Check `vsaf list`. Ensure `.vsaf/workflows/xxx.yaml` exists |
| `Command not found` | Ensure `.vsaf/commands/xxx.md` exists with correct frontmatter |
| Run stuck / no progress | Check `claude --print "hello"` works. Check network |
| `vsaf serve` shows "Web UI not built" | Build Angular: `cd packages/web && npx ng build` |
| Workspace disk full | Set `cleanup: after_always` in config.yaml or `rm -rf /tmp/vsaf-*` |

## License

MIT
