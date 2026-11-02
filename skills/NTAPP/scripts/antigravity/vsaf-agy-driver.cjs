#!/usr/bin/env node
/**
 * vsaf-agy-driver — PoC: drive a VSAF DAG workflow deterministically through
 * Antigravity CLI (`agy -p`) instead of Claude Code.
 *
 * WHY: VSAF's engine is a host-agnostic DAG orchestrator. Today the step loop
 * (vsaf_start/vsaf_next + the NTAPP-vsaf-run glue skill) is driven by an LLM
 * reading a markdown protocol — that is the consistency-weak link. This driver
 * replaces that LLM loop with CODE: it imports @vsaf/core, runs DAGExecutor.step()
 * in a plain JS loop, and executes each yielded AI node by shelling out to `agy -p`.
 * Orchestration becomes deterministic; only per-node content stays model-driven.
 *
 * Each AI node = one fresh `agy -p` process => a literal fresh context, which is
 * exactly what VSAF fanout sub-tasks want. The engine already caps fanout to
 * max_concurrency (it only yields <= mc sub-nodes per pass), so the driver just
 * runs whatever it is handed concurrently.
 *
 * This is ADDITIVE — it does not touch the Claude path (/NTAPP-vsaf-run MCP glue).
 * Hybrid mode: Claude primary, this driver as the Antigravity fallback host.
 *
 * Usage:
 *   node scripts/antigravity/vsaf-agy-driver.cjs NTAPP/ad-hoc-per-unit \
 *        --args "Thêm endpoint health-check cho service X" [--dry-run] [--json] [--yolo]
 *
 * Flags:
 *   --args "<s>"     workflow $ARGUMENTS (raw string)            (default "")
 *   --project <dir>  project root (has .vsaf/)                   (default cwd)
 *   --dry-run        do NOT call agy; stub each node's output    (default off)
 *   --agy <bin>      agy binary name/path                        (default "agy")
 *   --model <m>      model passed to agy (--model)               (default: map from .vsaf/config.yaml)
 *   --print-timeout  agy --print-timeout per node                (default 15m; agy default is 5m)
 *   --yolo           pass --dangerously-skip-permissions to agy  (default off)
 *   --max-parallel N hard cap on concurrent agy processes        (default 5)
 *   --no-hooks       disable the node-boundary hook layer         (default: hooks ON)
 *
 * Hooks: the 8 gate hooks the two workflows reference (3,4,5,5b,6,7,8,10) fire at node
 * boundaries via scripts/antigravity/hooks/run-hooks.cjs (reusing hooks/*.sh verbatim);
 * a blocking gate halts the run. Hook 9 (build_loop, per-edit) runs as a post-node sweep
 * here and ALSO as an agy-native PostToolUse hook (scripts/antigravity/hooks/agy-posttool-shim.cjs).
 * Disable: --no-hooks | NTAPP_AGY_NO_HOOKS=1 | DISABLE_HOOK_<NAME>=1 | DISABLE_HOOKS_ALL=1.
 *
 * Flags verified against agy 1.0.14 (`agy --help` / `agy models`). agy 1.0.14 has
 * NO --output-format flag — print mode emits PLAIN TEXT on stdout, so this driver
 * never sets structuredOutput. Neither slice-loop nor ad-hoc-per-unit declares an
 * `outputFormat` contract, so that is fine for the two target workflows.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn, execSync } = require('child_process');
const HOOKS = require('./hooks/run-hooks.cjs'); // node-boundary hook enforcement (Claude event-hook port)

const firstLine = (s) => String(s || '').split('\n')[0];

// ---- locate @vsaf/core (published under @ngocsangairvds/vsaf) ----
function resolveCore() {
  const cands = [];
  if (process.env.VSAF_CORE) cands.push(process.env.VSAF_CORE);
  try {
    const r = execSync('npm root -g', { encoding: 'utf8' }).trim();
    cands.push(path.join(r, '@ngocsangairvds/vsaf/packages/core/dist/index.js'));
  } catch { /* npm not on PATH */ }
  cands.push(path.join(os.homedir(), '.npm-global/lib/node_modules/@ngocsangairvds/vsaf/packages/core/dist/index.js'));
  for (const c of cands) { if (c && fs.existsSync(c)) return require(c); }
  throw new Error('Cannot locate @vsaf/core. Set VSAF_CORE=/abs/path/to/packages/core/dist/index.js');
}

// ---- arg parsing ----
function parseArgv(argv) {
  const o = { workflow: null, args: '', project: process.cwd(), dryRun: false,
              agy: 'agy', model: null, printTimeout: '15m', yolo: false, maxParallel: 5,
              noHooks: false };
  const rest = argv.slice(2);
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (a === '--args') o.args = rest[++i] ?? '';
    else if (a === '--project') o.project = path.resolve(rest[++i]);
    else if (a === '--dry-run') o.dryRun = true;
    else if (a === '--agy') o.agy = rest[++i];
    else if (a === '--model') o.model = rest[++i];
    else if (a === '--print-timeout') o.printTimeout = rest[++i];
    else if (a === '--yolo') o.yolo = true;
    else if (a === '--no-hooks') o.noHooks = true;
    else if (a === '--max-parallel') o.maxParallel = Number(rest[++i]);
    else if (!a.startsWith('--') && !o.workflow) o.workflow = a;
    else if (!a.startsWith('--')) o.args = o.args ? `${o.args} ${a}` : a; // first bare token after wf = args
  }
  if (!o.workflow) { console.error('ERROR: workflow name required, e.g. NTAPP/ad-hoc-per-unit'); process.exit(2); }
  return o;
}

// .vsaf/config.yaml model id -> real agy model display name (from `agy models`, agy 1.0.14).
// Goal = no Claude -> map to Gemini tiers. Override per-run with --model.
const MODEL_MAP = {
  opus:   'Gemini 3.1 Pro (High)',   // design-heavy stages (HLD, feature-design, ux)
  sonnet: 'Gemini 3.1 Pro (Low)',
  haiku:  'Gemini 3.5 Flash (Low)',
};
function resolveModel(opts, cfg) {
  if (opts.model) return opts.model;
  return MODEL_MAP[cfg.model] || cfg.model || null;
}

// agy flag spelling — verified against agy 1.0.14 (`agy --help`).
function buildAgyArgs(prompt, { model, printTimeout, yolo }) {
  const args = ['-p', prompt];                                   // -p/--print: single non-interactive prompt
  if (model) args.push('--model', model);                        // e.g. "Gemini 3.1 Pro (High)"
  if (printTimeout) args.push('--print-timeout', printTimeout);  // agy default 5m; raise for dev/review nodes
  if (yolo) args.push('--dangerously-skip-permissions');
  return args;
}

function runAgy(agyBin, prompt, cwd, flags) {
  return new Promise((resolve, reject) => {
    // stdin -> 'ignore' (/dev/null = immediate EOF). With the default pipe, agy print
    // mode blocks reading an stdin pipe that never closes, hanging until --print-timeout.
    const child = spawn(agyBin, buildAgyArgs(prompt, flags), { cwd, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '', err = '';
    child.stdout.on('data', d => out += d);
    child.stderr.on('data', d => err += d);
    child.on('error', reject); // e.g. ENOENT if agy not installed
    child.on('close', code => {
      if (code !== 0) return reject(new Error(`agy exited ${code}: ${(err || out).slice(0, 2000)}`));
      resolve({ output: out.trim() || '[agy: empty output]', structuredOutput: undefined });
    });
  });
}

// Execute one yielded AI node. Returns { nodeId, output, structuredOutput, _hookBlock? }.
// Hooks fire at the node boundary (the Claude event-hook port): pre = UserPromptSubmit
// gates (block BEFORE the agy call), post = SubagentStop verify + PostToolUse sweep.
async function runNode(node, opts, model) {
  const cwd = opts.project; // both target workflows use workspace:false -> run at project root
  const hookCtx = { hooksDir: opts._hooksDir, project: opts.project, cwd };

  if (opts.dryRun) {
    const plan = HOOKS.planForNode(opts._wfName, node.nodeId);
    const hk = [...plan.pre.map(h => `pre:${h}`), ...plan.post.map(h => `post:${h}`)];
    console.log(`   ╰─ [dry-run] ${node.nodeId}${node.skill ? ` (skill: ${node.skill})` : ''} — prompt ${node.prompt.length} chars`
      + (hk.length ? `\n        │ hooks → ${hk.join(', ')}` : '\n        │ hooks → (none)'));
    return { nodeId: node.nodeId, output: `[dry-run] node ${node.nodeId} executed (no agy call)`, structuredOutput: undefined };
  }

  // PRE — UserPromptSubmit gates. Block before spending an agy call.
  const pre = HOOKS.runPreHooks(opts._wfName, node, hookCtx);
  for (const w of pre.warns) console.error(`   ⚠ pre-hook ${w.hook} @ ${node.nodeId}: ${firstLine(w.message)}`);
  if (pre.blocked) {
    return { nodeId: node.nodeId, output: '[pre-hook blocked]', structuredOutput: undefined,
             _hookBlock: { phase: 'pre', nodeId: node.nodeId, blocks: pre.blocks } };
  }

  const res = await runAgy(opts.agy, node.prompt, cwd, { model: node.model || model, printTimeout: opts.printTimeout, yolo: opts.yolo });

  // POST — SubagentStop verify gates + PostToolUse build_loop sweep.
  const post = HOOKS.runPostHooks(opts._wfName, node, hookCtx);
  for (const w of post.warns) console.error(`   ⚠ post-hook ${w.hook} @ ${node.nodeId}: ${firstLine(w.message)}`);
  if (post.blocked) {
    return { nodeId: node.nodeId, output: res.output, structuredOutput: res.structuredOutput,
             _hookBlock: { phase: 'post', nodeId: node.nodeId, blocks: post.blocks } };
  }
  return { nodeId: node.nodeId, output: res.output, structuredOutput: res.structuredOutput };
}

// bounded concurrency over a list of async thunks
async function pool(items, limit, fn) {
  const results = new Array(items.length);
  let cursor = 0;
  const worker = async () => {
    while (cursor < items.length) {
      const i = cursor++;
      results[i] = await fn(items[i], i);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length || 1) }, worker));
  return results;
}

async function main() {
  const opts = parseArgv(process.argv);
  const core = resolveCore();

  const wfPath = path.join(opts.project, '.vsaf', 'workflows', `${opts.workflow}.yaml`);
  if (!fs.existsSync(wfPath)) { console.error(`ERROR: workflow not found: ${wfPath}`); process.exit(2); }
  const graph = core.parseWorkflow(fs.readFileSync(wfPath, 'utf-8'));
  const cfg = core.loadConfig(opts.project);
  const model = resolveModel(opts, cfg);

  // Hook layer (Claude event-hook port). Keyed by workflow basename (strip NTAPP/ prefix).
  if (opts.noHooks) process.env.NTAPP_AGY_NO_HOOKS = '1';
  opts._wfName = path.basename(opts.workflow);
  opts._hooksDir = HOOKS.hooksDisabled() ? null : HOOKS.resolveHooksDir(opts.project);
  const hooksState = HOOKS.hooksDisabled() ? 'OFF (--no-hooks)'
    : opts._hooksDir ? `ON (${path.relative(opts.project, opts._hooksDir) || opts._hooksDir})`
    : 'OFF (no hooks/ dir found)';

  const artifactsDir = fs.mkdtempSync(path.join(os.tmpdir(), 'vsaf-agy-'));
  const callbacks = {
    onNodeStart: id => console.log(`▶ start   ${id}`),
    onNodeComplete: (id, r) => console.log(`✓ done    ${id} (${r.durationMs ?? 0}ms)`),
    onNodeSkip: (id, why) => console.log(`↷ skip    ${id} — ${why}`),
    onNodeFail: (id, e) => console.log(`✗ FAIL    ${id} — ${e}`),
  };

  console.log(`\n[agy-driver] workflow=${opts.workflow} args="${opts.args}" provider=antigravity model=${model || '(agy default)'} mode=${opts.dryRun ? 'DRY-RUN' : 'LIVE'}`);
  console.log(`[agy-driver] engine=@vsaf/core nodes=${graph.nodes.size} hooks=${hooksState}\n`);

  const ex = new core.DAGExecutor(opts.project, opts.project, graph, callbacks);
  let res = await ex.step({ args: opts.args, artifactsDir });

  while (res.type === 'needs_ai') {
    if (res.nodes.length === 0) { // in-flight wait — nothing to do without async; advance
      res = await ex.step({}); continue;
    }
    console.log(`\n[agy-driver] executing ${res.nodes.length} AI node(s): ${res.nodes.map(n => n.nodeId).join(', ')}`);
    const completedResults = await pool(res.nodes, opts.maxParallel, n => runNode(n, opts, model));

    // A blocking hook (gate) halts the whole workflow — the only place with the full-DAG
    // view. Re-run after fixing: idempotent nodes skip, so it resumes where it stopped.
    const blocked = completedResults.filter(r => r._hookBlock);
    if (blocked.length) {
      console.error(`\n[agy-driver] ⛔ HOOK BLOCK — workflow halted:`);
      for (const b of blocked) {
        for (const blk of b._hookBlock.blocks) {
          console.error(`  ✗ ${b._hookBlock.phase}-hook ${blk.hook} @ ${b._hookBlock.nodeId}`);
          console.error(String(blk.message).split('\n').map(l => `      ${l}`).join('\n'));
        }
      }
      console.error(`\n[agy-driver] Fix the above, then re-run (idempotent nodes skip). Bypass: --no-hooks or DISABLE_HOOK_<NAME>=1.`);
      process.exit(1);
    }
    res = await ex.step({ completedResults });
  }

  console.log(`\n[agy-driver] FINISHED: ${res.type}`);
  if (res.type === 'failed') { console.error(`[agy-driver] error: ${res.error}`); process.exit(1); }
  process.exit(0);
}

main().catch(e => { console.error('[agy-driver] fatal:', e.message); process.exit(1); });
