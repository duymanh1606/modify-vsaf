import type { DAGGraph, NodeResult } from '@vsaf/core';
import type { NodeOutputMetrics } from './metrics/output-metrics.js';
import type { Tracer, RunInfo, DriftResult, RunOutcome } from './tracer.js';
import type { OtelRuntime } from './otel-sdk.js';
import type { LangfuseScoreClient } from './langfuse-scores.js';
export interface OtelTracerOptions {
    /** Value for gen_ai.provider.name on AI-node spans. */
    provider: string;
    /** When present, attachDriftScores also POSTs per-observation scores to Langfuse. */
    scoreClient?: LangfuseScoreClient;
}
export declare class OtelRunTracer implements Tracer {
    private readonly options;
    private nodes;
    private root?;
    private workflow;
    private userId?;
    /**
     * Trace-level attributes repeated on every node span. The root span is only
     * exported at endRun (BatchSpanProcessor exports on span end), so a running
     * flow would otherwise show an unnamed trace in Langfuse until it finishes —
     * Langfuse applies `langfuse.trace.*`, user.id and session.id from any span.
     */
    private traceAttributes;
    private ended;
    private runtime?;
    private readonly getRuntime;
    constructor(runtime: OtelRuntime | ((nodeCount: number) => OtelRuntime), options: OtelTracerOptions);
    startRun(run: RunInfo, graph: DAGGraph): void;
    nodeStart(nodeId: string): void;
    nodeComplete(nodeId: string, result: NodeResult): void;
    nodeFail(nodeId: string, error: string): void;
    nodeSkip(nodeId: string, reason: string): void;
    attachOutputMetrics(nodeId: string, metrics: NodeOutputMetrics): void;
    attachDriftScores(nodeId: string, results: DriftResult[]): void;
    getNodeSpanId(nodeId: string): string | undefined;
    endRun(success: boolean, error?: string, outcome?: RunOutcome): Promise<void>;
}
//# sourceMappingURL=otel-tracer.d.ts.map