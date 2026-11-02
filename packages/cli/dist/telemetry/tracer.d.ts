import type { DAGGraph, NodeResult } from '@vsaf/core';
import type { NodeOutputMetrics } from './metrics/output-metrics.js';
/** How a run ended, when "success or not" is too coarse. */
export type RunOutcome = 'completed' | 'failed' | 'paused';
export interface DriftResult {
    downstreamNode: string;
    upstreamNode: string;
    score: number;
    reason: string;
    checked: boolean;
}
export interface RunInfo {
    runId: string;
    workflow: string;
    args: string;
    claudeSessionId?: string;
    /** Identity for per-person views on the telemetry backend (user.id attribute). */
    userId?: string;
    /** True when the run was rehydrated after an engine restart — its trace is
     * new; vsaf.run.id links it to the pre-restart trace of the same run. */
    resumed?: boolean;
}
/**
 * Mode-agnostic telemetry emitter. Both the MCP path and a future
 * provider-adapter path drive the same DAGExecutor callbacks, so anything
 * hooked here works for both. Implementations must never throw.
 */
export interface Tracer {
    startRun(run: RunInfo, graph: DAGGraph): void;
    nodeStart(nodeId: string): void;
    nodeComplete(nodeId: string, result: NodeResult): void;
    nodeFail(nodeId: string, error: string): void;
    nodeSkip(nodeId: string, reason: string): void;
    /** Attach file/LOC output metrics to the still-open span of a node — call before nodeComplete. */
    attachOutputMetrics(nodeId: string, metrics: NodeOutputMetrics): void;
    /** Ghi điểm drift: span attribute trên node drift-check + (nếu Langfuse) POST Scores API per-observation. */
    attachDriftScores(nodeId: string, results: DriftResult[]): void;
    /**
     * `outcome` names what actually happened when it is not simply success or failure — a
     * run stopped at a HITL gate is `paused`, and filing it as failed made an approval
     * queue look like a wall of broken runs.
     */
    endRun(success: boolean, error?: string, outcome?: RunOutcome): Promise<void>;
}
export declare class NoopTracer implements Tracer {
    startRun(): void;
    nodeStart(): void;
    nodeComplete(): void;
    nodeFail(): void;
    nodeSkip(): void;
    attachOutputMetrics(): void;
    attachDriftScores(): void;
    endRun(): Promise<void>;
}
//# sourceMappingURL=tracer.d.ts.map