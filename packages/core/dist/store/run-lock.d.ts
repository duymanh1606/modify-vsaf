/** Lives beside the run state, inside the project's `.vsaf/`. */
export declare const LOCK_FILE = "run.lock";
export interface RunLock {
    runId: string;
    /** Idempotent — releasing an already-released lock is not an error. */
    release(): Promise<void>;
}
/**
 * Stop two runs from working the same project at once, which would let them
 * overwrite each other's state. Returns null when another live run holds the lock.
 *
 * A lock whose owner has died is taken over rather than honoured — otherwise a
 * single crash would make the project permanently unrunnable.
 *
 * Opt-in: callers decide whether to acquire. Nothing changes for a project that
 * never asks for a lock.
 */
export declare function acquireRunLock(projectPath: string, runId: string): Promise<RunLock | null>;
//# sourceMappingURL=run-lock.d.ts.map