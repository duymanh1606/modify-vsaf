---
name: vsaf
description: Run a VSAF DAG workflow by name from inside Claude — /vsaf <workflow> [args...]. Lists available workflows when called without arguments.
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# /vsaf — Workflow Runner

You drive a VSAF DAG workflow through the vsaf MCP server. The engine owns
ordering, bash nodes, gates, and telemetry; you execute the AI nodes it hands
you.

## Input

`$ARGUMENTS` = `<workflow> [args...]` — or a natural-language intent.

Trim `$ARGUMENTS` first.

- **Empty after trim?** List the available workflows instead of running one:
  read `.vsaf/workflows/**/*.yaml`, print each as `<name> — <description>`
  (both fields are at the top of each file), then stop.
- **First token resolves to a workflow?** The first whitespace-separated
  token names a workflow when `.vsaf/workflows/<token>.yaml` exists (the
  token may contain `/`, e.g. `sdlc/master-sdlc`). If it exists: that is the
  workflow; everything after the first token is the args string. Run it
  exactly as before — the router is NOT involved. A token containing `..`
  (path traversal) never resolves to a workflow; treat such input as a
  natural-language intent instead.
- **First token does NOT resolve?** Treat the ENTIRE original (trimmed)
  `$ARGUMENTS` as a natural-language intent: start the Intent Router via
  `vsaf_start` with `{ workflow: "router", args: <the full intent string>,
  projectPath: <project root> }` and drive it with the normal Execution
  Loop. Never report "workflow not found" for a natural-language request.
  After the router run completes, follow § Router Chaining.

## Requirements

The vsaf MCP tools (`vsaf_start`, `vsaf_next`, `vsaf_status`) must be
available. If they are not, tell the user to enable the project MCP servers
(`.mcp.json` already registers `vsaf`) and restart the Claude session — do not
try to simulate the engine yourself.

## Execution Loop

1. Call `vsaf_start` with `{ workflow, args, projectPath: <project root> }`.
2. The engine returns completed bash results plus the AI nodes ready to run.
   Each node carries a `context` field — branch on it:
   - `context: inherit` — execute the prompt faithfully inline in this
     session. The prompt text arrives resolved from the engine (inline from
     workflow `prompt:` nodes, or from `.vsaf/commands/*.md` for command
     nodes).
   - `context: fresh` — do NOT execute inline. Spawn a subagent via the
     Task tool (`subagent_type: general-purpose`, `model` = the node's
     `model` field; if that value isn't a valid Task-tool alias —
     sonnet/opus/haiku — map it to the closest one). The subagent prompt is
     the node prompt verbatim, plus
     this closing line: "Finish with a short summary of what you produced
     (files, decisions, results) — that summary is this node's output for
     downstream nodes." Use the subagent's final message as the node
     output. When several fresh nodes are ready together, spawn them in
     one message so they run concurrently. Fresh nodes cannot ask the
     user questions — never route interactive work here.
   Print progress as `[<workflow>] node <id>... ⏳/✅/❌`.
3. Report each finished node via `vsaf_next` with the run id and node results.
   **Reporting structured output:** when a node declares `output_format`
   (check the node's definition in the workflow YAML at
   `.vsaf/workflows/<workflow>.yaml`), extract the JSON object matching that
   schema from the node's answer and pass it as `structuredOutput` alongside
   `output` in that result entry. Downstream `when` conditions and
   `$node.output.<field>` references only work if you send it. Nodes without
   `output_format` are reported exactly as before.
4. Repeat until the engine reports the run is complete (or failed).
5. If the session is interrupted, the run can be resumed later: mention the
   run id and `vsaf run <workflow> --resume <runId>`.

## Completion

Summarize: nodes executed (with status), gates passed/failed, artifacts
produced, and the run id. Telemetry note: each run emits a Langfuse trace
named `vsaf:<workflow>` automatically when telemetry is configured.

## Router Chaining

Applies only when the run you just completed had `workflow === "router"`.

- Take the `confirm` node's `structuredOutput` (`{confirmed, workflow, args}`).
- `confirmed === true` → call `vsaf_start` a SECOND time with
  `{ workflow: <structuredOutput.workflow>, args: <structuredOutput.args>,
  projectPath }` and drive that run with the normal Execution Loop. This is
  a separate run with its own run id and its own Langfuse trace (both group
  under the current session automatically).
- `confirmed` is false or absent (no-match branch, declined, or the router
  failed) → do NOT start anything; summarize the router run only.
- If the second `vsaf_start` itself fails (e.g. the confirmed workflow does
  not exist), report that failure explicitly as "target run failed to
  start" — the router run still succeeded; do not conflate the two.
- Always report BOTH run ids, labeled: `router run <id1>` and
  `<workflow> run <id2>`. When mentioning resume, name which run a resume
  command targets: resuming the router = `vsaf run router --resume <id1>`;
  resuming the target = `vsaf run <workflow> --resume <id2>`. Never imply a
  target run exists when confirm was declined.
