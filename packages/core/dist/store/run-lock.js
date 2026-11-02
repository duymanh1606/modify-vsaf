"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LOCK_FILE = void 0;
exports.acquireRunLock = acquireRunLock;
const fs_1 = require("fs");
const path_1 = require("path");
/** Lives beside the run state, inside the project's `.vsaf/`. */
exports.LOCK_FILE = 'run.lock';
/** True when the process is still around, so its lock must be respected. */
function processAlive(pid) {
    try {
        // Signal 0 performs the permission/existence check without touching the process.
        process.kill(pid, 0);
        return true;
    }
    catch (error) {
        // EPERM means it exists but belongs to another user — still alive.
        return error.code === 'EPERM';
    }
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
async function acquireRunLock(projectPath, runId) {
    const dir = (0, path_1.join)(projectPath, '.vsaf');
    const path = (0, path_1.join)(dir, exports.LOCK_FILE);
    (0, fs_1.mkdirSync)(dir, { recursive: true });
    if ((0, fs_1.existsSync)(path)) {
        let holder = null;
        try {
            holder = JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
        }
        catch {
            holder = null; // unreadable lock is treated as abandoned, not as a deadlock
        }
        if (holder && typeof holder.pid === 'number' && processAlive(holder.pid))
            return null;
        (0, fs_1.rmSync)(path, { force: true });
    }
    // 'wx' fails if the file appeared between the check above and here, so two
    // concurrent callers cannot both believe they won.
    let fd;
    try {
        fd = (0, fs_1.openSync)(path, 'wx');
    }
    catch {
        return null;
    }
    (0, fs_1.closeSync)(fd);
    const record = { pid: process.pid, runId, at: Date.now() };
    (0, fs_1.writeFileSync)(path, JSON.stringify(record), 'utf-8');
    let released = false;
    return {
        runId,
        async release() {
            if (released)
                return;
            released = true;
            (0, fs_1.rmSync)(path, { force: true });
        },
    };
}
//# sourceMappingURL=run-lock.js.map