/** Rule sets are chosen per stack, not per project — a monorepo can need both. */
export type Stack = 'fe' | 'be';
/**
 * Work out what kind of code a repo holds, from its dependency manifests.
 *
 * An empty result is a normal answer, not a failure: a docs-only repo gets no
 * coding rules, which keeps its sessions free of irrelevant context.
 */
export declare function detectStack(projectPath: string): Stack[];
/**
 * Pull the managed import block back out of `CLAUDE.md`, leaving the prose the
 * user wrote around it. Returns the file path, or null when there was no block.
 */
export declare function removeRulesImport(projectPath: string): string | null;
/**
 * Install the pack's rule files for the stacks a repo actually uses, and point
 * `CLAUDE.md` at them through a marker block that a reinstall rewrites in place.
 *
 * Returns every path written, all of them inside the project.
 */
export declare function deployRules(packDir: string, projectPath: string, stack: Stack[]): string[];
//# sourceMappingURL=rules.d.ts.map