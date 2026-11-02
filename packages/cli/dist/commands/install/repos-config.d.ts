/** The config file the pack's skills read. Its name is fixed by those skills. */
export declare const CONFIG_FILE = ".bmm-config.yaml";
export interface RepoStack {
    language: string;
    framework: string;
    ui_library: string;
    build_tool: string;
}
export interface ReposLayout {
    /** Repo holding the documents and the canonical skills. */
    specRepo: string;
    /** Repos holding code, each configured with its own stack. */
    codeRepos: string[];
    metaRepo?: string;
    /**
     * Name of the project. Defaults to the spec repo's directory name — pass it so
     * every generated file agrees on one name.
     */
    projectName?: string;
    /**
     * Design-system sub-directory per code repo, keyed by absolute repo path. A repo
     * with no entry points at the family root, which is what a single front end wants.
     */
    designSystemRoots?: Map<string, string>;
}
/**
 * Work out a repo's stack from its build manifests.
 *
 * An unrecognised repo reports `<TODO>` rather than a guess, so the gap shows up
 * in the generated config instead of quietly steering skills the wrong way.
 */
export declare function detectRepoStack(repoPath: string): RepoStack;
/**
 * Render the pack's config template into every code repo, filling in that repo's
 * own stack and its relative path back to the spec repo.
 *
 * Returns the config files written.
 */
export declare function deployReposConfig(packDir: string, layout: ReposLayout): string[];
/**
 * Point each code repo at the spec repo's canonical skills through a relative
 * symlink, so one edit is seen by every repo in the workspace.
 *
 * A real directory already sitting at the link path is left alone — it may hold
 * the user's own files, and replacing it would destroy them.
 */
export declare function linkCanonicalSkills(specRepo: string, codeRepos: string[]): string[];
//# sourceMappingURL=repos-config.d.ts.map