#!/usr/bin/env node
/**
 * test-driver-hooks.cjs — harness for the Antigravity node-boundary hook layer.
 *
 * Verifies that run-hooks.cjs actually RUNS the reused hooks/*.sh and maps exit 2 → block,
 * that per-unit targeting (HOOK_TARGET_ID) picks the right artifact, and that the build_loop
 * sweep catches a bad file. Mirrors hooks/tests/run.sh style (temp git repos, auto-clean).
 *
 *   node scripts/antigravity/hooks/test-driver-hooks.cjs   # exit 0 = all pass
 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');
const H = require('./run-hooks.cjs');

const HOOKS_DIR = path.resolve(__dirname, '../../../hooks');
let PASS = 0, FAIL = 0;
const tmps = [];
process.on('exit', () => tmps.forEach(d => { try { fs.rmSync(d, { recursive: true, force: true }); } catch {} }));

function expect(desc, got, want) {
  if (got === want) { console.log(`  ok   ${desc} (=${got})`); PASS++; }
  else { console.log(`  FAIL ${desc} (want ${want}, got ${got})`); FAIL++; }
}
function newRepo() {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'agy-hooktest-'));
  execSync('git init -q', { cwd: d }); tmps.push(d); return d;
}
function write(p, c) { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, c); }
function ctx(project) { return { hooksDir: HOOKS_DIR, project, cwd: project }; }
const node = (nodeId, prompt) => ({ nodeId, prompt: prompt || '' });

// ── target resolution (pure) ────────────────────────────────────────────────
console.log('── target resolution ──');
expect('fanout unit marker → strips NN_ prefix',
  H.resolveTargetId(node('dd-per-unit~fanout~2', 'ITEM = NTAPP-output/.work/slice-units/03_SCR-LOGIN\nfoo'), '/x'),
  'SCR-LOGIN');
expect('fanout module marker → bare id',
  H.resolveTargetId(node('techspec-per-module~fanout~0', 'ITEM = NTAPP-output/.work/slice-modules/MPF\nfoo'), '/x'),
  'MPF');
{
  const r = newRepo(); write(path.join(r, 'NTAPP-output/.current-unit-id'), 'BE-BMS-09\n');
  expect('single node → reads .current-unit-id', H.resolveTargetId(node('dev', ''), r), 'BE-BMS-09');
}

// ── story_bridge_gate (Hook 7) post, BLOCKING, targeted ─────────────────────
console.log('── story_bridge_gate (post, blocking) ──');
function storyRepo(complete) {
  const r = newRepo();
  write(path.join(r, '.bmm-entry-mode'), 'mode: stage_4_standalone\n'); // skip slice_id check
  const body = complete
    ? '## Acceptance Criteria\n- a\n## Tasks\n- t\n## Dev Notes\nn\n## Testing\nx\n'
    : '## Acceptance Criteria\n- a\n'; // missing Tasks/Dev Notes/Testing
  write(path.join(r, 'NTAPP-output/Stage_5_Build_Verify/MPF-01.md'), body);
  return r;
}
{
  const r = storyRepo(false);
  const out = H.runPostHooks('slice-loop', node('story-bridge-per-unit~fanout~0', 'ITEM = NTAPP-output/.work/slice-units/01_MPF-01'), ctx(r));
  expect('incomplete story → blocked', out.blocked, true);
}
{
  const r = storyRepo(true);
  const out = H.runPostHooks('slice-loop', node('story-bridge-per-unit~fanout~0', 'ITEM = NTAPP-output/.work/slice-units/01_MPF-01'), ctx(r));
  expect('complete story → not blocked', out.blocked, false);
}

// ── ds_build_approval_gate (Hook 5b) pre, BLOCKING, targeted ────────────────
console.log('── ds_build_approval_gate (pre, blocking) ──');
function dsRepo(status) {
  const r = newRepo();
  const dir = path.join(r, 'NTAPP-output/design-system/feature_deltas/SCR-FOO');
  write(path.join(dir, 'ds_delta_decision.md'), `---\nid: SCR-FOO\nstatus: ${status}\n---\n`);
  return r;
}
{
  const r = dsRepo('pending');
  const out = H.runPreHooks('slice-loop', node('ds-build-per-fe-unit~fanout~0', 'ITEM = NTAPP-output/.work/slice-units/01_SCR-FOO'), ctx(r));
  expect('pending decision → blocked', out.blocked, true);
}
{
  const r = dsRepo('approved');
  const out = H.runPreHooks('slice-loop', node('ds-build-per-fe-unit~fanout~0', 'ITEM = NTAPP-output/.work/slice-units/01_SCR-FOO'), ctx(r));
  expect('approved decision → not blocked', out.blocked, false);
}

// ── build_loop (Hook 9) post SWEEP, BLOCKING ────────────────────────────────
console.log('── build_loop sweep (post, blocking) ──');
{
  const r = newRepo();
  write(path.join(r, 'NTAPP-output/Stage_2_Architecture/project_wbs.md'),
    '| ID | Type | Module |\n|----|------|--------|\n| MPF-01 | feature | core |\n');
  write(path.join(r, 'bad.ts'), 'export const x = 1\n'); // untracked code, NO header → Rule 1 block
  const out = H.runPostHooks('ad-hoc-per-unit', node('dev', ''), ctx(r));
  expect('untracked code w/o header → blocked', out.blocked, true);
}
{
  const r = newRepo();
  write(path.join(r, 'README.md'), '# docs only\n'); // non-code untracked → no block
  const out = H.runPostHooks('ad-hoc-per-unit', node('dev', ''), ctx(r));
  expect('no code changes → not blocked', out.blocked, false);
}

// ── disable switch ──────────────────────────────────────────────────────────
console.log('── disable switch ──');
{
  const r = storyRepo(false);
  process.env.NTAPP_AGY_NO_HOOKS = '1';
  const out = H.runPostHooks('slice-loop', node('story-bridge-per-unit~fanout~0', 'ITEM = NTAPP-output/.work/slice-units/01_MPF-01'), ctx(r));
  delete process.env.NTAPP_AGY_NO_HOOKS;
  expect('NTAPP_AGY_NO_HOOKS=1 → never blocks', out.blocked, false);
}

console.log(`\n${FAIL === 0 ? 'ALL PASS' : 'FAILURES'}: ${PASS} passed, ${FAIL} failed`);
process.exit(FAIL === 0 ? 0 : 1);
