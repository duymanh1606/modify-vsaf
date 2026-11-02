"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolvePython = resolvePython;
exports.checkPython = checkPython;
const child_process_1 = require("child_process");
/**
 * Order matters. `python3` is the reliable name on Linux and macOS; Windows with
 * Git Bash commonly has only `python`; the `py` launcher is last and needs `-3`
 * so it does not hand back a Python 2 interpreter.
 */
const CANDIDATES = [
    { command: 'python3', args: [] },
    { command: 'python', args: [] },
    { command: 'py', args: ['-3'] },
];
function defaultProbe(command, args) {
    try {
        return (0, child_process_1.execFileSync)(command, [...args, '--version'], {
            stdio: ['ignore', 'pipe', 'pipe'],
            encoding: 'utf-8',
        });
    }
    catch {
        return null;
    }
}
/**
 * Find an interpreter able to run the pack's Python hooks.
 *
 * Python 2 is rejected rather than accepted: the hooks are Python 3, so reporting
 * a 2.x interpreter as found would trade a clear "missing" message for hooks that
 * die at runtime with a syntax error.
 */
function resolvePython(probe = defaultProbe) {
    for (const { command, args } of CANDIDATES) {
        const output = probe(command, args);
        if (!output)
            continue;
        const version = output.trim().match(/Python\s+(\d+\.\d+(?:\.\d+)?)/i)?.[1];
        if (!version || !version.startsWith('3.'))
            continue;
        return { command, args, version };
    }
    return null;
}
/** Doctor-shaped report, so a missing interpreter surfaces before hooks fail silently. */
function checkPython(probe = defaultProbe) {
    const runtime = resolvePython(probe);
    if (runtime) {
        return { name: 'Python 3', ok: true, version: runtime.version };
    }
    return {
        name: 'Python 3',
        ok: false,
        message: 'not found — pack hooks need Python 3 on PATH as python3, python, or py -3',
    };
}
//# sourceMappingURL=python.js.map