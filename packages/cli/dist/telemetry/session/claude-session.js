"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CLAUDE_SESSION_FILE = void 0;
exports.readClaudeSessionId = readClaudeSessionId;
// packages/cli/src/telemetry/session/claude-session.ts
const fs_1 = require("fs");
const path_1 = require("path");
exports.CLAUDE_SESSION_FILE = (0, path_1.join)('.vsaf', '.claude-session');
const DEFAULT_MAX_AGE_MS = 24 * 60 * 60 * 1000;
// Mirrors the gateway's session-id value validation (x-*-session-id headers).
const SESSION_ID_RE = /^[a-zA-Z0-9_-]{8,}$/;
/**
 * Read the Claude Code session id written by the SessionStart hook
 * (see README "Telemetry" section). Returns undefined when the file is
 * missing, stale, or contains an invalid value — telemetry then runs
 * without usage attribution.
 */
function readClaudeSessionId(projectPath, maxAgeMs = DEFAULT_MAX_AGE_MS) {
    try {
        const filePath = (0, path_1.join)(projectPath, exports.CLAUDE_SESSION_FILE);
        if (!(0, fs_1.existsSync)(filePath))
            return undefined;
        const age = Date.now() - (0, fs_1.statSync)(filePath).mtimeMs;
        if (age > maxAgeMs)
            return undefined;
        const value = (0, fs_1.readFileSync)(filePath, 'utf-8').trim();
        return SESSION_ID_RE.test(value) ? value : undefined;
    }
    catch {
        return undefined;
    }
}
//# sourceMappingURL=claude-session.js.map