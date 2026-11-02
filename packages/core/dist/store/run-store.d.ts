import type { WorkflowRun, NodeResult, WorkflowEvent } from './types.js';
export declare class RunStore {
    private readonly baseDir;
    private runs;
    private logs;
    constructor(baseDir: string);
    create(workflow: string, args: string, workspacePath: string, artifactsPath: string, projectPath: string): WorkflowRun;
    updateNode(runId: string, nodeId: string, result: Partial<NodeResult>): void;
    save(runId: string): void;
    complete(runId: string): void;
    fail(runId: string): void;
    /**
     * The run stopped at a gate a person clears — not a failure. Kept separate from `fail`
     * so a workflow waiting for a signature is not filed next to one that broke.
     */
    pause(runId: string): void;
    /**
     * Put a terminated run back in flight — used when a run that stopped at a HITL gate is
     * resumed after the human signed. The node results stay; only the run's own verdict is
     * cleared, so whatever happens next decides it afresh.
     */
    resume(runId: string): void;
    load(runId: string): WorkflowRun | undefined;
    listAll(): WorkflowRun[];
    getEvents(runId: string): WorkflowEvent[];
    private getLog;
    private getRun;
    private persist;
    private statusToEventType;
}
//# sourceMappingURL=run-store.d.ts.map