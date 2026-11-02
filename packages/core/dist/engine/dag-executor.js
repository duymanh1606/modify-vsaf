"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DAGExecutor = exports.FANOUT_SEP = void 0;
const fs_1 = require("fs");
const node_runner_js_1 = require("./node-runner.js");
const condition_evaluator_js_1 = require("./condition-evaluator.js");
const contract_validator_js_1 = require("./contract-validator.js");
/**
 * Separates a fanout parent id from its sub-task index: `build~fanout~2`.
 * Chosen because `~` is not valid in an author-written node id, so a synthetic
 * sub-task id can never collide with a real node. Exported because run recovery
 * needs to recognise these ids — they exist only at runtime, never in the YAML.
 */
exports.FANOUT_SEP = '~fanout~';
class DAGExecutor {
    workspaceCwd;
    projectPath;
    graph;
    callbacks;
    pending;
    completed = new Set();
    failed = new Set();
    skipped = new Set();
    nodeResults = {};
    runner;
    args = '';
    artifactsDir = '/tmp';
    initialized = false;
    inputsValidated = false;
    retryCounts = new Map();
    /** Parent node id → expansion state. Empty for every workflow that declares no fanout. */
    fanoutState = new Map();
    delayFn;
    configVars;
    constructor(workspaceCwd, projectPath, graph, callbacks, options = {}) {
        this.workspaceCwd = workspaceCwd;
        this.projectPath = projectPath;
        this.graph = graph;
        this.callbacks = callbacks;
        this.runner = new node_runner_js_1.NodeRunner(workspaceCwd, projectPath);
        this.pending = new Set(graph.nodes.keys());
        this.delayFn = options.delayFn ?? ((ms) => new Promise(r => setTimeout(r, ms)));
        this.configVars = options.configVars;
    }
    // ── Fanout ────────────────────────────────────────────────────────────────
    // A fanout node runs once per file matched by its `over` glob. Sub-tasks carry
    // synthetic ids (`parent~fanout~N`); the parent stays pending until all of them
    // finish, then takes on their combined status.
    subId(parentId, index) {
        return `${parentId}${exports.FANOUT_SEP}${index}`;
    }
    /** Split a sub-task id back into its parts, or null if this is a plain node id. */
    parseSubId(id) {
        const at = id.lastIndexOf(exports.FANOUT_SEP);
        if (at === -1)
            return null;
        const index = Number(id.slice(at + exports.FANOUT_SEP.length));
        if (!Number.isInteger(index))
            return null;
        return { parent: id.slice(0, at), index };
    }
    /**
     * Expand a parent the first time it becomes ready. `over` is a glob resolved
     * against the same cwd the node itself would run in, so `workspace: false`
     * nodes glob the project rather than the throwaway workspace.
     */
    expandFanout(node) {
        const cwd = !node.workspace && this.projectPath ? this.projectPath : this.workspaceCwd;
        let items = [];
        try {
            items = (0, fs_1.globSync)(node.fanout.over, { cwd }).sort();
        }
        catch {
            items = [];
        }
        const state = {
            items,
            as: node.fanout.as,
            maxConcurrency: node.fanout.maxConcurrency,
            results: new Map(),
            inFlight: new Set(),
        };
        // Resume: a sub-task that already completed keeps its result and is not dispatched
        // again. Only completed ones — a failed sub-task is meant to be retried.
        for (let index = 0; index < items.length; index++) {
            const previous = this.nodeResults[this.subId(node.id, index)];
            if (previous?.status === 'completed')
                state.results.set(index, previous);
        }
        this.fanoutState.set(node.id, state);
        return state;
    }
    /** Variable context for one sub-task: its item under both ITEM and the `as` name. */
    fanoutContext(item, asName) {
        return { ...this.buildContext(), fanout: { ITEM: item, [asName]: item } };
    }
    /** True while any expanded parent still has sub-tasks left to finish. */
    fanoutBusy() {
        for (const [, state] of this.fanoutState) {
            if (state.results.size < state.items.length)
                return true;
        }
        return false;
    }
    /** Indices not yet started, capped so no parent exceeds its concurrency limit. */
    dispatchableSubTasks(parentId, state) {
        const room = Math.max(0, state.maxConcurrency - state.inFlight.size);
        const todo = [];
        for (let i = 0; i < state.items.length && todo.length < room; i++) {
            if (!state.results.has(i) && !state.inFlight.has(i))
                todo.push(i);
        }
        return todo;
    }
    /** Once every sub-task has answered, settle the parent as completed or failed. */
    settleFanoutParent(parentId, state) {
        if (state.results.size < state.items.length)
            return;
        const failures = [...state.results.values()].filter(r => r.status === 'failed');
        const result = failures.length
            ? {
                status: 'failed',
                error: `${failures.length}/${state.items.length} fanout sub-tasks failed`,
                durationMs: 0,
            }
            : {
                status: 'completed',
                output: [...state.results.values()].map(r => r.output ?? '').join('\n'),
                durationMs: 0,
                completedAt: new Date().toISOString(),
            };
        this.nodeResults[parentId] = result;
        this.pending.delete(parentId);
        if (result.status === 'failed') {
            this.failed.add(parentId);
            this.callbacks.onNodeFail(parentId, result.error);
        }
        else {
            this.completed.add(parentId);
            this.callbacks.onNodeComplete(parentId, result);
        }
    }
    /** Run every sub-task of a bash parent, honouring the concurrency limit. */
    async runBashFanout(node, state) {
        let next = 0;
        const worker = async () => {
            for (;;) {
                const index = next++;
                if (index >= state.items.length)
                    return;
                try {
                    const result = await this.runner.runBash(node, this.fanoutContext(state.items[index], state.as));
                    state.results.set(index, result);
                }
                catch (error) {
                    state.results.set(index, {
                        status: 'failed',
                        error: error instanceof Error ? error.message : String(error),
                        durationMs: 0,
                    });
                }
            }
        };
        const lanes = Math.min(state.items.length, Number.isFinite(state.maxConcurrency) ? state.maxConcurrency : state.items.length);
        await Promise.all(Array.from({ length: Math.max(lanes, 0) }, worker));
    }
    /**
     * Rehydrate a fresh executor from persisted run state (state.json) after an
     * engine restart. Terminal nodes are seeded so they never re-execute;
     * 'running' nodes stay pending — the next step() either absorbs their
     * result via completedResults or re-yields them. Inputs were already
     * validated on the original start, so validation is not repeated.
     */
    /**
     * `retryFailed` re-arms the nodes that failed instead of restoring them as terminal.
     *
     * A HITL gate fails on purpose: it exits non-zero until a human signs the artifact.
     * Restoring that node as terminal-failed leaves the run permanently stuck at the one
     * step the human has just cleared, so the only way forward was to start the workflow
     * over — which re-does nothing (every artifact already exists) and buries the real run
     * under an empty one. Completed nodes stay terminal either way: nothing already done
     * is repeated.
     */
    restore(state, options = {}) {
        this.args = state.args;
        this.artifactsDir = state.artifactsDir;
        this.initialized = true;
        this.inputsValidated = true;
        for (const [nodeId, result] of Object.entries(state.nodes)) {
            if (!this.graph.nodes.has(nodeId)) {
                // A fanout sub-task id (`parent~fanout~N`) is created at runtime, so it never
                // appears in the graph rebuilt from the YAML. Dropping it would make a resume
                // re-run work that already finished — for an AI fanout that means spending a
                // subagent again and overwriting the artifact it wrote. Keep the result for
                // `expandFanout` to re-absorb; the sub-id is not a pending node, so nothing
                // else needs to change. Anything else absent from the graph is still dropped.
                const sub = this.parseSubId(nodeId);
                if (sub && this.graph.nodes.has(sub.parent))
                    this.nodeResults[nodeId] = result;
                continue;
            }
            switch (result.status) {
                case 'completed':
                    this.completed.add(nodeId);
                    break;
                case 'failed':
                    if (options.retryFailed)
                        continue; // leave pending so the gate runs again
                    this.failed.add(nodeId);
                    break;
                case 'skipped':
                    // Everything downstream of the failed gate was skipped as a consequence, and a
                    // persisted skip does not say whether it came from that cascade or from a `when`
                    // condition — both are stored as a bare `skipped`. Re-arming all of them is the
                    // safe reading: a condition-skip re-evaluates to the same answer and skips
                    // again, while a cascade-skip gets the run it never had.
                    if (options.retryFailed)
                        continue;
                    this.skipped.add(nodeId);
                    break;
                default:
                    continue; // running/pending: leave in pending
            }
            this.nodeResults[nodeId] = result;
            this.pending.delete(nodeId);
        }
    }
    /**
     * Whether every failed node is a gate that a person clears by signing.
     *
     * The signal is the `approved_by` convention in the gate's own script: those gates check
     * a file for a signature and exit non-zero until it is there. Node ids are not usable —
     * `test-gate` and `input-gate` are named like gates but fail on real defects, and
     * treating them as pauses would hide broken tests.
     */
    allFailedAreApprovalGates() {
        if (this.failed.size === 0)
            return false;
        for (const id of this.failed) {
            const node = this.graph.nodes.get(id);
            if (node?.type !== 'bash' || !node.content.includes('approved_by'))
                return false;
        }
        return true;
    }
    async step(input = {}) {
        // Initialize on first call
        if (!this.initialized && input.args !== undefined) {
            this.args = input.args;
            this.artifactsDir = input.artifactsDir ?? '/tmp';
            this.initialized = true;
        }
        // Validate inputs on first call
        if (!this.inputsValidated) {
            this.inputsValidated = true;
            if (this.graph.inputs) {
                const inputErrors = (0, contract_validator_js_1.validateInputs)(this.args, this.graph.inputs);
                if (inputErrors.length > 0) {
                    return {
                        type: 'failed',
                        error: `Input validation failed: ${inputErrors.join('; ')}`,
                    };
                }
            }
        }
        // Absorb completed AI results
        if (input.completedResults) {
            for (const r of input.completedResults) {
                // A fanout sub-task answers under a synthetic id; record it against its parent.
                const sub = this.parseSubId(r.nodeId);
                const subState = sub && this.fanoutState.get(sub.parent);
                if (sub && subState) {
                    subState.inFlight.delete(sub.index);
                    subState.results.set(sub.index, {
                        status: 'completed',
                        output: r.output,
                        structuredOutput: r.structuredOutput,
                        durationMs: 0,
                        completedAt: new Date().toISOString(),
                    });
                    this.settleFanoutParent(sub.parent, subState);
                    continue;
                }
                // Validate output contract if defined
                const node = this.graph.nodes.get(r.nodeId);
                if (node?.outputFormat && r.structuredOutput) {
                    const validation = (0, contract_validator_js_1.validateOutputFormat)(r.structuredOutput, node.outputFormat);
                    if (!validation.valid) {
                        const errorMsg = `Output contract violation: ${validation.errors.join('; ')}`;
                        this.nodeResults[r.nodeId] = {
                            status: 'failed',
                            error: errorMsg,
                            durationMs: 0,
                        };
                        this.failed.add(r.nodeId);
                        this.pending.delete(r.nodeId);
                        this.callbacks.onNodeFail(r.nodeId, errorMsg);
                        continue;
                    }
                }
                // Normal completion flow
                this.nodeResults[r.nodeId] = {
                    status: 'completed',
                    output: r.output,
                    structuredOutput: r.structuredOutput,
                    durationMs: 0,
                    completedAt: new Date().toISOString(),
                };
                this.completed.add(r.nodeId);
                this.pending.delete(r.nodeId);
                this.callbacks.onNodeComplete(r.nodeId, this.nodeResults[r.nodeId]);
            }
        }
        // Find ready nodes. A fanout parent already expanded stays pending until its
        // sub-tasks answer, so drop it here to avoid expanding it twice.
        const ready = this.findReadyNodes().filter(n => !this.fanoutState.has(n.id));
        const fanoutBusy = this.fanoutBusy();
        if (ready.length === 0 && this.pending.size === 0 && !fanoutBusy) {
            if (this.failed.size > 0) {
                return {
                    type: 'failed',
                    results: this.nodeResults,
                    error: `Nodes failed: ${[...this.failed].join(', ')}`,
                    paused: this.allFailedAreApprovalGates(),
                };
            }
            return { type: 'done', results: this.nodeResults };
        }
        if (ready.length === 0 && this.pending.size > 0 && !fanoutBusy) {
            for (const id of this.pending) {
                this.skipped.add(id);
                this.nodeResults[id] = { status: 'skipped' };
                this.callbacks.onNodeSkip(id, 'blocked by failed dependency');
            }
            this.pending.clear();
            return {
                type: 'failed',
                results: this.nodeResults,
                error: `Blocked nodes: ${[...this.failed].join(', ')}`,
                paused: this.allFailedAreApprovalGates(),
            };
        }
        // Evaluate conditions
        const conditionFiltered = ready.filter(node => {
            const shouldRun = (0, condition_evaluator_js_1.evaluateCondition)(node.when, this.buildOutputsMap());
            if (!shouldRun) {
                this.skipped.add(node.id);
                this.pending.delete(node.id);
                this.nodeResults[node.id] = { status: 'skipped' };
                this.callbacks.onNodeSkip(node.id, `condition not met: ${node.when}`);
                return false;
            }
            return true;
        });
        // Fanout parents take a different path: expand first, then run or yield per item.
        const fanoutNodes = conditionFiltered.filter(n => n.fanout);
        const plainNodes = conditionFiltered.filter(n => !n.fanout);
        for (const node of fanoutNodes) {
            this.callbacks.onNodeStart(node.id);
            const state = this.expandFanout(node);
            // A glob matching nothing is not an error — the parent simply has no work.
            if (state.items.length === 0) {
                this.settleFanoutParent(node.id, state);
                continue;
            }
            if (node.type === 'bash') {
                await this.runBashFanout(node, state);
                this.settleFanoutParent(node.id, state);
            }
            // AI parents are yielded below, capped by maxConcurrency.
        }
        // Separate bash vs AI
        const bashNodes = plainNodes.filter(n => n.type === 'bash');
        const aiNodes = plainNodes.filter(n => n.type !== 'bash');
        // Execute bash nodes internally
        for (const node of bashNodes) {
            this.callbacks.onNodeStart(node.id);
            this.pending.delete(node.id);
            try {
                const result = await this.runner.runBash(node, this.buildContext());
                // Validate output contract if defined
                if (node.outputFormat && result.structuredOutput) {
                    const validation = (0, contract_validator_js_1.validateOutputFormat)(result.structuredOutput, node.outputFormat);
                    if (!validation.valid) {
                        throw new Error(`Output contract violation: ${validation.errors.join('; ')}`);
                    }
                }
                this.nodeResults[node.id] = result;
                this.completed.add(node.id);
                this.callbacks.onNodeComplete(node.id, result);
            }
            catch (error) {
                const errorMsg = error instanceof Error ? error.message : String(error);
                const result = { status: 'failed', error: errorMsg, durationMs: 0 };
                this.nodeResults[node.id] = result;
                // Loop support: retry if configured
                if (node.loop) {
                    const retries = this.retryCounts.get(node.id) ?? 0;
                    if (retries < node.loop.maxRetries) {
                        this.retryCounts.set(node.id, retries + 1);
                        if (node.loop.backoffMs) {
                            await this.delayFn(node.loop.backoffMs * (retries + 1));
                        }
                        this.resetNode(node.id, node.loop.onFail, node.loop.injectError ? errorMsg : undefined);
                        return this.step();
                    }
                }
                this.failed.add(node.id);
                this.callbacks.onNodeFail(node.id, errorMsg);
                // Error strategy: fail_workflow = skip all remaining, return immediately
                if (node.errorStrategy === 'fail_workflow') {
                    for (const id of this.pending) {
                        this.skipped.add(id);
                        this.nodeResults[id] = { status: 'skipped' };
                        this.callbacks.onNodeSkip(id, `workflow failed at "${node.id}"`);
                    }
                    this.pending.clear();
                    return {
                        type: 'failed',
                        results: this.nodeResults,
                        error: `Workflow failed at node "${node.id}": ${errorMsg}`,
                        paused: this.allFailedAreApprovalGates(),
                    };
                }
            }
        }
        // Sub-tasks of every expanded AI fanout parent that still has room to dispatch.
        const fanoutBatch = [];
        for (const [parentId, state] of this.fanoutState) {
            const parent = this.graph.nodes.get(parentId);
            if (!parent || parent.type === 'bash')
                continue;
            for (const index of this.dispatchableSubTasks(parentId, state)) {
                state.inFlight.add(index);
                const resolved = this.runner.resolveAIPrompt(parent, this.fanoutContext(state.items[index], state.as));
                fanoutBatch.push({
                    nodeId: this.subId(parentId, index),
                    prompt: resolved.prompt,
                    skill: resolved.skill,
                    model: parent.model ?? this.graph.defaultModel,
                    context: parent.context,
                });
            }
        }
        // If only bash nodes were ready, recurse to find next batch
        if (aiNodes.length === 0 && fanoutBatch.length === 0) {
            return this.step();
        }
        // Yield AI nodes
        const resolvedNodes = aiNodes.map(node => {
            this.callbacks.onNodeStart(node.id);
            const resolved = this.runner.resolveAIPrompt(node, this.buildContext());
            return {
                nodeId: node.id,
                prompt: resolved.prompt,
                skill: resolved.skill,
                model: node.model ?? this.graph.defaultModel,
                context: node.context,
            };
        });
        return { type: 'needs_ai', nodes: [...resolvedNodes, ...fanoutBatch] };
    }
    findReadyNodes() {
        const ready = [];
        for (const nodeId of this.pending) {
            const node = this.graph.nodes.get(nodeId);
            const depsResolved = node.dependsOn.every(dep => this.completed.has(dep) || this.skipped.has(dep) || this.failed.has(dep));
            if (!depsResolved)
                continue;
            if (node.triggerRule === 'all_success') {
                const anyBlocking = node.dependsOn.some(dep => {
                    if (this.failed.has(dep)) {
                        const depNode = this.graph.nodes.get(dep);
                        return depNode.errorStrategy !== 'continue';
                    }
                    return this.skipped.has(dep);
                });
                if (anyBlocking) {
                    this.pending.delete(nodeId);
                    this.skipped.add(nodeId);
                    this.nodeResults[nodeId] = { status: 'skipped' };
                    this.callbacks.onNodeSkip(nodeId, 'dependency failed');
                    continue;
                }
            }
            else if (node.triggerRule === 'one_success') {
                const anySuccess = node.dependsOn.some(dep => this.completed.has(dep));
                if (!anySuccess) {
                    this.pending.delete(nodeId);
                    this.skipped.add(nodeId);
                    this.nodeResults[nodeId] = { status: 'skipped' };
                    this.callbacks.onNodeSkip(nodeId, 'no dependency succeeded');
                    continue;
                }
            }
            ready.push(node);
        }
        return ready;
    }
    resetNode(loopNodeId, targetNodeId, errorMsg) {
        this.completed.delete(targetNodeId);
        this.failed.delete(targetNodeId);
        this.skipped.delete(targetNodeId);
        this.pending.add(targetNodeId);
        delete this.nodeResults[targetNodeId];
        this.completed.delete(loopNodeId);
        this.failed.delete(loopNodeId);
        this.pending.add(loopNodeId);
        delete this.nodeResults[loopNodeId];
        if (errorMsg) {
            // Stash the failure on the on_fail TARGET so its next prompt carries
            // the real error output (consumed by NodeRunner.resolveAIPrompt).
            const targetNode = this.graph.nodes.get(targetNodeId);
            if (targetNode)
                targetNode.error = errorMsg;
        }
    }
    buildOutputsMap() {
        const outputs = {};
        for (const [id, res] of Object.entries(this.nodeResults)) {
            outputs[id] = { output: res.output?.trim(), structuredOutput: res.structuredOutput };
        }
        return outputs;
    }
    buildContext() {
        return {
            ARGUMENTS: this.args,
            ARTIFACTS_DIR: this.artifactsDir,
            config: this.configVars,
            nodes: this.buildOutputsMap(),
        };
    }
}
exports.DAGExecutor = DAGExecutor;
//# sourceMappingURL=dag-executor.js.map