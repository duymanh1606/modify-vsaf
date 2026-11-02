/**
 * workflow-hooks.js — node→hook map for the Antigravity driver.
 *
 * The 16 NTAPP event hooks (hooks/*.sh) were wired to Claude Code events
 * (UserPromptSubmit / SubagentStop / PostToolUse). The Antigravity driver
 * (vsaf-agy-driver.cjs) runs one `agy -p` process per DAG node, so there is no
 * Claude event bus — instead the driver fires hooks at NODE BOUNDARIES:
 *
 *   Claude UserPromptSubmit  -> driver `pre`  (before the node's agy call)
 *   Claude SubagentStop      -> driver `post` (after the node's agy call)
 *   Claude PostToolUse       -> agy-native PostToolUse hook (per-edit), with a
 *                               driver `post` SWEEP as the host-agnostic fallback.
 *
 * This map is keyed by the BASE node id (fanout sub-nodes `id~fanout~N` strip the
 * suffix). It is the single source of truth for which hook fires where; the exact
 * shell scripts and their pass/block logic are reused VERBATIM from hooks/.
 *
 * Each spec:
 *   { hook, event, blocking, prompt?, sweep? }
 *     hook     - basename of the script in hooks/ (no .sh)
 *     event    - synthetic Claude event name fed to the hook ('UserPromptSubmit' |
 *                'SubagentStop' | 'PostToolUse'); the hook reads it from stdin.
 *     blocking - if the hook exits 2, halt the workflow (true) or warn+continue (false).
 *                Mirrors each hook's own design: gates block, recorders/advisories warn.
 *     prompt   - (pre hooks) synthetic `.prompt` so the hook's slash-command grep
 *                fires; `{ID}` is replaced by the node's resolved target unit id.
 *     sweep    - (build_loop) run per changed code file via `git status` instead of
 *                a single synthetic stdin (mirrors Claude's per-edit PostToolUse).
 *
 * Lane fidelity (CLAUDE.md §"So sánh 4 workflow build"):
 *   - ad-hoc-per-unit is the RELAXED lane: NO Hook 3 (skips Stage 3 / no slice plan),
 *     NO Hook 10 (relaxed = test+lint only). Matches each ad-hoc node's YAML comment.
 *   - slice-loop is FULL strictness: Hook 3 input-gate + Hook 10 verification-gate.
 */

'use strict';

// Hook 3 reuse — fires before technical-design / ux-design / feature-design.
const HOOK3 = (prompt) => ({ hook: 'stage3_input_gate', event: 'UserPromptSubmit', blocking: true, prompt });

module.exports = {
  'slice-loop': {
    // Stage 3a — techspec per module. Pre: Hook 3 input gate.
    'techspec-per-module': {
      pre: [HOOK3('/ntapp-technical-design {ID}')],
    },
    // Stage 3b — UX spec singleton. Pre: Hook 3 (reuse).
    'ux-design-update': {
      pre: [HOOK3('/ntapp-ux-design')],
    },
    // Stage 4a — DD per unit. Pre: Hook 3. Post: Hook 4 completeness (warn-only).
    'dd-per-unit': {
      pre: [HOOK3('/ntapp-feature-design {ID}')],
      post: [{ hook: 'stage4a_complete', event: 'SubagentStop', blocking: false }],
    },
    // Stage 4b — ui_schema per FE unit. Post: Hook 5 ds-delta-router (RECORDER, warn-only;
    // fires after /ntapp-ui-generation, exactly Claude's SubagentStop timing).
    'ui-schema-per-fe-unit': {
      post: [{ hook: 'ds_delta_router', event: 'SubagentStop', blocking: false }],
    },
    // Stage 4b — DS build per FE unit. Pre: Hook 5b approval gate. Post: Hook 6 build verify.
    'ds-build-per-fe-unit': {
      pre: [{ hook: 'ds_build_approval_gate', event: 'UserPromptSubmit', blocking: true,
              prompt: '/ntapp-ds-build-component {ID}' }],
      post: [{ hook: 'build_component_verify', event: 'SubagentStop', blocking: true }],
    },
    // Stage 4c — story per unit. Post: Hook 7 story-bridge gate (blocks).
    'story-bridge-per-unit': {
      post: [{ hook: 'story_bridge_gate', event: 'SubagentStop', blocking: true }],
    },
    // Stage 4d — ATDD tests per story. Post: Hook 9 build-loop sweep (test files).
    'atdd-tests-per-story': {
      post: [{ hook: 'build_loop', event: 'PostToolUse', blocking: true, sweep: true }],
    },
    // Stage 5 — dev per story. Pre: Hook 8 ATDD classifier (advisory). Post: Hook 9 sweep
    // + Hook 10 verification gate (FULL strictness: tests + ATDD + sonar + review recency).
    'dev-per-story': {
      pre: [{ hook: 'atdd_classifier', event: 'UserPromptSubmit', blocking: false,
              prompt: '/bmad-dev-story {ID}.md' }],
      post: [
        { hook: 'build_loop', event: 'PostToolUse', blocking: true, sweep: true },
        { hook: 'verification_gate', event: 'UserPromptSubmit', blocking: true,
          prompt: '/bmad-dev-story --commit' },
      ],
    },
    // Stage 5 pre — cross-unit wire-up. Post: Hook 9 sweep (seam patches are code).
    'slice-integration': {
      post: [{ hook: 'build_loop', event: 'PostToolUse', blocking: true, sweep: true }],
    },
  },

  'ad-hoc-per-unit': {
    // Stage 4a — DD. Post: Hook 4 (warn-only). NO Hook 3 (relaxed lane, no slice plan).
    'dd': {
      post: [{ hook: 'stage4a_complete', event: 'SubagentStop', blocking: false }],
    },
    // Stage 4b — ui_schema. Post: Hook 5 ds-delta-router (recorder).
    'ui-schema': {
      post: [{ hook: 'ds_delta_router', event: 'SubagentStop', blocking: false }],
    },
    // Stage 4b — DS build. Pre: Hook 5b approval gate. Post: Hook 6 build verify.
    'ds-build': {
      pre: [{ hook: 'ds_build_approval_gate', event: 'UserPromptSubmit', blocking: true,
              prompt: '/ntapp-ds-build-component {ID}' }],
      post: [{ hook: 'build_component_verify', event: 'SubagentStop', blocking: true }],
    },
    // Stage 4c — story. Post: Hook 7 story-bridge gate.
    'story-bridge': {
      post: [{ hook: 'story_bridge_gate', event: 'SubagentStop', blocking: true }],
    },
    // Stage 4d — ATDD tests. Post: Hook 9 sweep.
    'atdd-tests': {
      post: [{ hook: 'build_loop', event: 'PostToolUse', blocking: true, sweep: true }],
    },
    // Stage 5 — dev. Pre: Hook 8 classifier (advisory). Post: Hook 9 sweep.
    // NO Hook 10 (relaxed lane = test+lint only, per CLAUDE.md table).
    'dev': {
      pre: [{ hook: 'atdd_classifier', event: 'UserPromptSubmit', blocking: false,
              prompt: '/bmad-dev-story {ID}.md' }],
      post: [{ hook: 'build_loop', event: 'PostToolUse', blocking: true, sweep: true }],
    },
  },
};
