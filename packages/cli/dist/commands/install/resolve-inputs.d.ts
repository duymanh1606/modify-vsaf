/**
 * Sort out what someone pasted when asked for the project's code repos.
 *
 * The question takes one box, and people paste into it whatever their browser or their
 * terminal already had: a directory beside the project, a clone url, the page of a repo,
 * or the page of a whole project. The last one is the reason this file exists — a
 * project of twenty repos used to mean pasting twenty urls, read off twenty pages.
 *
 * Classifying is a decision about a string, and stays that way: no network, no disk. The
 * one read that does happen — the repo list of a project — is in `resolveInputs` at the
 * bottom, so everything above it can be tested exhaustively without either.
 */
import { type Credential, type GitRunner } from './credentials.js';
import { type GitRunner as PickRunner } from './pick-repos.js';
export type Input = {
    kind: 'adopt';
    path: string;
} | {
    kind: 'clone';
    url: string;
} | {
    kind: 'project';
    base: string;
    key: string;
};
/**
 * Turn the page url of one repo into a url git can clone.
 *
 * The key is lowercased for the path — Bitbucket displays it upper-case and serves it
 * lower-case — but only here: the api is addressed with the key exactly as written.
 *
 * Http by default, because it is built entirely from the url the user pasted and so
 * points at a host and port already known to answer. The ssh form has to guess the port,
 * and the guess is wrong more often than not: bitbucket.digital.vn refuses 7999 and
 * advertises 8081, which then hangs. Ssh stays available for a caller that knows better.
 */
export declare function browseUrlToClone(url: string, protocol?: 'ssh' | 'http'): string;
/**
 * Decide which of the three things an entry is.
 *
 * Order matters: a repo page and a project page differ only by what follows the key, and
 * both look like plain urls. Anything left over is read as a path — the safest reading,
 * because the layer that adopts paths already refuses one that is not a directory, and
 * it refuses it by name. Throwing here instead would take down an install over a
 * mistyped entry that the user could have fixed on the next line.
 */
export declare function classifyInput(entry: string): Input;
/**
 * Something the user asked for that this run could not deliver.
 *
 * Reported back rather than only printed, because it is printed before the install
 * starts and the install prints a hundred lines after it. The one line saying "your
 * twelve repos did not come" scrolled away, and the last thing on screen was
 * "Install complete, 0 issue(s)" — which was not true of what the user asked for.
 */
export interface Unresolved {
    /** What the user pasted or passed. */
    entry: string;
    reason: string;
}
/**
 * Expand what the user pasted into the two lists the installer works from.
 *
 * A project link becomes the repos it holds — the read that saves twenty page visits.
 * Everything else keeps the meaning it already had.
 *
 * A project that cannot be read costs that entry and nothing else: the rest of the
 * install is still worth having, and an install that stops on a missing credential
 * teaches people to avoid the feature rather than to fix the credential.
 *
 * Lives here rather than in `index.ts` (where the spec put it) because `index.ts` parses
 * the command line as it loads and so cannot be imported by a test.
 */
export declare function resolveInputs(entries: string[], options?: {
    token?: string | Credential;
    fetchImpl?: typeof fetch;
    /** Same reason as `fetchImpl`: so a test can fix what the machine holds. */
    env?: NodeJS.ProcessEnv;
    run?: GitRunner;
    /**
     * Where code repos will land. Needed to tell which of a project's repos are already
     * here — without it the picker can still ask, it just cannot mark them.
     */
    beside?: string;
    /** Injected together: the git that reads sibling remotes, and whether to ask at all. */
    pickRun?: PickRunner;
    isTTY?: boolean;
    ask?: (question: string) => Promise<string>;
}): Promise<{
    clone: string[];
    adopt: string[];
    unresolved: Unresolved[];
}>;
//# sourceMappingURL=resolve-inputs.d.ts.map