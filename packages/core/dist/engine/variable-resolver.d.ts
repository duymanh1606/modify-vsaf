/**
 * `bash` quotes every substituted value so spaces and quotes cannot break the script —
 * which means **workflow authors must NOT add quotes of their own** around a variable.
 * `prompt` substitutes raw text for an AI node.
 *
 * One deliberate exception in either mode: `$CONFIG.<key>` is never quoted. It holds a
 * command to execute (`npm test`), not data; quoting it would make the shell look for a
 * binary literally named "npm test" and break the sdlc test gate.
 */
export type ResolveMode = 'prompt' | 'bash';
export interface VariableContext {
    ARGUMENTS: string;
    ARTIFACTS_DIR: string;
    /** Values from .vsaf/config.yaml exposed as $CONFIG.<key> (e.g. $CONFIG.test_command). */
    config?: Record<string, string | undefined>;
    /** Per-item values for a fanout sub-task: always `ITEM`, plus the name chosen by `as`. */
    fanout?: Record<string, string>;
    nodes: Record<string, {
        output?: string;
        structuredOutput?: Record<string, unknown>;
    }>;
}
export declare function resolveVariables(template: string, ctx: VariableContext, mode?: ResolveMode): string;
//# sourceMappingURL=variable-resolver.d.ts.map