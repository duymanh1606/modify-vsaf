/**
 * Resolve the identity attached to traces (the user.id attribute), so per-person
 * views ("who created the most artifacts") work. Priority:
 * 1. VSAF_USER env var (explicit override)
 * 2. git config user.name of the project (every dev has one)
 * 3. OS username
 */
export declare function resolveUserId(projectPath: string, env?: NodeJS.ProcessEnv): string | undefined;
//# sourceMappingURL=user.d.ts.map