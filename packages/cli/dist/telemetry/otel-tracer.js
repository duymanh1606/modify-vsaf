"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OtelRunTracer = void 0;
/** Δ6: run args can carry huge prompts — cap the attribute payload. */
const MAX_ARGS_LENGTH = 4096;
function debugLog(...args) {
    if (process.env.VSAF_TELEMETRY_DEBUG) {
        console.error('[vsaf:telemetry]', ...args);
    }
}
/** The 6 score entries derived from one NodeOutputMetrics. */
function outputScoreEntries(m) {
    return [
        { name: 'loc_added', value: m.locAdded },
        { name: 'loc_removed', value: m.locRemoved },
        { name: 'net_loc', value: m.locAdded - m.locRemoved },
        { name: 'files_created', value: m.filesCreated },
        { name: 'files_modified', value: m.filesModified },
        { name: 'artifacts_created', value: m.artifactsCreated },
    ];
}
const ROLES = ['spec', 'code'];
/**
 * Extra score entries splitting the totals by repo, so a dashboard can tell design
 * output from working code instead of adding them into one figure.
 *
 * Emitted only once a run has actually touched a code repo: a single-repo project
 * would otherwise gain six all-zero score names per node for no information. That
 * means a dual-repo dashboard should sum these, not average them — a doc-only node
 * contributes no entry rather than an explicit zero.
 */
function roleScoreEntries(m) {
    if (!m.byRole || !hasOutput(m.byRole.code))
        return [];
    const entries = [];
    for (const role of ROLES) {
        const r = m.byRole[role];
        entries.push({ name: `${role}_loc_added`, value: r.locAdded }, { name: `${role}_net_loc`, value: r.locAdded - r.locRemoved }, { name: `${role}_files_created`, value: r.filesCreated });
    }
    return entries;
}
function hasOutput(r) {
    return r.locAdded > 0 || r.locRemoved > 0 || r.filesCreated > 0 || r.filesModified > 0;
}
function emptyRole() {
    return { filesCreated: 0, filesModified: 0, locAdded: 0, locRemoved: 0, artifactsCreated: 0 };
}
class OtelRunTracer {
    options;
    nodes = new Map();
    root;
    workflow = '';
    userId;
    /**
     * Trace-level attributes repeated on every node span. The root span is only
     * exported at endRun (BatchSpanProcessor exports on span end), so a running
     * flow would otherwise show an unnamed trace in Langfuse until it finishes —
     * Langfuse applies `langfuse.trace.*`, user.id and session.id from any span.
     */
    traceAttributes = {};
    ended = false;
    runtime;
    getRuntime;
    constructor(runtime, options) {
        this.options = options;
        // A factory lets the queue size scale with the DAG (Δ7) — the graph is
        // only known at startRun, after createTelemetry has already run.
        this.getRuntime = typeof runtime === 'function' ? runtime : () => runtime;
    }
    startRun(run, graph) {
        try {
            this.workflow = run.workflow;
            this.userId = run.userId;
            this.runtime = this.getRuntime(graph.nodes.size);
            for (const [id, node] of graph.nodes) {
                this.nodes.set(id, {
                    attempt: 0,
                    kind: node.type === 'bash' ? 'bash' : 'ai',
                    model: node.type === 'bash' ? undefined : (node.model ?? graph.defaultModel),
                });
            }
            const args = run.args.length > MAX_ARGS_LENGTH
                ? `${run.args.slice(0, MAX_ARGS_LENGTH)}…[truncated]`
                : run.args;
            const attributes = {
                'vsaf.run.id': run.runId,
                'vsaf.run.args': args,
                'vsaf.run.node_count': graph.nodes.size,
            };
            if (run.resumed)
                attributes['vsaf.run.resumed'] = true;
            if (run.claudeSessionId)
                attributes['session.id'] = run.claudeSessionId;
            if (run.userId)
                attributes['user.id'] = run.userId;
            this.traceAttributes = {
                'langfuse.trace.name': `vsaf:${run.workflow}`,
                'langfuse.trace.metadata.args': args,
            };
            if (run.claudeSessionId)
                this.traceAttributes['session.id'] = run.claudeSessionId;
            if (run.userId)
                this.traceAttributes['user.id'] = run.userId;
            this.root = this.runtime.startSpan(`vsaf:${run.workflow}`, {
                startTime: new Date(),
                attributes,
            });
        }
        catch (error) {
            debugLog('startRun failed:', error);
        }
    }
    nodeStart(nodeId) {
        try {
            if (!this.root)
                return;
            const state = this.nodes.get(nodeId) ?? { attempt: 0, kind: 'ai' };
            // Orphan-guard (Δ1): a re-entered node whose previous span never closed
            // would otherwise leak an open span past endRun.
            if (state.span) {
                state.span.setAttribute('vsaf.status', 'orphaned');
                state.span.end(new Date());
            }
            state.attempt += 1;
            state.startedAt = new Date();
            const isAi = state.kind === 'ai';
            const attributes = {
                ...this.traceAttributes,
                'vsaf.node_id': nodeId,
                'vsaf.attempt': state.attempt,
                'vsaf.kind': state.kind,
            };
            if (isAi) {
                attributes['gen_ai.operation.name'] = 'invoke_agent';
                attributes['gen_ai.provider.name'] = this.options.provider;
                if (state.model)
                    attributes['gen_ai.request.model'] = state.model;
            }
            state.span = this.runtime.startSpan(isAi ? `invoke_agent ${nodeId}` : nodeId, { startTime: state.startedAt, attributes }, this.root);
            state.spanId = state.span.spanContext().spanId;
            this.nodes.set(nodeId, state);
        }
        catch (error) {
            debugLog('nodeStart failed:', error);
        }
    }
    nodeComplete(nodeId, result) {
        try {
            const state = this.nodes.get(nodeId);
            if (!state?.span || !state.startedAt)
                return;
            state.span.setAttributes({
                'vsaf.status': 'completed',
                'vsaf.reported_duration_ms': result?.durationMs,
            });
            state.span.end(new Date());
            state.span = undefined;
        }
        catch (error) {
            debugLog('nodeComplete failed:', error);
        }
    }
    nodeFail(nodeId, error) {
        try {
            const state = this.nodes.get(nodeId);
            if (!state?.span || !state.startedAt)
                return;
            state.span.setStatus({ code: 'ERROR', message: error });
            state.span.setAttribute('vsaf.status', 'failed');
            state.span.end(new Date());
            state.span = undefined;
        }
        catch (failError) {
            debugLog('nodeFail failed:', failError);
        }
    }
    nodeSkip(nodeId, reason) {
        try {
            if (!this.root)
                return;
            const state = this.nodes.get(nodeId);
            const now = new Date();
            const isAi = (state?.kind ?? 'ai') === 'ai';
            this.runtime
                .startSpan(isAi ? `invoke_agent ${nodeId}` : nodeId, {
                startTime: now,
                attributes: {
                    ...this.traceAttributes,
                    'vsaf.node_id': nodeId,
                    'vsaf.kind': state?.kind ?? 'ai',
                    'vsaf.status': 'skipped',
                    'vsaf.skip_reason': reason,
                },
            }, this.root)
                .end(now);
        }
        catch (error) {
            debugLog('nodeSkip failed:', error);
        }
    }
    attachOutputMetrics(nodeId, metrics) {
        try {
            const state = this.nodes.get(nodeId);
            if (!state?.span) {
                debugLog('attachOutputMetrics dropped — span already ended:', nodeId);
                return;
            }
            state.span.setAttributes({
                'vsaf.output.artifacts_created': metrics.artifactsCreated,
                'vsaf.output.files_created': metrics.filesCreated,
                'vsaf.output.loc_added': metrics.locAdded,
            });
            // Attributes carry no cardinality cost, so the split is always recorded here
            // even when one side is zero — it makes a span self-describing on inspection.
            if (metrics.byRole) {
                for (const role of ROLES) {
                    const r = metrics.byRole[role];
                    state.span.setAttributes({
                        [`vsaf.output.${role}.files_created`]: r.filesCreated,
                        [`vsaf.output.${role}.files_modified`]: r.filesModified,
                        [`vsaf.output.${role}.loc_added`]: r.locAdded,
                    });
                }
            }
            state.lastOutput = metrics;
            // Per-node Langfuse scores (per-user stats via user.id on the trace).
            // Optional chaining on postScores keeps drift-only test doubles valid.
            if (this.options.scoreClient && state.spanId) {
                const traceId = this.root?.spanContext().traceId;
                void this.options.scoreClient.postScores?.([...outputScoreEntries(metrics), ...roleScoreEntries(metrics)].map((entry) => ({
                    traceId,
                    observationId: state.spanId,
                    ...entry,
                })));
            }
        }
        catch (error) {
            debugLog('attachOutputMetrics failed:', error);
        }
    }
    attachDriftScores(nodeId, results) {
        try {
            const state = this.nodes.get(nodeId);
            const traceId = this.root?.spanContext().traceId;
            for (const r of results) {
                // (1) span attribute trên node drift-check (nếu span còn mở)
                state?.span?.setAttributes({
                    [`vsaf.drift.${r.downstreamNode}_vs_${r.upstreamNode}`]: r.score,
                });
                // (2) Langfuse Scores API per-observation (nếu có client)
                const observationId = this.getNodeSpanId(r.downstreamNode);
                if (this.options.scoreClient && observationId) {
                    void this.options.scoreClient.postScore({
                        traceId,
                        observationId,
                        name: 'drift',
                        value: r.score,
                        comment: r.reason,
                    });
                }
            }
        }
        catch (error) {
            debugLog('attachDriftScores failed:', error);
        }
    }
    getNodeSpanId(nodeId) {
        return this.nodes.get(nodeId)?.spanId;
    }
    async endRun(success, error, outcome) {
        try {
            if (this.ended)
                return; // Δ3: idempotent
            this.ended = true;
            const traceId = this.root?.spanContext().traceId;
            for (const state of this.nodes.values()) {
                if (state.span) {
                    // A span still open here belongs to a node that was mid-flight when
                    // the run ended — close it now so nothing leaks past endRun.
                    state.span.end(new Date());
                    state.span = undefined;
                }
            }
            // Totals are summed from each node's LAST attachment (Δ2): re-emitted
            // output replaces its predecessor instead of double-counting.
            const totals = {
                artifacts_created: 0,
                files_created: 0,
                files_modified: 0,
                loc_added: 0,
                loc_removed: 0,
            };
            const roleTotals = { spec: emptyRole(), code: emptyRole() };
            for (const state of this.nodes.values()) {
                if (state.lastOutput) {
                    totals.artifacts_created += state.lastOutput.artifactsCreated;
                    totals.files_created += state.lastOutput.filesCreated;
                    totals.files_modified += state.lastOutput.filesModified;
                    totals.loc_added += state.lastOutput.locAdded;
                    totals.loc_removed += state.lastOutput.locRemoved;
                    for (const role of ROLES) {
                        const from = state.lastOutput.byRole?.[role];
                        if (!from)
                            continue;
                        const acc = roleTotals[role];
                        acc.artifactsCreated += from.artifactsCreated;
                        acc.filesCreated += from.filesCreated;
                        acc.filesModified += from.filesModified;
                        acc.locAdded += from.locAdded;
                        acc.locRemoved += from.locRemoved;
                    }
                }
            }
            // Trace-level run totals as Langfuse scores; `run_` prefix keeps
            // per-user dashboard sums from double-counting the per-node scores.
            if (this.options.scoreClient && traceId) {
                const totalsMetrics = {
                    artifactsCreated: totals.artifacts_created,
                    filesCreated: totals.files_created,
                    filesModified: totals.files_modified,
                    locAdded: totals.loc_added,
                    locRemoved: totals.loc_removed,
                    createdPaths: [],
                    byRole: roleTotals,
                };
                void this.options.scoreClient.postScores?.([...outputScoreEntries(totalsMetrics), ...roleScoreEntries(totalsMetrics)].map(({ name, value }) => ({ traceId, name: `run_${name}`, value })));
            }
            if (this.root) {
                for (const [name, value] of Object.entries(totals)) {
                    this.root.setAttribute(`vsaf.run.${name}`, value);
                }
                for (const role of ROLES) {
                    const r = roleTotals[role];
                    this.root.setAttribute(`vsaf.run.${role}.files_created`, r.filesCreated);
                    this.root.setAttribute(`vsaf.run.${role}.files_modified`, r.filesModified);
                    this.root.setAttribute(`vsaf.run.${role}.loc_added`, r.locAdded);
                    this.root.setAttribute(`vsaf.run.${role}.loc_removed`, r.locRemoved);
                }
                const status = outcome ?? (success ? 'completed' : 'failed');
                this.root.setAttribute('vsaf.run.status', status);
                // A pause is not an error span: the gate did its job. Marking it ERROR is what put
                // every approval-in-waiting into the failed bucket on the dashboard.
                if (status === 'failed') {
                    this.root.setStatus({ code: 'ERROR', message: error ?? 'unknown' });
                }
                this.root.end(new Date());
                this.root = undefined;
            }
            // Δ4: omit user.id rather than emit `undefined`; Δ5: always emit, even 0.
            if (this.runtime) {
                const metricAttributes = { workflow: this.workflow };
                if (this.userId)
                    metricAttributes['user.id'] = this.userId;
                for (const [name, value] of Object.entries(totals)) {
                    this.runtime.addMetric(`vsaf.run.${name}`, value, metricAttributes);
                }
                await this.runtime.flush(5_000);
                await this.runtime.shutdown();
            }
        }
        catch (endError) {
            debugLog('endRun failed:', endError);
        }
    }
}
exports.OtelRunTracer = OtelRunTracer;
//# sourceMappingURL=otel-tracer.js.map