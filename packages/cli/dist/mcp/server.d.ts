import { type StepResult } from '@vsaf/core';
interface StartParams {
    workflow: string;
    args: string;
    projectPath: string;
}
interface NextParams {
    runId: string;
    results: Array<{
        nodeId: string;
        output: string;
        structuredOutput?: Record<string, unknown>;
    }>;
    /** Only needed to resume a run after an engine restart (rehydrate). */
    projectPath?: string;
}
interface ResumeParams {
    runId: string;
    projectPath: string;
}
interface StatusParams {
    runId: string;
}
interface CommandParams {
    name: string;
    projectPath: string;
    args?: string;
}
/**
 * Load a single command outside any workflow run: the merged prompt is the
 * skill body plus the project-context overlay from .vsaf/commands/<name>.md —
 * the same composition loadCommand does for `command:` DAG nodes. There is no
 * run/workspace here, so $ARTIFACTS_DIR resolves to empty.
 */
export declare function execCommand(params: CommandParams): {
    name: string;
    description: string;
    prompt: string;
};
export declare class VSAFEngine {
    private executors;
    private workspaces;
    private runMeta;
    private runStores;
    private failedRuns;
    private telemetries;
    start(params: StartParams): Promise<{
        runId: string;
        step: StepResult;
        workspacePath: string;
        projectPath: string;
    }>;
    /**
     * Continue a run the engine no longer holds — after a restart, or after a HITL gate
     * stopped it. Handing back no results is what makes it a resume: nothing new is
     * reported, the run is rebuilt from disk and simply asked what comes next.
     */
    resume(params: ResumeParams): Promise<{
        step: StepResult;
        workspacePath: string;
        projectPath: string;
    }>;
    next(params: NextParams): Promise<{
        step: StepResult;
        workspacePath: string;
        projectPath: string;
    }>;
    status(params: StatusParams): {
        runId: string;
        workflow: string;
        status: string;
    };
    /**
     * Persistence + telemetry wiring shared by start and rehydrate. Per AI node,
     * MCP-mode enrichment collects output metrics (file/LOC deltas in the
     * project dir, where Claude writes). Metrics attach before nodeComplete —
     * the span closes there, and attributes only land on an open span.
     * Concurrent fresh-context nodes write to the same project dir, so their
     * file/LOC deltas can cross-attribute; these metrics are per-node
     * accurate only for serial execution.
     *
     * For the drift-check command node (content === 'sdlc-drift-check'),
     * maybeAttachDrift reads .vsaf/telemetry/drift.json (written by the
     * sdlc-drift-check skill) and attaches drift scores to the same still-open
     * span, right before nodeComplete closes it.
     */
    private buildRunCallbacks;
    /**
     * Rebuild a run lost with a previous engine process from its persisted
     * state.json (see README "Resume Failed Runs"). The rebuilt executor never
     * re-runs terminal nodes; the rehydrated run gets a fresh trace marked
     * vsaf.run.resumed, linked to the original trace via vsaf.run.id.
     */
    private rehydrate;
    private finalizeTelemetry;
    /**
     * End a run that stopped. A pause is recorded as such and keeps its workspace: the human
     * signs, `vsaf_resume` picks the run back up, and the gate runs again. Tearing the
     * workspace down on a pause is what forced resume to rebuild one.
     */
    private stopRun;
    private cleanupRun;
    private finishRun;
}
export declare function startMCPServer(): Promise<void>;
export {};
//# sourceMappingURL=server.d.ts.map