"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveUserId = resolveUserId;
// packages/cli/src/telemetry/user.ts
const child_process_1 = require("child_process");
const os_1 = require("os");
/**
 * Resolve the identity attached to traces (the user.id attribute), so per-person
 * views ("who created the most artifacts") work. Priority:
 * 1. VSAF_USER env var (explicit override)
 * 2. git config user.name of the project (every dev has one)
 * 3. OS username
 */
function resolveUserId(projectPath, env = process.env) {
    const explicit = env.VSAF_USER?.trim();
    if (explicit)
        return explicit;
    try {
        const gitName = (0, child_process_1.execFileSync)('git', ['config', 'user.name'], {
            cwd: projectPath,
            encoding: 'utf-8',
            windowsHide: true,
        }).trim();
        if (gitName)
            return gitName;
    }
    catch {
        // not a git repo / git missing — fall through
    }
    try {
        return (0, os_1.userInfo)().username || undefined;
    }
    catch {
        return undefined;
    }
}
//# sourceMappingURL=user.js.map