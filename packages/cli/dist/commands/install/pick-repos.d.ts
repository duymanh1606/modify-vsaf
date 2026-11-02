/**
 * Which repos of a project to bring in.
 *
 * A project link used to mean every repo behind it. That is right for a project that *is*
 * the product, and wrong for the ones people actually paste: a group holding dozens of
 * repos, of which a given piece of work needs three. Cloning the other sixty costs disk,
 * costs time, and on Bitbucket costs a login attempt each.
 *
 * Two projects pasted together are two questions, not one list — the numbers restart per
 * project so a repo is never picked by a number that belongs to a different group.
 *
 * Everything here decides things about strings and directories, so it can be tested
 * without a network: the one impure part is reading the git remote of a sibling directory,
 * and that takes an injectable runner.
 */
/** Runs git and returns stdout. Injected so tests need no repos on disk. */
export type GitRunner = (args: string[]) => string;
/**
 * The identity of a repo, as far as "do we already have this one" goes.
 *
 * The last two path segments, lowercased, without `.git`. Not the whole url, because the
 * same repo is `http://host/scm/vcoding/vsaf.git` to one person and
 * `ssh://git@host:7999/vcoding/vsaf.git` to the next, and not the directory name either —
 * a spec repo cloned as `project-spec` while its slug is `map-spec` is the case that made
 * this necessary: comparing names, the installer cloned a second copy of a repo the user
 * already had.
 */
export declare function repoKey(url: string): string;
/**
 * The repos already sitting beside the project, by identity.
 *
 * Only immediate children, and only ones holding a `.git` — a directory of loose files is
 * not a repo, and walking deeper would find the repos inside a workspace nobody meant to
 * include. A child without an `origin` is skipped rather than guessed at.
 */
export declare function reposAlreadyBeside(parent: string, run?: GitRunner): Map<string, string>;
/** What the user typed, read against a list of that many entries. */
export interface Selection {
    /** Zero-based positions, in order, without repeats. */
    picked: number[];
    /** Tokens that named nothing — reported rather than silently dropped. */
    unknown: string[];
}
/**
 * Read `1,3-5` — and `a`, and an empty line.
 *
 * Commas or spaces, either way: people type both, and rejecting one of them over
 * punctuation would be its own small insult. A number outside the list is reported, not
 * clamped: clamping `70` to `63` clones a repo nobody asked for.
 */
export declare function parseSelection(answer: string, count: number): Selection;
/**
 * Lay labels out across the terminal, filling down each column.
 *
 * Down rather than across, so a list read top-to-bottom stays in order in the first
 * column — reading order matters more than packing when the numbers are what you type.
 */
export declare function inColumns(labels: string[], width?: number): string[];
/** One repo as offered for picking. */
export interface Offered {
    slug: string;
    url: string;
}
/** The numbered lines to show, one per repo, marking the ones already on disk. */
export declare function offerLines(repos: Offered[], beside: Map<string, string>): string[];
/**
 * Ask which repos of one project to bring in.
 *
 * Returns them all where nobody can be asked — a script or a CI job pasted the link
 * meaning the whole project, and that is what the flag has always done. Changing that
 * silently would break jobs whose output nobody reads.
 *
 * A repo already on disk is offered but left out of `a`: it is still pickable by number,
 * for the person who knows their copy is stale, but "all" cannot quietly re-clone over
 * work that is not pushed yet.
 */
export declare function askWhichRepos(key: string, repos: Offered[], options?: {
    parent?: string;
    run?: GitRunner;
    isTTY?: boolean;
    /** Injected so a test can drive the whole exchange, prompt and marking included. */
    ask?: (question: string) => Promise<string>;
}): Promise<Offered[]>;
//# sourceMappingURL=pick-repos.d.ts.map