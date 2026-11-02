"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.authorizationHeader = authorizationHeader;
exports.credentialFromEnv = credentialFromEnv;
exports.forgetCredentials = forgetCredentials;
exports.credentialFromGit = credentialFromGit;
exports.approveInGit = approveInGit;
exports.configuredHelper = configuredHelper;
exports.helperForThisOs = helperForThisOs;
exports.enableHelper = enableHelper;
exports.resolveCredential = resolveCredential;
exports.credentialForHost = credentialForHost;
const child_process_1 = require("child_process");
/** The variable that still wins, because that is how CI passes a credential. */
const ENV_KEY = 'BITBUCKET_TOKEN';
/**
 * How long to let git answer.
 *
 * A helper can be a program that unlocks a keychain, and on a locked one it may sit
 * waiting for a dialog nobody is looking at. `GIT_TERMINAL_PROMPT=0` stops git itself
 * from asking, but it cannot stop a helper, so there is a clock as well.
 */
const FILL_TIMEOUT_MS = 10_000;
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
function authorizationHeader(credential, scheme) {
    const form = scheme ?? (credential.username ? 'basic' : 'bearer');
    if (form === 'bearer')
        return `Bearer ${credential.secret}`;
    const pair = `${credential.username ?? ''}:${credential.secret}`;
    return `Basic ${Buffer.from(pair, 'utf-8').toString('base64')}`;
}
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
function credentialFromEnv(env = process.env) {
    const fromEnv = env[ENV_KEY]?.trim();
    return fromEnv ? { secret: fromEnv, source: 'env' } : undefined;
}
const runGit = (args, stdin) => (0, child_process_1.execFileSync)('git', args, {
    input: stdin,
    encoding: 'utf-8',
    timeout: FILL_TIMEOUT_MS,
    // Piped, not inherited: a helper's chatter on stderr would otherwise land in the
    // middle of the install's own output, and stdout carries the credential.
    stdio: ['pipe', 'pipe', 'pipe'],
    // Without this, a host with nothing stored makes git ask for a username at the
    // terminal — in the middle of an install, with no explanation of what it is for.
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0' },
});
/**
 * How long to wait when git is allowed to ask a person.
 *
 * Ten seconds is right for a helper answering from a keychain and wrong for someone typing
 * a password. This is the only path where a human is in the loop.
 */
const ASK_TIMEOUT_MS = 300_000;
/**
 * Run git with its prompt allowed.
 *
 * The prompt goes to `/dev/tty`, not to this process's stdin — measured: with the query
 * piped in, git still asks "Username for …" on the terminal and hands the answer back. So
 * one question can serve a whole batch of clones, which is the point.
 */
const runGitAsking = (args, stdin) => (0, child_process_1.execFileSync)('git', args, {
    input: stdin,
    encoding: 'utf-8',
    timeout: ASK_TIMEOUT_MS,
    stdio: ['pipe', 'pipe', 'inherit'],
    env: { ...process.env, GIT_TERMINAL_PROMPT: '1' },
});
/**
 * Credentials already resolved in this run, by host.
 *
 * Without this, one command asks twice: once to read the repo list over the api, once more
 * before cloning. Two prompts for the same password is the bug this map exists to prevent.
 */
const remembered = new Map();
/** Drop what this run remembered. For tests, which must not leak into each other. */
function forgetCredentials() {
    remembered.clear();
}
/**
 * The question to put to git, in its own key-value form.
 *
 * Host and protocol only, no `path=`. Git ignores a path unless `credential.useHttpPath`
 * is on, and where it is on, a path would make the lookup *miss*: the api is addressed at
 * the server root while the stored entry belongs to `scm/<project>/<repo>.git`. Asking at
 * host level is the question the default configuration answers.
 */
function query(url) {
    let parsed;
    try {
        parsed = new URL(url);
    }
    catch {
        return undefined;
    }
    const protocol = parsed.protocol.replace(/:$/, '');
    // Ssh carries no credential a helper would hold — it is a key on disk — and asking for
    // one is how you get git prompting for a password that does not exist.
    if (protocol !== 'http' && protocol !== 'https')
        return undefined;
    return `protocol=${protocol}\nhost=${parsed.host}\n\n`;
}
/** git's key-value output, as a map. Values may hold `=`; keys may not. */
function fields(output) {
    const found = {};
    for (const line of output.split('\n')) {
        const at = line.indexOf('=');
        if (at > 0)
            found[line.slice(0, at).trim()] = line.slice(at + 1);
    }
    return found;
}
/**
 * Ask git for the credential this machine already holds for a host.
 *
 * Returns nothing when there is none, and that is not a failure: it is the state of a
 * machine that has only ever cloned over ssh, or never cloned from this host at all.
 */
function credentialFromGit(url, run = runGit) {
    const stdin = query(url);
    if (!stdin)
        return undefined;
    let output;
    try {
        output = run(['credential', 'fill'], stdin);
    }
    catch {
        // Nothing stored, no helper configured, or a helper that hung past the clock. All
        // three mean the same thing to the caller.
        return undefined;
    }
    const found = fields(output);
    const secret = found.password?.trim();
    if (!secret)
        return undefined;
    return { secret, username: found.username?.trim() || undefined, source: 'git' };
}
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
function approveInGit(url, credential, run = runGit) {
    // Only what git gave us. A token from the environment belongs to a CI job or to one
    // command someone ran on purpose — writing it into this machine's store is not what
    // they asked for.
    if (credential.source !== 'git' || !credential.username)
        return false;
    const stdin = query(url);
    if (!stdin)
        return false;
    const body = stdin.replace(/\n\n$/, '\n')
        + `username=${credential.username}\npassword=${credential.secret}\n\n`;
    try {
        run(['credential', 'approve'], body);
        return true;
    }
    catch {
        // A store that refuses to write costs the next run one prompt. Not worth a word here.
        return false;
    }
}
/**
 * Which helper git would use, or nothing when none is configured.
 *
 * Nothing is the whole problem this exists to find. With no helper, git has nowhere to keep
 * a credential: it asks, uses the answer for that one command, and forgets. Cloning twelve
 * repos then means typing the password twelve times — measured on macOS, which ships no
 * helper by default, unlike Windows where `manager` is already there.
 */
function configuredHelper(run = runGit) {
    try {
        return run(['config', '--get', 'credential.helper'], '').trim() || undefined;
    }
    catch {
        // `--get` exits non-zero when the key is unset. That is the answer, not a failure.
        return undefined;
    }
}
/** The keychain-backed helper this OS ships, when it ships one. */
function helperForThisOs(platform = process.platform) {
    if (platform === 'darwin')
        return 'osxkeychain';
    if (platform === 'win32')
        return 'manager';
    // Linux has no one answer: `libsecret` needs a package, and `store` writes the secret to
    // a plain file. Neither is ours to choose for someone.
    return undefined;
}
/** Turn a helper on for this machine, so the next credential typed is the last one. */
function enableHelper(helper, run = runGit) {
    try {
        run(['config', '--global', 'credential.helper', helper], '');
        return true;
    }
    catch {
        return false;
    }
}
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
function resolveCredential(url, options = {}) {
    const env = options.env ?? process.env;
    const fromEnv = credentialFromEnv(env);
    if (fromEnv)
        return fromEnv;
    const stored = credentialFromGit(url, options.run ?? runGit);
    if (stored)
        return stored;
    // Nothing stored, and someone is here: let git ask, once. Twelve clones used to mean
    // twelve prompts — each `git clone` asking on its own, and on a machine with no helper
    // none of the answers kept. One question here, carried to every clone in the batch.
    const interactive = options.isTTY ?? Boolean(process.stdin.isTTY);
    if (!interactive)
        return undefined;
    return credentialFromGit(url, options.askRun ?? runGitAsking);
}
/**
 * The credential for a host, asked for at most once per run.
 *
 * Reading the repo list and cloning are two separate needs for the same password. Asked
 * separately, they are two prompts.
 */
function credentialForHost(url, options = {}) {
    let key;
    try {
        key = new URL(url).host;
    }
    catch {
        key = url;
    }
    const already = remembered.get(key);
    if (already)
        return already;
    const found = resolveCredential(url, options);
    if (found)
        remembered.set(key, found);
    return found;
}
//# sourceMappingURL=credentials.js.map