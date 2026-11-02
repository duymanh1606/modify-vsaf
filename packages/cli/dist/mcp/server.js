"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.VSAFEngine = void 0;
exports.execCommand = execCommand;
exports.startMCPServer = startMCPServer;
const fs_1 = require("fs");
const path_1 = require("path");
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const core_1 = require("@vsaf/core");
const index_js_2 = require("../telemetry/index.js");
const drift_glue_js_1 = require("./drift-glue.js");
/**
 * Load a single command outside any workflow run: the merged prompt is the
 * skill body plus the project-context overlay from .vsaf/commands/<name>.md —
 * the same composition loadCommand does for `command:` DAG nodes. There is no
 * run/workspace here, so $ARTIFACTS_DIR resolves to empty.
 */
function execCommand(params) {
    const command = (0, core_1.loadCommand)(params.name, params.projectPath);
    const config = (0, core_1.loadConfig)(params.projectPath);
    const prompt = (0, core_1.buildPrompt)(command.body, {
        ARGUMENTS: params.args ?? '',
        ARTIFACTS_DIR: '',
        config: { test_command: config.test_command },
        nodes: {},
    });
    return { name: command.name, description: command.description, prompt };
}
class VSAFEngine {
    executors = new Map();
    workspaces = new Map();
    runMeta = new Map();
    runStores = new Map();
    failedRuns = new Set();
    telemetries = new Map();
    async start(params) {
        const config = (0, core_1.loadConfig)(params.projectPath);
        const workflowPath = (0, path_1.join)(params.projectPath, '.vsaf', 'workflows', `${params.workflow}.yaml`);
        if (!(0, fs_1.existsSync)(workflowPath)) {
            throw new Error(`Workflow not found: "${params.workflow}" (expected at ${workflowPath})`);
        }
        const yamlContent = (0, fs_1.readFileSync)(workflowPath, 'utf-8');
        const graph = (0, core_1.parseWorkflow)(yamlContent);
        const wsManager = new core_1.WorkspaceManager({ exclude: config.isolation.exclude });
        const ws = await (0, core_1.resolveWorkspace)(config, params.projectPath, params.workflow, wsManager);
        const storeDir = (0, path_1.join)(params.projectPath, '.vsaf', 'storage');
        const runStore = new core_1.RunStore(storeDir);
        const run = runStore.create(params.workflow, params.args, ws.sourcePath, ws.artifactsPath, params.projectPath);
        const telemetry = (0, index_js_2.createTelemetry)(config, params.projectPath);
        telemetry.tracer.startRun({
            runId: run.runId,
            workflow: params.workflow,
            args: params.args,
            claudeSessionId: telemetry.claudeSessionId,
            userId: telemetry.userId,
        }, graph);
        this.telemetries.set(run.runId, telemetry);
        const finalCallbacks = this.buildRunCallbacks(run.runId, runStore, graph, telemetry, params.projectPath);
        const executor = new core_1.DAGExecutor(ws.sourcePath, params.projectPath, graph, finalCallbacks, {
            configVars: { test_command: config.test_command },
        });
        this.executors.set(run.runId, executor);
        this.workspaces.set(run.runId, { manager: wsManager, wsId: ws.id, sourcePath: ws.sourcePath });
        this.runMeta.set(run.runId, { workflow: params.workflow, projectPath: params.projectPath });
        this.runStores.set(run.runId, runStore);
        const step = await executor.step({ args: params.args, artifactsDir: ws.artifactsPath });
        if (step.type === 'done') {
            await this.finishRun(run.runId);
        }
        else if (step.type === 'failed') {
            await this.stopRun(run.runId, step);
        }
        // workspacePath/projectPath: thêm mới (additive) để client điều khiển qua
        // MCP biết nơi ghi code, không còn phải tự đọc state.json (bug B).
        return { runId: run.runId, step, workspacePath: ws.sourcePath, projectPath: params.projectPath };
    }
    /**
     * Continue a run the engine no longer holds — after a restart, or after a HITL gate
     * stopped it. Handing back no results is what makes it a resume: nothing new is
     * reported, the run is rebuilt from disk and simply asked what comes next.
     */
    async resume(params) {
        return this.next({ runId: params.runId, results: [], projectPath: params.projectPath });
    }
    async next(params) {
        const executor = this.executors.get(params.runId) ?? (await this.rehydrate(params.runId, params.projectPath));
        const runStore = this.runStores.get(params.runId);
        const meta = this.runMeta.get(params.runId);
        // Chụp lại trước khi finishRun/cleanupRun xoá entry khỏi this.workspaces.
        const workspacePath = this.workspaces.get(params.runId)?.sourcePath ?? meta.projectPath;
        const step = await executor.step({
            completedResults: params.results.map(r => ({
                nodeId: r.nodeId,
                output: r.output,
                structuredOutput: r.structuredOutput,
            })),
        });
        if (step.type === 'done') {
            await this.finishRun(params.runId);
        }
        else if (step.type === 'failed') {
            await this.stopRun(params.runId, step);
        }
        return { step, workspacePath, projectPath: meta.projectPath };
    }
    status(params) {
        const meta = this.runMeta.get(params.runId);
        if (!meta)
            throw new Error(`Run not found: ${params.runId}`);
        const hasExecutor = this.executors.has(params.runId);
        let status;
        if (hasExecutor) {
            status = 'running';
        }
        else if (this.failedRuns.has(params.runId)) {
            status = 'failed';
        }
        else {
            status = 'completed';
        }
        return {
            runId: params.runId,
            workflow: meta.workflow,
            status,
        };
    }
    /**
     * Persistence + telemetry wiring shared by start and rehydrate. Per AI node,
     * MCP-mode enrichment collects output metrics (file/LOC deltas in the
     * project dir, where Claude writes). Metrics attach before nodeComplete —
     * the span closes there, and attributes only land on an open span.
     * Concurrent fresh-context nodes write to the same project dir, so their
     * file/LOC deltas can cross-attribute; these metrics are per-node
     * accurate only for serial execution.
     *
     * For the drift-check command node (content === 'sdlc-drift-check'),
     * maybeAttachDrift reads .vsaf/telemetry/drift.json (written by the
     * sdlc-drift-check skill) and attaches drift scores to the same still-open
     * span, right before nodeComplete closes it.
     */
    buildRunCallbacks(runId, runStore, graph, telemetry, projectPath) {
        const callbacks = {
            onNodeStart: (nodeId) => {
                runStore.updateNode(runId, nodeId, { status: 'running', startedAt: new Date().toISOString() });
                runStore.save(runId);
            },
            onNodeComplete: (nodeId, result) => {
                runStore.updateNode(runId, nodeId, result);
                runStore.save(runId);
            },
            onNodeSkip: (nodeId) => {
                runStore.updateNode(runId, nodeId, { status: 'skipped' });
                runStore.save(runId);
            },
            onNodeFail: (nodeId, error) => {
                runStore.updateNode(runId, nodeId, { status: 'failed', error });
                runStore.save(runId);
            },
        };
        const tracedCallbacks = (0, index_js_2.withTelemetry)(callbacks, telemetry.tracer);
        const isAiNode = (nodeId) => graph.nodes.get(nodeId)?.type !== 'bash';
        const isDriftNode = (nodeId) => {
            const n = graph.nodes.get(nodeId);
            return n?.type === 'command' && n.content === 'sdlc-drift-check';
        };
        // Drift scores and output metrics both have to land while the node's span is still
        // open, so each wraps the decoration that ends it.
        const withDrift = {
            ...tracedCallbacks,
            onNodeComplete: (nodeId, result) => {
                (0, drift_glue_js_1.maybeAttachDrift)(telemetry.tracer, projectPath, nodeId, isDriftNode(nodeId));
                tracedCallbacks.onNodeComplete(nodeId, result);
            },
        };
        return (0, index_js_2.withOutputMetrics)(withDrift, telemetry.tracer, telemetry.outputMetrics, isAiNode);
    }
    /**
     * Rebuild a run lost with a previous engine process from its persisted
     * state.json (see README "Resume Failed Runs"). The rebuilt executor never
     * re-runs terminal nodes; the rehydrated run gets a fresh trace marked
     * vsaf.run.resumed, linked to the original trace via vsaf.run.id.
     */
    async rehydrate(runId, projectPath) {
        if (!projectPath) {
            throw new Error(`Run not found: ${runId}. If the engine restarted since vsaf_start, pass projectPath to resume from persisted state.`);
        }
        const runStore = new core_1.RunStore((0, path_1.join)(projectPath, '.vsaf', 'storage'));
        const run = runStore.load(runId);
        if (!run) {
            throw new Error(`Run not found: ${runId} — no persisted state in ${projectPath}. Start a new run.`);
        }
        // A run that stopped at a HITL gate is persisted as `failed`, because the gate exits
        // non-zero on purpose until a human signs. Refusing to rehydrate it made the one
        // command NTAPP documents for that moment — `/NTAPP-vsaf-resume` — impossible, and
        // the workaround (start the workflow again) skips every node whose artifact already
        // exists, so the real work is filed under a run marked `failed` and the run that
        // "succeeded" recorded nothing. `completed` still refuses: there is nothing to do.
        if (run.status === 'completed') {
            throw new Error(`Run ${runId} already completed — start a new run.`);
        }
        const config = (0, core_1.loadConfig)(projectPath);
        const workflowPath = (0, path_1.join)(projectPath, '.vsaf', 'workflows', `${run.workflow}.yaml`);
        if (!(0, fs_1.existsSync)(workflowPath)) {
            throw new Error(`Workflow not found: "${run.workflow}" (expected at ${workflowPath})`);
        }
        const graph = (0, core_1.parseWorkflow)((0, fs_1.readFileSync)(workflowPath, 'utf-8'));
        const wsManager = new core_1.WorkspaceManager({ exclude: config.isolation.exclude });
        // Reattach to the workspace the run was using; make a fresh one if it is gone. A run
        // that stopped at a gate had its workspace destroyed by the failure cleanup, and
        // refusing to resume over that is refusing for the wrong reason: the nodes already
        // completed do not need a workspace, and the ones still to run are content with a new
        // one. (Every NTAPP node declares `workspace: false` and works in the project dir, so
        // there is nothing in the old worktree to lose.)
        let ws;
        try {
            ws = wsManager.reattach({
                workflow: run.workflow,
                workspacePath: run.workspacePath,
                artifactsPath: run.artifactsPath,
                projectPath,
            });
        }
        catch {
            ws = await (0, core_1.resolveWorkspace)(config, projectPath, run.workflow, wsManager);
            run.workspacePath = ws.sourcePath;
            run.artifactsPath = ws.artifactsPath;
            runStore.save(runId);
        }
        const telemetry = (0, index_js_2.createTelemetry)(config, projectPath);
        telemetry.tracer.startRun({
            runId,
            workflow: run.workflow,
            args: run.args,
            claudeSessionId: telemetry.claudeSessionId,
            userId: telemetry.userId,
            resumed: true,
        }, graph);
        this.telemetries.set(runId, telemetry);
        const executor = new core_1.DAGExecutor(run.workspacePath, projectPath, graph, this.buildRunCallbacks(runId, runStore, graph, telemetry, projectPath), { configVars: { test_command: config.test_command } });
        executor.restore({ args: run.args, artifactsDir: run.artifactsPath, nodes: run.nodes }, { retryFailed: run.status === 'failed' || run.status === 'paused' });
        // The store still says `failed`; the run is live again, and its own callbacks own the
        // next verdict. Left as it was, a second resume would read a stale terminal state.
        if (run.status === 'failed' || run.status === 'paused') {
            this.failedRuns.delete(runId);
            runStore.resume(runId);
        }
        this.executors.set(runId, executor);
        this.workspaces.set(runId, { manager: wsManager, wsId: ws.id, sourcePath: ws.sourcePath });
        this.runMeta.set(runId, { workflow: run.workflow, projectPath });
        this.runStores.set(runId, runStore);
        return executor;
    }
    async finalizeTelemetry(runId, success, error, outcome) {
        const telemetry = this.telemetries.get(runId);
        this.telemetries.delete(runId);
        if (!telemetry)
            return;
        await telemetry.tracer.endRun(success, error, outcome);
    }
    /**
     * End a run that stopped. A pause is recorded as such and keeps its workspace: the human
     * signs, `vsaf_resume` picks the run back up, and the gate runs again. Tearing the
     * workspace down on a pause is what forced resume to rebuild one.
     */
    async stopRun(runId, step) {
        const runStore = this.runStores.get(runId);
        if (step.paused) {
            runStore?.pause(runId);
            await this.finalizeTelemetry(runId, false, step.error, 'paused');
            this.executors.delete(runId);
            return;
        }
        runStore?.fail(runId);
        await this.cleanupRun(runId, step.error);
    }
    async cleanupRun(runId, error) {
        this.failedRuns.add(runId);
        await this.finalizeTelemetry(runId, false, error);
        const wsInfo = this.workspaces.get(runId);
        if (wsInfo) {
            try {
                await wsInfo.manager.destroy(wsInfo.wsId);
            }
            catch { /* workspace cleanup is best-effort */ }
        }
        this.executors.delete(runId);
        this.workspaces.delete(runId);
        this.runStores.delete(runId);
    }
    async finishRun(runId) {
        const runStore = this.runStores.get(runId);
        if (runStore)
            runStore.complete(runId);
        await this.finalizeTelemetry(runId, true);
        const wsInfo = this.workspaces.get(runId);
        if (wsInfo) {
            try {
                await wsInfo.manager.applyChanges(wsInfo.wsId);
                await wsInfo.manager.destroy(wsInfo.wsId);
            }
            catch { /* workspace cleanup is best-effort */ }
        }
        this.executors.delete(runId);
        this.workspaces.delete(runId);
        this.runStores.delete(runId);
    }
}
exports.VSAFEngine = VSAFEngine;
async function startMCPServer() {
    const engine = new VSAFEngine();
    const server = new index_js_1.Server({ name: 'vsaf', version: '0.2.0' }, { capabilities: { tools: {} } });
    server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => ({
        tools: [
            {
                name: 'vsaf_start',
                description: 'Start a VSAF DAG workflow. Returns first step (bash results + AI nodes to execute), ' +
                    'plus workspacePath (the effective source directory to write code into — equals ' +
                    'projectPath when isolation.type: none) and projectPath. ' +
                    'Each AI node has a "context" field: "fresh" means you MUST run it in a spawned subagent ' +
                    '(Task tool, pass the node prompt verbatim and its model) and report the subagent final ' +
                    'message as the node output; append a closing line to the subagent prompt asking it to ' +
                    'finish with a short summary of what it produced, since that final message becomes the ' +
                    'node output; "inherit" means run it inline in this session. Spawn ' +
                    'concurrently when multiple fresh nodes are returned together.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        workflow: { type: 'string', description: 'Workflow name (e.g. sdlc/master-sdlc)' },
                        args: { type: 'string', description: 'Arguments passed to workflow' },
                        projectPath: { type: 'string', description: 'Project root path' },
                    },
                    required: ['workflow', 'args', 'projectPath'],
                },
            },
            {
                name: 'vsaf_next',
                description: 'Report AI node results and advance the workflow to the next step. Returns the next ' +
                    'step plus workspacePath and projectPath (same meaning as in vsaf_start), so you never ' +
                    'need to read .vsaf/storage/<runId>/state.json manually to find where to write code. ' +
                    'Returned AI nodes follow the same "context" rule as vsaf_start ("fresh" = run in ' +
                    'spawned subagent, "inherit" = run inline). If the engine restarted since vsaf_start ' +
                    '(e.g. resumed session), pass projectPath to rehydrate the run from persisted state.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        runId: { type: 'string', description: 'Run ID from vsaf_start' },
                        projectPath: {
                            type: 'string',
                            description: 'Project root path — only needed to resume a run after an engine restart',
                        },
                        results: {
                            type: 'array',
                            items: {
                                type: 'object',
                                properties: {
                                    nodeId: { type: 'string' },
                                    output: { type: 'string' },
                                    structuredOutput: {
                                        type: 'object',
                                        description: 'When the node declares output_format: the JSON object extracted from the ' +
                                            'node answer, matching that schema. Enables when-conditions and ' +
                                            '$node.output.<field> resolution downstream.',
                                    },
                                },
                                required: ['nodeId', 'output'],
                            },
                            description: 'Completed AI node results',
                        },
                    },
                    required: ['runId', 'results'],
                },
            },
            {
                name: 'vsaf_resume',
                description: 'Resume a run that was interrupted or stopped at a HITL gate, after the human ' +
                    'signed the artifact the gate checks. Rebuilds the run from .vsaf/storage and ' +
                    're-runs the gate; nodes already completed are never repeated. Returns the next ' +
                    'step, same shape as vsaf_next.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        runId: { type: 'string', description: 'Run ID to resume' },
                        projectPath: { type: 'string', description: 'Project root path' },
                    },
                    required: ['runId', 'projectPath'],
                },
            },
            {
                name: 'vsaf_status',
                description: 'Get current run status and progress.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        runId: { type: 'string', description: 'Run ID' },
                    },
                    required: ['runId'],
                },
            },
            {
                name: 'vsaf_command',
                description: 'Load a single VSAF command (skill + project-context overlay from .vsaf/commands/) and return the merged prompt to execute. Use for running one phase outside a workflow.',
                inputSchema: {
                    type: 'object',
                    properties: {
                        name: { type: 'string', description: 'Command name (a .md file in .vsaf/commands/, e.g. sdlc-discovery)' },
                        args: { type: 'string', description: 'Arguments resolved into $ARGUMENTS' },
                        projectPath: { type: 'string', description: 'Project root path' },
                    },
                    required: ['name', 'projectPath'],
                },
            },
        ],
    }));
    server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
        const args = request.params.arguments;
        try {
            switch (request.params.name) {
                case 'vsaf_start': {
                    const result = await engine.start(args);
                    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                }
                case 'vsaf_next': {
                    const result = await engine.next(args);
                    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                }
                case 'vsaf_resume': {
                    const result = await engine.resume(args);
                    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                }
                case 'vsaf_status': {
                    const result = engine.status(args);
                    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                }
                case 'vsaf_command': {
                    const result = execCommand(args);
                    return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
                }
                default:
                    throw new Error(`Unknown tool: ${request.params.name}`);
            }
        }
        catch (error) {
            return {
                content: [{ type: 'text', text: `Error: ${error.message}` }],
                isError: true,
            };
        }
    });
    const transport = new stdio_js_1.StdioServerTransport();
    await server.connect(transport);
}
//# sourceMappingURL=server.js.map