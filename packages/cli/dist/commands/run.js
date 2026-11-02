"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.prepareRun = prepareRun;
exports.execRun = execRun;
const fs_1 = require("fs");
const path_1 = require("path");
const core_1 = require("@vsaf/core");
const progress_js_1 = require("../ui/progress.js");
const index_js_1 = require("../telemetry/index.js");
async function prepareRun(workflowName, projectPath, options) {
    const config = (0, core_1.loadConfig)(projectPath);
    const workflowPath = (0, path_1.join)(projectPath, '.vsaf', 'workflows', `${workflowName}.yaml`);
    if (!(0, fs_1.existsSync)(workflowPath)) {
        throw new Error(`Workflow not found: "${workflowName}" (expected at ${workflowPath})`);
    }
    const yamlContent = (0, fs_1.readFileSync)(workflowPath, 'utf-8');
    const graph = (0, core_1.parseWorkflow)(yamlContent);
    return { graph, config, args: options.args };
}
async function execRun(workflowName, projectPath, options) {
    const { graph, config, args } = await prepareRun(workflowName, projectPath, options);
    // Check for AI nodes — vsaf run only supports bash-only workflows
    const hasAINodes = [...graph.nodes.values()].some(n => n.type === 'prompt' || n.type === 'command');
    if (hasAINodes) {
        console.error('[vsaf] This workflow contains AI nodes. Use `/vsaf ' + workflowName + '` inside Claude instead.');
        process.exit(1);
    }
    console.log(`[vsaf] Loading config from .vsaf/config.yaml`);
    console.log(`[vsaf] Parsing workflow: ${workflowName}`);
    const wsManager = new core_1.WorkspaceManager({ exclude: config.isolation.exclude });
    const ws = await (0, core_1.resolveWorkspace)(config, projectPath, workflowName, wsManager);
    console.log(`[vsaf] Creating workspace: ${ws.sourcePath}`);
    const storeDir = (0, path_1.join)(projectPath, '.vsaf', 'storage');
    const runStore = new core_1.RunStore(storeDir);
    const run = runStore.create(workflowName, args, ws.sourcePath, ws.artifactsPath, projectPath);
    console.log(`[vsaf] Starting DAG execution (${graph.nodes.size} nodes)\n`);
    const startTime = Date.now();
    const telemetry = (0, index_js_1.createTelemetry)(config, projectPath);
    telemetry.tracer.startRun({ runId: run.runId, workflow: workflowName, args, userId: telemetry.userId }, graph);
    const callbacks = {
        onNodeStart: (nodeId) => {
            console.log((0, progress_js_1.formatNodeStatus)(nodeId, 'running'));
            runStore.updateNode(run.runId, nodeId, { status: 'running', startedAt: new Date().toISOString() });
            runStore.save(run.runId);
        },
        onNodeComplete: (nodeId, result) => {
            console.log((0, progress_js_1.formatNodeStatus)(nodeId, 'completed', result.durationMs));
            runStore.updateNode(run.runId, nodeId, result);
            runStore.save(run.runId);
        },
        onNodeSkip: (nodeId, _reason) => {
            console.log((0, progress_js_1.formatNodeStatus)(nodeId, 'skipped'));
            runStore.updateNode(run.runId, nodeId, { status: 'skipped' });
            runStore.save(run.runId);
        },
        onNodeFail: (nodeId, error) => {
            console.log((0, progress_js_1.formatNodeStatus)(nodeId, 'failed'));
            runStore.updateNode(run.runId, nodeId, { status: 'failed', error });
            runStore.save(run.runId);
        },
    };
    // Opt-in guard: two runs on one project would overwrite each other's state.
    const runLock = config.run_lock ? await (0, core_1.acquireRunLock)(projectPath, run.runId) : null;
    if (config.run_lock && !runLock) {
        console.error('[vsaf] Another run is already active on this project. Wait for it to finish, or set run_lock: false in .vsaf/config.yaml.');
        process.exit(1);
    }
    const executor = new core_1.DAGExecutor(ws.sourcePath, projectPath, graph, (0, index_js_1.withTelemetry)(callbacks, telemetry.tracer), {
        configVars: { test_command: config.test_command },
    });
    // Step loop — for bash-only workflows, this completes in one call
    let step = await executor.step({ args, artifactsDir: ws.artifactsPath });
    if (step.type === 'needs_ai') {
        // This shouldn't happen (we checked for AI nodes above), but just in case
        throw new Error('Unexpected AI node in bash-only workflow');
    }
    const totalMs = Date.now() - startTime;
    const success = step.type === 'done';
    console.log((0, progress_js_1.formatSummary)(success, totalMs));
    // Workspace teardown can throw — a `git branch -D` for a branch that was never
    // created is enough — and everything after it used to be skipped: the run lock
    // stayed held, and endRun, the ONLY place the span exporter is flushed, never
    // ran, so the whole trace was dropped with no error surfaced anywhere. Both now
    // happen whatever cleanup does.
    try {
        if (success) {
            const diff = await wsManager.diff(ws.id);
            if (diff.modified.length > 0 || diff.added.length > 0) {
                console.log('\n[vsaf] Changed files:');
                for (const f of diff.modified)
                    console.log(`  M ${f}`);
                for (const f of diff.added)
                    console.log(`  A ${f}`);
                await wsManager.applyChanges(ws.id);
                console.log('[vsaf] Changes applied to project.');
            }
            runStore.complete(run.runId);
            await wsManager.destroy(ws.id);
            console.log(`[vsaf] Workspace cleaned up`);
        }
        else if (step.paused) {
            // Stopped at a gate a person clears, not at a defect. Recorded as such so an
            // approval queue is not filed next to broken runs.
            runStore.pause(run.runId);
            console.log(`\n[vsaf] Run ID: ${run.runId}`);
            console.log(`[vsaf] Đang chờ chữ ký — ký xong resume bằng: vsaf_resume ${run.runId}`);
            console.log(`[vsaf] Workspace preserved at: ${ws.sourcePath}`);
        }
        else {
            runStore.fail(run.runId);
            console.log(`\n[vsaf] Run ID: ${run.runId}`);
            console.log(`[vsaf] Workspace preserved at: ${ws.sourcePath}`);
        }
    }
    finally {
        await runLock?.release();
        // Flush telemetry before the CLI process exits.
        await telemetry.tracer.endRun(success, step.type === 'failed' ? step.error : undefined, step.paused ? 'paused' : undefined);
    }
}
//# sourceMappingURL=run.js.map