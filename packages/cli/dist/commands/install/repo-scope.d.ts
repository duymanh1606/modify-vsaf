/** What kind of code a repo is allowed to hold. Drives the pre-commit path rule. */
export type RepoScope = 'service-only' | 'fullstack' | 'unknown';
export interface ScopeDetection {
    scope: RepoScope;
    /** What in the repo led to the answer, so a wrong guess is easy to argue with. */
    signal: string;
}
/**
 * Decide whether a repo holds services only, or UI as well.
 *
 * A repo with no telling manifest stays `unknown` rather than being guessed at: the
 * scope decides what the pre-commit rule forbids, and a wrong guess would block
 * legitimate work.
 */
export declare function detectRepoScope(repoPath: string): ScopeDetection;
/**
 * Take the scope block back out, leaving the rest of the file.
 *
 * Separate from removing files the installer created: `CLAUDE.md` belongs to the
 * repo, and deleting it to undo an appended block would destroy the user's own
 * documentation.
 *
 * Returns the file written, or null when there was no block.
 */
export declare function removeScopeBlock(repoPath: string): string | null;
/**
 * Record what kind of code a repo holds, in a marker block in its `CLAUDE.md`.
 *
 * A scope already written in the block wins over a fresh guess — someone may have
 * corrected it by hand, and detection cannot tell a correction from a stale value.
 * Only `unknown` is re-detected, since that one is an admission of not knowing.
 *
 * Returns the file written, or null when nothing changed.
 */
export declare function writeScopeBlock(repoPath: string): string | null;
//# sourceMappingURL=repo-scope.d.ts.map