/**
 * Write the multi-root workspace file beside the spec repo.
 *
 * Paths are relative so the file survives the workspace being moved or cloned
 * somewhere else. Built and serialised as data rather than by filling a text
 * template, so the result cannot come out as invalid JSON.
 *
 * Written even when no code repo is named yet. That case used to be skipped as "one
 * repo needs no multi-root file", but it is the case that needs the file most: a
 * project is set up before its code repos arrive, and the person who installed it
 * then had nothing to open — and no obvious way to get one, short of installing
 * again with the right flag.
 *
 * Returns the file written.
 */
export declare function writeWorkspaceFile(specRepo: string, projectName: string, codeRepos: string[]): string;
//# sourceMappingURL=workspace-file.d.ts.map