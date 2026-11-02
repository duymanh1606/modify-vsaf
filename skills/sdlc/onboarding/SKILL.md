---
name: onboarding
description: Phase 0 — Full project onboarding in one command; runs docs graph (onboard-docs) then code graph + env setup (onboard-code)
version: 1.0.0
author: "@ngocsangairvds/vsaf"
---

# Onboarding — One-Command Project Onboarding

You are running the full Phase 0 onboarding chain. This is the single entry
point devs use on a fresh project: `/sdlc-onboarding`.

## Progress Protocol

Each step prints progress:
```
[ONBOARDING] [1/2] description... (icon)
```
Icon: `⏳` running, `✅` done, `❌` error.

## Input

- Project path: `$ARGUMENTS` (or current directory)

## Preferred Path: run as a vsaf workflow

If the vsaf MCP tools (`vsaf_start`, `vsaf_next`, `vsaf_status`) are available,
drive the chain through the engine so the run gets dependency ordering, resume
support, and a Langfuse trace:

1. Call `vsaf_start` with `workflow: "sdlc/onboarding"` and `args: $ARGUMENTS`.
2. Execute each AI node the engine returns (they map to the skills below).
3. Report results via `vsaf_next` until the run completes.

## Fallback Path: run the skills directly

If the vsaf MCP server is not available, run the two phases in order — each is
a skill already installed in this project:

```
[ONBOARDING] [1/2] Docs graph (sdlc-onboard-docs)... ⏳
```

1. Invoke the `sdlc-onboard-docs` skill with the same arguments.

```
[ONBOARDING] [2/2] Code graph + env setup (sdlc-onboard-code)... ⏳
```

2. After docs onboarding completes, invoke the `sdlc-onboard-code` skill.

## Completion

Summarize for the user:
- Docs graph status (graphify output location)
- Code graph status (GitNexus index, symbol/relationship counts)
- Environment check results and anything the dev must fix manually
