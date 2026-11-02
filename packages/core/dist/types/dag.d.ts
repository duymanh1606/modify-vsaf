import type { ErrorStrategy, OutputFormat, InputParamDef } from './workflow.js';
export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export interface DAGNode {
    id: string;
    type: 'prompt' | 'bash' | 'command';
    content: string;
    dependsOn: string[];
    when?: string;
    triggerRule: 'all_success' | 'one_success';
    context: 'fresh' | 'inherit';
    workspace: boolean;
    model?: string;
    allowedTools?: string[];
    outputFormat?: OutputFormat;
    status: NodeStatus;
    output?: string;
    structuredOutput?: Record<string, unknown>;
    durationMs?: number;
    error?: string;
    errorStrategy: ErrorStrategy;
    loop?: {
        onFail: string;
        maxRetries: number;
        injectError: boolean;
        backoffMs?: number;
    };
    /** Path to a read-only file whose tail is prepended to this node's AI prompt. */
    ledger?: string;
    /**
     * Resolved fanout config. Note `maxConcurrency` is always set here (defaults to
     * Infinity) whereas the YAML-level `max_concurrency` is optional.
     */
    fanout?: {
        over: string;
        as: string;
        maxConcurrency: number;
    };
}
export interface DAGGraph {
    name: string;
    description: string;
    defaultProvider: string;
    defaultModel: string;
    inputs?: Record<string, InputParamDef>;
    nodes: Map<string, DAGNode>;
}
//# sourceMappingURL=dag.d.ts.map