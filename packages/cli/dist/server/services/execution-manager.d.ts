import { type StepResult } from '@vsaf/core';
import { SseManager } from './sse-manager.js';
export interface StartRunResult {
    runId: string;
    step: StepResult;
}
export declare class ExecutionManager {
    private readonly projectPath;
    private readonly sseManager;
    private activeRuns;
    constructor(projectPath: string, sseManager: SseManager);
    startRun(workflowName: string, args: string): Promise<StartRunResult>;
    isActive(runId: string): boolean;
}
//# sourceMappingURL=execution-manager.d.ts.map