/**
 * Where the credential for a Bitbucket host comes from.
 *
 * `git clone` never needed this file: git asks its own credential helper — Keychain on
 * macOS, Credential Manager on Windows, whatever `credential.helper` names on Linux — and
 * anyone who has cloned over http once already has an answer stored there.
 *
 * The api read does need it. That read is a `fetch()`, and `fetch()` knows nothing about
 * credential helpers, which is why the install used to stop and ask for
 * `BITBUCKET_TOKEN` in the environment. So the credential is fetched the way git fetches
 * it — by running git — and the person who has cloned before does nothing at all.
 *
 * Two doors and no third one. vsaf reads a credential; it never takes one down and never
 * puts one away. There is deliberately no prompt here: asking someone to paste a token
 * would put a secret in a terminal, and keeping it would mean vsaf writing to the
 * machine's credential store on their behalf — both are the user's own call, and both are
 * already served by `git clone`, which asks and stores through the OS itself.
 */
/** A credential as git hands it over: the secret, and the name it belongs to. */
export interface Credential {
    /** The password field. On Bitbucket Server this is usually a personal access token. */
    secret: string;
    /** Present when the store keeps one. Needed for basic auth. */
    username?: string;
    /** Which door it came through — for messages, which must never name the secret. */
    source: 'env' | 'git';
}
/** Runs git and returns its stdout. Injected so tests need neither git nor a store. */
export type GitRunner = (args: string[], stdin: string) => string;
/** Which of the two forms the same secret is sent in. */
export type AuthScheme = 'bearer' | 'basic';
/**
 * The `Authorization` header value for a credential.
 *
 * One place, because two callers now send the same secret to the same server: the api
 * read that lists repos, and the git config the flows clone runs under. Written twice it
 * would be two chances to pick the wrong form — and the two forms are not
 * interchangeable here, see `listProjectRepos`.
 *
 * Default form follows what the credential is. A pair with a username is a login, which
 * this server takes as `Basic`; a bare secret is a personal access token, which it takes
 * as `Bearer` and refuses as `Basic` — measured against bitbucket.digital.vn.
 */
export declare function authorizationHeader(credential: Credential, scheme?: AuthScheme): string;
/**
 * The credential the environment carries, or nothing.
 *
 * Its own function because two callers need this half on its own: `resolveCredential`
 * below, and the flows clone, which must not run `git credential fill` itself — git runs
 * its own helper during the clone, so asking here would be a second lookup for the same
 * answer, and on a locked keychain a second wait for it.
 *
 * A blank value counts as absent: that is exactly what `export BITBUCKET_TOKEN=<token>`
 * leaves behind, since `<token>` is a redirection, and treating it as present produced a
 * 401 that sent people hunting for a permissions problem they did not have.
 */
export declare function credentialFromEnv(env?: NodeJS.ProcessEnv): Credential | undefined;
/** Drop what this run remembered. For tests, which must not leak into each other. */
export declare function forgetCredentials(): void;
/**
 * Ask git for the credential this machine already holds for a host.
 *
 * Returns nothing when there is none, and that is not a failure: it is the state of a
 * machine that has only ever cloned over ssh, or never cloned from this host at all.
 */
export declare function credentialFromGit(url: string, run?: GitRunner): Credential | undefined;
/**
 * Tell git a credential worked, so its store keeps it.
 *
 * This is the step git takes for itself and cannot take here: after any git command
 * authenticates successfully, git calls `credential approve` and the machine's store
 * remembers. Reading the repo list is a `fetch`, not a git command, so nothing ever
 * approved — the person typed a password into their editor's popup, it worked, and it was
 * gone by the next run. Measured behaviour, and the whole reason this exists.
 *
 * Nothing new is stored: the pair came from git's own helper a moment ago, and it goes back
 * to the same place through git's own command. vsaf never invents a secret and never keeps
 * one of its own — a credential typed into a prompt of ours, kept in a file of ours, would
 * be a different thing entirely, and is not what happens here.
 *
 * Needs a username: git stores a pair, and inventing the name would leave `git clone`
 * sending one the server never issued.
 */
export declare function approveInGit(url: string, credential: Credential, run?: GitRunner): boolean;
/**
 * Which helper git would use, or nothing when none is configured.
 *
 * Nothing is the whole problem this exists to find. With no helper, git has nowhere to keep
 * a credential: it asks, uses the answer for that one command, and forgets. Cloning twelve
 * repos then means typing the password twelve times — measured on macOS, which ships no
 * helper by default, unlike Windows where `manager` is already there.
 */
export declare function configuredHelper(run?: GitRunner): string | undefined;
/** The keychain-backed helper this OS ships, when it ships one. */
export declare function helperForThisOs(platform?: string): string | undefined;
/** Turn a helper on for this machine, so the next credential typed is the last one. */
export declare function enableHelper(helper: string, run?: GitRunner): boolean;
/**
 * The credential to use for a host: the environment, then the store git itself reads.
 *
 * The environment first because that is the override — CI sets it, and so does anyone
 * working around a stale entry in their keychain for one run. A blank value counts as
 * absent: that is exactly what `export BITBUCKET_TOKEN=<token>` leaves behind, since
 * `<token>` is a redirection, and treating it as present produced a 401 that sent people
 * hunting for a permissions problem they did not have.
 *
 * Nothing after those two. When neither answers, the caller says so and the run carries
 * on without that one project link — see `tokenGuidance` in `resolve-inputs.ts`.
 */
export declare function resolveCredential(url: string, options?: {
    env?: NodeJS.ProcessEnv;
    run?: GitRunner;
    /** Runner that lets git prompt. Absent means no asking. */
    askRun?: GitRunner;
    isTTY?: boolean;
}): Credential | undefined;
/**
 * The credential for a host, asked for at most once per run.
 *
 * Reading the repo list and cloning are two separate needs for the same password. Asked
 * separately, they are two prompts.
 */
export declare function credentialForHost(url: string, options?: Parameters<typeof resolveCredential>[1]): Credential | undefined;
//# sourceMappingURL=credentials.d.ts.map