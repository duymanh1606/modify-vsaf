import type { DAGGraph } from '../types/dag.js';
import type { NodeResult } from '../store/types.js';
/**
 * Separates a fanout parent id from its sub-task index: `build~fanout~2`.
 * Chosen because `~` is not valid in an author-written node id, so a synthetic
 * sub-task id can never collide with a real node. Exported because run recovery
 * needs to recognise these ids — they exist only at runtime, never in the YAML.
 */
export declare const FANOUT_SEP = "~fanout~";
export interface ExecutorCallbacks {
    onNodeStart: (nodeId: string) => void;
    onNodeComplete: (nodeId: string, result: NodeResult) => void;
    onNodeSkip: (nodeId: string, reason: string) => void;
    onNodeFail: (nodeId: string, error: string) => void;
}
export interface ExecutorOptions {
    delayFn?: (ms: number) => Promise<void>;
    /** Values from .vsaf/config.yaml exposed to nodes as $CONFIG.<key>. */
    configVars?: Record<string, string | undefined>;
}
export interface ResolvedNode {
    nodeId: string;
    prompt: string;
    skill?: string;
    model?: string;
    /** 'fresh': orchestrator phải chạy node trong subagent context mới; 'inherit': chạy inline. */
    context: 'fresh' | 'inherit';
}
export interface CompletedResult {
    nodeId: string;
    output: string;
    structuredOutput?: Record<string, unknown>;
}
export interface StepResult {
    type: 'needs_ai' | 'done' | 'failed';
    nodes?: ResolvedNode[];
    results?: Record<string, NodeResult>;
    error?: string;
    /**
     * The run stopped at a gate a human clears, not at a defect.
     *
     * A HITL gate exits non-zero until someone signs the artifact it checks, which is the
     * gate doing its job — but it was recorded as a failed run, so a workflow waiting for
     * an approval looked identical to one that broke. Callers that ignore this flag behave
     * exactly as before.
     */
    paused?: boolean;
}
export interface StepInput {
    args?: string;
    artifactsDir?: string;
    completedResults?: CompletedResult[];
}
export interface RestoreState {
    args: string;
    artifactsDir: string;
    /** Persisted node results from RunStore state.json. */
    nodes: Record<string, NodeResult>;
}
export declare class DAGExecutor {
    private readonly workspaceCwd;
    private readonly projectPath;
    private readonly graph;
    private readonly callbacks;
    private pending;
    private completed;
    private failed;
    private skipped;
    private nodeResults;
    private runner;
    private args;
    private artifactsDir;
    private initialized;
    private inputsValidated;
    private retryCounts;
    /** Parent node id → expansion state. Empty for every workflow that declares no fanout. */
    private fanoutState;
    private readonly delayFn;
    private readonly configVars?;
    constructor(workspaceCwd: string, projectPath: string, graph: DAGGraph, callbacks: ExecutorCallbacks, options?: ExecutorOptions);
    private subId;
    /** Split a sub-task id back into its parts, or null if this is a plain node id. */
    private parseSubId;
    /**
     * Expand a parent the first time it becomes ready. `over` is a glob resolved
     * against the same cwd the node itself would run in, so `workspace: false`
     * nodes glob the project rather than the throwaway workspace.
     */
    private expandFanout;
    /** Variable context for one sub-task: its item under both ITEM and the `as` name. */
    private fanoutContext;
    /** True while any expanded parent still has sub-tasks left to finish. */
    private fanoutBusy;
    /** Indices not yet started, capped so no parent exceeds its concurrency limit. */
    private dispatchableSubTasks;
    /** Once every sub-task has answered, settle the parent as completed or failed. */
    private settleFanoutParent;
    /** Run every sub-task of a bash parent, honouring the concurrency limit. */
    private runBashFanout;
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
    restore(state: RestoreState, options?: {
        retryFailed?: boolean;
    }): void;
    /**
     * Whether every failed node is a gate that a person clears by signing.
     *
     * The signal is the `approved_by` convention in the gate's own script: those gates check
     * a file for a signature and exit non-zero until it is there. Node ids are not usable —
     * `test-gate` and `input-gate` are named like gates but fail on real defects, and
     * treating them as pauses would hide broken tests.
     */
    private allFailedAreApprovalGates;
    step(input?: StepInput): Promise<StepResult>;
    private findReadyNodes;
    private resetNode;
    private buildOutputsMap;
    private buildContext;
}
//# sourceMappingURL=dag-executor.d.ts.map