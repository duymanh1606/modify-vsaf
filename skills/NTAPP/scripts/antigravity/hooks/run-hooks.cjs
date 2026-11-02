/**
 * run-hooks.cjs — driver-side hook executor for the Antigravity VSAF host.
 *
 * Reuses the existing NTAPP hook scripts (hooks/*.sh) VERBATIM. The only thing this
 * module adds is the wiring Claude Code's event bus used to provide: it synthesizes
 * the minimal stdin JSON each hook reads, runs the hook with cwd=project, and reads
 * exit code 2 as "block" (Claude's convention; see hooks/lib/common.sh `block()`).
 *
 * Fired by vsaf-agy-driver.cjs at node boundaries (see workflow-hooks.js for the map):
 *   runPreHooks  before the node's `agy -p` call   (Claude UserPromptSubmit equivalent)
 *   runPostHooks after the node's `agy -p` call     (Claude SubagentStop / PostToolUse)
 *
 * Determinism win over Claude's heuristics: in a parallel fanout (mc:5), Claude's
 * SubagentStop hooks pick "the newest artifact in the last 5 min" — racy across
 * concurrent sub-agents. Here the driver knows each node's exact unit id, so we pass
 * HOOK_TARGET_ID and the hooks resolve THAT unit's artifact (backward-compatible:
 * hooks fall back to the -mmin heuristic when the env is unset → Claude path unchanged).
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync, execSync } = require('child_process');

const MAP = require('./workflow-hooks.js');

const TRUTHY = new Set(['1', 'true', 'yes', 'on']);
const isTrue = (v) => TRUTHY.has(String(v || '').trim().toLowerCase());

// Hooks layer fully off? (DISABLE_HOOKS_ALL is also honored by each hook itself.)
function hooksDisabled() {
  return isTrue(process.env.NTAPP_AGY_NO_HOOKS) || isTrue(process.env.DISABLE_HOOKS_ALL);
}

// Canonical hooks dir: env override → <project>/hooks → <project>/.claude/hooks (symlink).
function resolveHooksDir(project) {
  const cands = [
    process.env.NTAPP_HOOKS_DIR,
    path.join(project, 'hooks'),
    path.join(project, '.claude', 'hooks'),
  ].filter(Boolean);
  for (const d of cands) {
    if (fs.existsSync(path.join(d, 'lib', 'common.sh'))) return d;
  }
  return null;
}

// fanout sub-node id `foo~fanout~3` → base `foo`.
const FANOUT_SEP = '~fanout~';
function baseNodeId(nodeId) {
  const i = nodeId.indexOf(FANOUT_SEP);
  return i === -1 ? nodeId : nodeId.slice(0, i);
}

// Resolve the unit/module id this node targets, for deterministic per-unit hooks.
//   fanout node → the marker path interpolated into the prompt
//                 (NTAPP-output/.work/slice-(units|modules)/<marker>); strip NN_ order prefix.
//   single node → NTAPP-output/.current-unit-id (ad-hoc-per-unit writes it).
function resolveTargetId(node, project) {
  if (node.nodeId.includes(FANOUT_SEP) && node.prompt) {
    const m = node.prompt.match(/\.work\/slice-(?:units|modules)\/([^\s"'`)]+)/);
    if (m) return m[1].replace(/^\d+_/, '');
  }
  try {
    const f = path.join(project, 'NTAPP-output', '.current-unit-id');
    if (fs.existsSync(f)) {
      const id = fs.readFileSync(f, 'utf8').trim();
      if (id) return id;
    }
  } catch { /* ignore */ }
  return null;
}

// Code files changed (uncommitted) — the build_loop sweep set. Committed files were
// already gated by the git pre-commit hook, so the two together cover every code file.
const CODE_RE = /\.(ts|tsx|js|jsx|go|java|kt|py|rs|cs|swift|vue|html|css|scss|sass|less)$/;
function sweepFiles(cwd) {
  let out = '';
  try {
    out = execSync('git status --porcelain --untracked-files=all', { cwd, encoding: 'utf8' });
  } catch { return []; }
  const files = [];
  for (const line of out.split('\n')) {
    if (!line.trim()) continue;
    let p = line.slice(3);                 // strip XY + space
    if (p.includes(' -> ')) p = p.split(' -> ')[1]; // rename: take dest
    p = p.replace(/^"|"$/g, '');
    if (CODE_RE.test(p)) files.push(path.resolve(cwd, p));
  }
  return files;
}

// Run one hook script with synthesized stdin. exit 2 = block; exit 0 = pass.
function runHookScript(hooksDir, hookName, stdinObj, { cwd, extraEnv }) {
  const script = path.join(hooksDir, `${hookName}.sh`);
  if (!fs.existsSync(script)) {
    return { code: 0, stderr: `[run-hooks] WARN: ${hookName}.sh not found in ${hooksDir} — skipped` };
  }
  const r = spawnSync('bash', [script], {
    cwd,
    input: JSON.stringify(stdinObj),
    env: { ...process.env, ...extraEnv },
    encoding: 'utf8',
  });
  if (r.error) return { code: 0, stderr: `[run-hooks] WARN: ${hookName} spawn failed: ${r.error.message}` };
  return { code: r.status == null ? 0 : r.status, stderr: (r.stderr || '').trim() };
}

// Execute one hook spec → { blocked, hook, message, warn }.
function runOne(spec, node, ctx) {
  const { hooksDir, project, cwd, phase } = ctx;
  const targetId = resolveTargetId(node, project);
  const extraEnv = targetId ? { HOOK_TARGET_ID: targetId } : {};

  // build_loop sweep: one invocation per changed code file (Claude per-edit PostToolUse).
  if (spec.sweep) {
    const files = sweepFiles(cwd);
    const blocks = [];
    for (const file of files) {
      const stdin = { hook_event_name: 'PostToolUse', tool_name: 'Write',
                      tool_input: { file_path: file }, cwd };
      const r = runHookScript(hooksDir, spec.hook, stdin, { cwd, extraEnv });
      if (r.code === 2) blocks.push(`${path.relative(cwd, file)}: ${r.stderr}`);
    }
    if (blocks.length) {
      return { blocked: spec.blocking, hook: spec.hook,
               message: `build-loop violations on ${blocks.length} file(s):\n  - ${blocks.join('\n  - ')}` };
    }
    return { blocked: false };
  }

  // pre (UserPromptSubmit) — synthetic prompt; {ID} → resolved target.
  // post (SubagentStop)   — synthetic stop event; hooks read artifacts off disk.
  let stdin;
  if (spec.event === 'UserPromptSubmit') {
    const prompt = (spec.prompt || '').replace('{ID}', targetId || '');
    stdin = { hook_event_name: 'UserPromptSubmit', prompt, cwd };
  } else {
    stdin = { hook_event_name: spec.event || 'SubagentStop', stop_hook_active: false,
              transcript_path: '', cwd };
  }
  const r = runHookScript(hooksDir, spec.hook, stdin, { cwd, extraEnv });
  if (r.code === 2) {
    return { blocked: spec.blocking, hook: spec.hook,
             message: r.stderr || `${spec.hook} blocked (exit 2)`, warn: !spec.blocking };
  }
  return { blocked: false };
}

// Run all `pre` (or `post`) specs for a node. Returns { blocked, blocks:[], warns:[] }.
function runPhase(phase, workflow, node, ctx) {
  const out = { blocked: false, blocks: [], warns: [] };
  if (hooksDisabled() || !ctx.hooksDir) return out;
  const wf = MAP[workflow];
  if (!wf) return out;
  const specs = (wf[baseNodeId(node.nodeId)] || {})[phase] || [];
  for (const spec of specs) {
    const r = runOne(spec, node, { ...ctx, phase });
    if (!r.hook) continue;
    if (r.blocked) out.blocks.push({ hook: r.hook, message: r.message });
    else out.warns.push({ hook: r.hook, message: r.message });
  }
  out.blocked = out.blocks.length > 0;
  return out;
}

// Public: what hooks WOULD fire (for --dry-run logging), without running them.
function planForNode(workflow, nodeId) {
  const wf = MAP[workflow];
  if (!wf) return { pre: [], post: [] };
  const entry = wf[baseNodeId(nodeId)] || {};
  const fmt = (s) => `${s.hook}${s.blocking ? '' : ' (warn)'}${s.sweep ? ' (sweep)' : ''}`;
  return { pre: (entry.pre || []).map(fmt), post: (entry.post || []).map(fmt) };
}

module.exports = {
  resolveHooksDir,
  baseNodeId,
  resolveTargetId,
  runPreHooks: (workflow, node, ctx) => runPhase('pre', workflow, node, ctx),
  runPostHooks: (workflow, node, ctx) => runPhase('post', workflow, node, ctx),
  planForNode,
  hooksDisabled,
};
