export declare const CLAUDE_SESSION_FILE: string;
/**
 * Read the Claude Code session id written by the SessionStart hook
 * (see README "Telemetry" section). Returns undefined when the file is
 * missing, stale, or contains an invalid value — telemetry then runs
 * without usage attribution.
 */
export declare function readClaudeSessionId(projectPath: string, maxAgeMs?: number): string | undefined;
//# sourceMappingURL=claude-session.d.ts.map