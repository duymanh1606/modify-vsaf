/**
 * What marks the spec repo: the directory holding the NTAPP artifact tree. The
 * older bootstrap script used the same signal.
 */
export declare const SPEC_REPO_MARKER = "NTAPP-output";
/**
 * The repos this project already claims, read from its own workspace file.
 *
 * `<name>.code-workspace` sits at the spec repo root, is committed, and lists the spec
 * repo plus every code repo the wiring found — so it is the project's own answer to
 * "which repos are mine", identical for everyone on the team.
 *
 * Reading it means `--upgrade` does not have to ask a question it can already answer.
 * Before this, someone who cloned one more repo was asked to re-pick the other five, or
 * to spell them out on the command line — and a list retyped by hand is a list that
 * eventually loses an entry.
 *
 * Anything unreadable returns nothing: a hand-edited workspace file with a trailing comma
 * is not a reason to stop an install, and asking is a working fallback.
 */
/**
 * The workspace file's own name, read off disk rather than guessed.
 *
 * `<name>.code-workspace` is named after the project, and that name is not always the
 * folder someone typed: `--new` asks for it separately, `--clone` infers it from the
 * folder, and a hand-run bootstrap can rename it with `--project-name`. Only the file
 * itself is the answer — printing a path built from a name the code assumed is exactly
 * how a "here's what to open next" message ends up pointing at a file that is not there.
 *
 * `undefined` when there is none yet, or more than one and picking is a guess.
 */
export declare function workspaceFileIn(specRepo: string): string | undefined;
export declare function reposInWorkspaceFile(specRepo: string): string[];
/**
 * How a candidate must be spelled on the command line.
 *
 * Always relative to the spec repo, because that is what resolution reads. Naming
 * them relative to anything else does not round-trip: a name that fails to resolve
 * falls back to a match by last path segment, which can silently pick a different
 * repo that happens to share the name.
 */
export declare function candidateName(specRepo: string, candidate: string): string;
/**
 * Read what the user picked from the numbered list of candidates.
 *
 * Returns names spelled the way `--code-repos` accepts, or undefined for "nothing"
 * — an empty answer, or one that names nothing valid. Undefined means nothing is
 * wired, which is the safe reading of an answer that could not be understood.
 *
 * `a` takes every candidate; anything out of range is dropped rather than guessed at.
 */
export declare function parseRepoChoice(answer: string, candidates: string[], specRepo: string): string[] | undefined;
/**
 * Whether every name would resolve to a code repo, without writing anything.
 *
 * The same reading `resolveWorkspace` does, split out so it can be run before the
 * install starts. It used to happen at the end of the wiring step, which is after the
 * skills, the hooks, the rules, the artifact tree and a git repo had all been written
 * — so a typo in `--code-repos` left a half-installed directory behind and no record
 * of it.
 *
 * Pure: it reads directories and nothing else. The marker for the spec repo is not
 * consulted, because the install is what creates it.
 */
export declare function validateRepoNames(projectPath: string, names: string[]): {
    ok: true;
} | {
    ok: false;
    unknown: string[];
    candidates: string[];
};
export interface Workspace {
    specRepo: string;
    /** Whether this project is the spec repo — the only place worth configuring from. */
    isSpecRepo: boolean;
    /** Sibling directories that look like code repos. Suggestions only. */
    candidates: string[];
    /** The repos the caller actually asked for. Empty unless named. */
    codeRepos: string[];
}
export declare function isCodeRepo(path: string): boolean;
/**
 * Work out the multi-repo layout around a spec repo.
 *
 * Nothing is selected unless the caller names it. Configuring every sibling that
 * merely looks like a repo is how the older script reached into unrelated projects
 * sharing the same parent directory, and that is not recoverable by guessing.
 *
 * A name that matches no sibling repo throws rather than quietly configuring
 * nothing — a typo would otherwise look like success.
 */
export declare function resolveWorkspace(projectPath: string, names?: string[], options?: {
    assumeSpecRepo?: boolean;
}): Workspace;
//# sourceMappingURL=workspace.d.ts.map