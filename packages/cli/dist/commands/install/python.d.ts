/** How the interpreter must be invoked once found. */
export interface PythonRuntime {
    command: string;
    args: string[];
    version: string;
}
/** Returns the command's version output, or null when the command does not answer. */
export type PythonProbe = (command: string, args: string[]) => string | null;
/**
 * Find an interpreter able to run the pack's Python hooks.
 *
 * Python 2 is rejected rather than accepted: the hooks are Python 3, so reporting
 * a 2.x interpreter as found would trade a clear "missing" message for hooks that
 * die at runtime with a syntax error.
 */
export declare function resolvePython(probe?: PythonProbe): PythonRuntime | null;
export interface PythonCheck {
    name: string;
    ok: boolean;
    version?: string;
    message?: string;
}
/** Doctor-shaped report, so a missing interpreter surfaces before hooks fail silently. */
export declare function checkPython(probe?: PythonProbe): PythonCheck;
//# sourceMappingURL=python.d.ts.map