/**
 * Install the pack's pre-commit hook into a repo.
 *
 * Skips a directory that is not a git repo rather than failing: a workspace often
 * holds a mix, and the rest of the install has nothing to do with git.
 *
 * A hook already in place is copied aside first — it may be the user's own. Only
 * when it differs from the one being installed: backing up unconditionally left a
 * fresh `.bak` in every repo on every run, and re-running the install is the normal
 * way to finish one that stopped half way, so the copies piled up.
 *
 * Returns the hook path, or null when there was nothing to install.
 */
export declare function installPreCommitHook(packDir: string, repoPath: string): string | null;
//# sourceMappingURL=precommit.d.ts.map