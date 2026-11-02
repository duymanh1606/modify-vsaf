export interface OutputFormatProperty {
    type: string;
    enum?: string[];
}
export interface OutputFormat {
    type: 'object';
    properties: Record<string, OutputFormatProperty>;
    required?: string[];
}
export type ErrorStrategy = 'skip_dependents' | 'fail_workflow' | 'continue';
export interface InputParamDef {
    type: 'string' | 'number' | 'boolean';
    required?: boolean;
    default?: string;
}
export type TriggerRule = 'all_success' | 'one_success';
export interface LoopConfig {
    on_fail: string;
    max_retries: number;
    inject_error?: boolean;
    backoff_ms?: number;
}
export interface NodeDefinition {
    id: string;
    /** Documentation only — the engine does not consume it. */
    description?: string;
    prompt?: string;
    bash?: string;
    command?: string;
    depends_on?: string[];
    when?: string;
    trigger_rule?: TriggerRule;
    context?: 'fresh' | 'inherit';
    model?: string;
    allowed_tools?: string[];
    output_format?: OutputFormat;
    workspace?: boolean;
    loop?: LoopConfig;
    on_error?: ErrorStrategy;
    /** Path to a read-only file whose tail is prepended to this node's AI prompt. */
    ledger?: string;
    /** Expand this node into one sub-task per file matched by `over`. */
    fanout?: FanoutConfig;
}
export interface FanoutConfig {
    /** Glob pattern resolved against the node's cwd. */
    over: string;
    /** Variable name each sub-task sees, alongside the always-present `ITEM`. */
    as: string;
    /** Max sub-tasks in flight per parent node. Omitted means unlimited. */
    max_concurrency?: number;
}
export interface WorkflowDefinition {
    name: string;
    description: string;
    provider: string;
    model: string;
    inputs?: Record<string, InputParamDef>;
    nodes: NodeDefinition[];
}
//# sourceMappingURL=workflow.d.ts.map