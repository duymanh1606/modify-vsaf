import type { NodeStatus } from '../types/dag.js';
export type RunStatus = 'running' | 'completed' | 'failed' | 'paused';
export interface NodeResult {
    status: NodeStatus;
    output?: string;
    structuredOutput?: Record<string, unknown>;
    durationMs?: number;
    error?: string;
    startedAt?: string;
    completedAt?: string;
}
export interface WorkflowRun {
    runId: string;
    workflow: string;
    status: RunStatus;
    args: string;
    workspacePath: string;
    artifactsPath: string;
    projectPath: string;
    startedAt: string;
    completedAt?: string;
    nodes: Record<string, NodeResult>;
}
export interface WorkflowEvent {
    timestamp: string;
    type: 'run:create' | 'node:start' | 'node:complete' | 'node:skip' | 'node:fail' | 'run:complete' | 'run:fail' | 'run:resume' | 'run:pause';
    nodeId?: string;
    data?: Record<string, unknown>;
}
//# sourceMappingURL=types.d.ts.map