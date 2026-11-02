import { type DAGGraph, type VSAFConfig } from '@vsaf/core';
export interface RunOptions {
    args: string;
    resume?: string;
}
export interface PreparedRun {
    graph: DAGGraph;
    config: VSAFConfig;
    args: string;
}
export declare function prepareRun(workflowName: string, projectPath: string, options: RunOptions): Promise<PreparedRun>;
export declare function execRun(workflowName: string, projectPath: string, options: RunOptions): Promise<void>;
//# sourceMappingURL=run.d.ts.map