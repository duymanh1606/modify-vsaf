"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ExecutionManager = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const core_1 = require("@vsaf/core");
const index_js_1 = require("../../telemetry/index.js");
class ExecutionManager {
    projectPath;
    sseManager;
    activeRuns = new Set();
    constructor(projectPath, sseManager) {
        this.projectPath = projectPath;
        this.sseManager = sseManager;
    }
    async startRun(workflowName, args) {
        const config = (0, core_1.loadConfig)(this.projectPath);
        const workflowPath = (0, path_1.join)(this.projectPath, '.vsaf', 'workflows', `${workflowName}.yaml`);
        if (!(0, fs_1.existsSync)(workflowPath)) {
            throw new Error(`Workflow not found: "${workflowName}"`);
        }
        const yamlContent = (0, fs_1.readFileSync)(workflowPath, 'utf-8');
        const graph = (0, core_1.parseWorkflow)(yamlContent);
        const wsManager = new core_1.WorkspaceManager({ exclude: config.isolation.exclude });
        const ws = await (0, core_1.resolveWorkspace)(config, this.projectPath, workflowName, wsManager);
        const storeDir = (0, path_1.join)(this.projectPath, '.vsaf', 'storage');
        const runStore = new core_1.RunStore(storeDir);
        const run = runStore.create(workflowName, args, ws.sourcePath, ws.artifactsPath, this.projectPath);
        this.activeRuns.add(run.runId);
        const telemetry = (0, index_js_1.createTelemetry)(config, this.projectPath);
        telemetry.tracer.startRun({ runId: run.runId, workflow: workflowName, args, userId: telemetry.userId }, graph);
        const callbacks = {
            onNodeStart: (nodeId) => {
                runStore.updateNode(run.runId, nodeId, { status: 'running', startedAt: new Date().toISOString() });
                runStore.save(run.runId);
                this.sseManager.pushEvent(run.runId, 'node:start', { nodeId, timestamp: new Date().toISOString() });
            },
            onNodeComplete: (nodeId, result) => {
                runStore.updateNode(run.runId, nodeId, result);
                runStore.save(run.runId);
                this.sseManager.pushEvent(run.runId, 'node:complete', {
                    nodeId,
                    durationMs: result.durationMs,
                    output: result.output?.substring(0, 200),
                });
            },
            onNodeSkip: (nodeId, reason) => {
                runStore.updateNode(run.runId, nodeId, { status: 'skipped' });
                runStore.save(run.runId);
                this.sseManager.pushEvent(run.runId, 'node:skip', { nodeId, reason });
            },
            onNodeFail: (nodeId, error) => {
                runStore.updateNode(run.runId, nodeId, { status: 'failed', error });
                runStore.save(run.runId);
                this.sseManager.pushEvent(run.runId, 'node:fail', { nodeId, error });
            },
        };
        const executor = new core_1.DAGExecutor(ws.sourcePath, this.projectPath, graph, (0, index_js_1.withTelemetry)(callbacks, telemetry.tracer), {
            configVars: { test_command: config.test_command },
        });
        const step = await executor.step({ args, artifactsDir: ws.artifactsPath });
        // endRun is the only place the span exporter is flushed, so it has to survive a
        // throwing workspace teardown — otherwise the whole trace is dropped silently.
        // Same reason as the CLI run path.
        if (step.type === 'done') {
            try {
                const diff = await wsManager.diff(ws.id);
                if (diff.modified.length > 0 || diff.added.length > 0) {
                    await wsManager.applyChanges(ws.id);
                }
                runStore.complete(run.runId);
                await wsManager.destroy(ws.id);
                this.sseManager.pushEvent(run.runId, 'run:complete', { success: true });
            }
            finally {
                await telemetry.tracer.endRun(true);
            }
        }
        else if (step.type === 'failed') {
            runStore.fail(run.runId);
            this.sseManager.pushEvent(run.runId, 'run:complete', { success: false, error: step.error });
            await telemetry.tracer.endRun(false, step.error);
        }
        this.activeRuns.delete(run.runId);
        return { runId: run.runId, step };
    }
    isActive(runId) {
        return this.activeRuns.has(runId);
    }
}
exports.ExecutionManager = ExecutionManager;
//# sourceMappingURL=execution-manager.js.map