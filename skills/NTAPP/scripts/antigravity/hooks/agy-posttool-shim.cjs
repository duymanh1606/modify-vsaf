#!/usr/bin/env node
/**
 * agy-posttool-shim.cjs — adapter: agy-native PostToolUse hook → NTAPP build_loop.sh.
 *
 * This is the ONE NTAPP hook that genuinely belongs inside agy (not the driver): Hook 9
 * (build_loop) fires PER FILE EDIT, mid-node — the driver only sees node boundaries. agy
 * fires PostToolUse after a tool runs, passing the tool event as JSON on stdin and matching
 * on tool name. This shim:
 *   1. reads agy's PostToolUse event JSON from stdin,
 *   2. digs out the edited file path (schema-tolerant — agy's exact shape isn't documented),
 *   3. re-shapes it into the Claude stdin build_loop.sh expects
 *        { hook_event_name:"PostToolUse", tool_name:"Write", tool_input:{ file_path } },
 *   4. runs build_loop.sh and maps exit 2 → an agy block decision (+ stderr for the agent).
 *
 * Install via the agy `/hooks` form (1.0.14 has no CLI subcommand; see install-agy-hooks.sh):
 *   event   : PostToolUse
 *   matcher : write_to_file|replace_file_content
 *   command : node
 *   args    : ["<repo>/scripts/antigravity/hooks/agy-posttool-shim.cjs"]
 *
 * Best-effort on the block contract: the git pre-commit hook is the hard backstop for
 * Rules 1-9, and the driver's post-node sweep re-runs build_loop at node end. This shim
 * is the realtime "fail fast" layer so the agent self-corrects in the same turn.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function readStdin() {
  try { return fs.readFileSync(0, 'utf8'); } catch { return ''; }
}

// Recursively find the first plausible edited-file path in agy's event JSON.
// Prefer keys that look like a file path; fall back to any string that is an existing file.
function findFilePath(obj) {
  const keyHit = [];
  const fileHit = [];
  const KEY_RE = /(file_?path|filepath|absolute_?path|target_?file|^path$|^file$)/i;
  const walk = (v, key) => {
    if (v == null) return;
    if (typeof v === 'string') {
      if (key && KEY_RE.test(key) && /[\/\\]/.test(v)) keyHit.push(v);
      else if (/[\/\\].+\.[A-Za-z0-9]+$/.test(v)) { try { if (fs.existsSync(v)) fileHit.push(v); } catch {} }
      return;
    }
    if (Array.isArray(v)) { v.forEach(x => walk(x, key)); return; }
    if (typeof v === 'object') { for (const k of Object.keys(v)) walk(v[k], k); }
  };
  walk(obj, null);
  return keyHit[0] || fileHit[0] || null;
}

// Locate hooks/ (build_loop.sh + lib/common.sh): env → walk up from cwd.
function resolveHooksDir(startCwd) {
  if (process.env.NTAPP_HOOKS_DIR && fs.existsSync(path.join(process.env.NTAPP_HOOKS_DIR, 'build_loop.sh')))
    return process.env.NTAPP_HOOKS_DIR;
  let dir = startCwd;
  for (let i = 0; i < 8; i++) {
    for (const cand of [path.join(dir, 'hooks'), path.join(dir, '.claude', 'hooks')]) {
      if (fs.existsSync(path.join(cand, 'build_loop.sh'))) return cand;
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function emitBlock(reason) {
  // Cover both agy-proto (blocked/block_reason) and Claude-style (decision/reason) shapes.
  process.stdout.write(JSON.stringify({ blocked: true, block_reason: reason, decision: 'block', reason }) + '\n');
  process.stderr.write(reason + '\n');
  process.exit(2);
}

function main() {
  const raw = readStdin();
  let event;
  try { event = JSON.parse(raw); } catch { process.exit(0); } // unparseable → don't block

  const file = findFilePath(event);
  if (!file) process.exit(0);                       // no file in event → nothing to lint

  const cwd = process.cwd();
  const hooksDir = resolveHooksDir(cwd);
  if (!hooksDir) process.exit(0);                   // hooks not found here → defer to pre-commit

  const stdin = { hook_event_name: 'PostToolUse', tool_name: 'Write',
                  tool_input: { file_path: path.resolve(cwd, file) }, cwd };
  const r = spawnSync('bash', [path.join(hooksDir, 'build_loop.sh')], {
    cwd, input: JSON.stringify(stdin), env: process.env, encoding: 'utf8',
  });

  if (r.status === 2) emitBlock((r.stderr || 'build-loop violation').trim());
  process.exit(0);
}

main();
