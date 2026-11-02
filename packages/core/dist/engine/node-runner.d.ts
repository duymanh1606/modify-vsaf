import type { DAGNode } from '../types/dag.js';
import type { NodeResult } from '../store/types.js';
import { type VariableContext } from './variable-resolver.js';
export declare function resolveBashShell(): string | undefined;
export interface ResolvedPrompt {
    prompt: string;
    skill?: string;
}
export declare class NodeRunner {
    private readonly workspaceCwd;
    private readonly projectCwd?;
    constructor(workspaceCwd: string, projectCwd?: string | undefined);
    private getCwd;
    /**
     * Cross-iteration context: when a node declares `ledger: <path>`, read that file
     * and return a READ-ONLY preamble to prepend to the prompt — the lessons a previous
     * iteration left behind. Capped at the last 16 KB because the file is append-only,
     * so the tail is the recent part. A missing, unreadable or blank file yields '' and
     * is never an error. The engine only reads; other nodes in the workflow do the writing.
     */
    private ledgerPreamble;
    runBash(node: DAGNode, ctx: VariableContext): Promise<NodeResult>;
    resolveAIPrompt(node: DAGNode, ctx: VariableContext): ResolvedPrompt;
    /**
     * When a loop with inject_error reset this node, carry the downstream
     * failure (e.g. test-gate output) into its prompt so the model fixes the
     * real error instead of retrying blind. One-shot: cleared after use.
     */
    private withInjectedError;
}
//# sourceMappingURL=node-runner.d.ts.map