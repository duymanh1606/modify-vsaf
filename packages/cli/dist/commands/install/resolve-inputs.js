"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.browseUrlToClone = browseUrlToClone;
exports.classifyInput = classifyInput;
exports.resolveInputs = resolveInputs;
const promises_1 = require("node:readline/promises");
const bitbucket_js_1 = require("./bitbucket.js");
const credentials_js_1 = require("./credentials.js");
const pick_repos_js_1 = require("./pick-repos.js");
const PROJECT_SEGMENT = '/projects/';
/** Bitbucket Server's default ssh port, used only when guessing from a page url. */
const DEFAULT_SSH_PORT = 7999;
/** Drop the anchor, the query string and any trailing slashes a browser left behind. */
function clean(url) {
    return url.trim().split('#')[0].split('?')[0].replace(/\/+$/, '');
}
/**
 * Cut a Bitbucket page url in two at `/projects/`.
 *
 * Cutting at the host instead would lose the path prefix of a server published under
 * one — `http://host/bitbucket/projects/IDP` — and every api call after that would be
 * aimed at a url nobody serves.
 *
 * Returns null when the string is not a url, or holds no `/projects/` segment: a
 * directory really named `/srv/projects/IDP` is a path, not a page.
 */
function splitAtProjects(entry) {
    const url = clean(entry);
    const at = url.indexOf(PROJECT_SEGMENT);
    if (at < 0)
        return null;
    const base = url.slice(0, at);
    if (!base.includes('://'))
        return null;
    const rest = url.slice(at + PROJECT_SEGMENT.length);
    return rest ? { base, rest } : null;
}
/** The repo a page url points at: `<key>/repos/<slug>/…` — the tail is browser state. */
function repoOnPage(rest) {
    const [key, marker, slug] = rest.split('/');
    if (!key || marker !== 'repos' || !slug)
        return null;
    return { key, slug: slug.replace(/\.git$/, '') };
}
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
function browseUrlToClone(url, protocol = 'http') {
    const split = splitAtProjects(url);
    const repo = split && repoOnPage(split.rest);
    if (!split || !repo)
        throw new Error(`Not the page of a repo: ${url}`);
    const path = `${repo.key.toLowerCase()}/${repo.slug}.git`;
    if (protocol === 'http')
        return `${split.base}/scm/${path}`;
    return `ssh://git@${new URL(split.base).hostname}:${DEFAULT_SSH_PORT}/${path}`;
}
/**
 * Decide which of the three things an entry is.
 *
 * Order matters: a repo page and a project page differ only by what follows the key, and
 * both look like plain urls. Anything left over is read as a path — the safest reading,
 * because the layer that adopts paths already refuses one that is not a directory, and
 * it refuses it by name. Throwing here instead would take down an install over a
 * mistyped entry that the user could have fixed on the next line.
 */
function classifyInput(entry) {
    const value = entry.trim();
    const split = splitAtProjects(value);
    if (split) {
        try {
            // A url malformed enough that it cannot be parsed falls through to a path, where
            // it gets reported by name rather than ending the install.
            if (repoOnPage(split.rest))
                return { kind: 'clone', url: browseUrlToClone(value) };
            const [key] = split.rest.split('/');
            if (key)
                return { kind: 'project', base: new URL(split.base).toString().replace(/\/$/, ''), key };
        }
        catch {
            return { kind: 'adopt', path: value };
        }
    }
    // Anything carrying a scheme is a url to fetch from, not a directory: `https://…` and
    // `file://…` name repos too, and a project page is the only url form already handled
    // above. Dropping this rule for a list of known shapes silently turned a github url
    // without a `.git` suffix into a path that does not exist.
    if (value.includes('://') || value.startsWith('git@') || value.endsWith('.git')) {
        return { kind: 'clone', url: value };
    }
    return { kind: 'adopt', path: value };
}
/**
 * True when nothing came back at all, as opposed to a refusal that came back quickly.
 *
 * The difference decides what to tell the person: silence is worth another go, while a
 * 401 or a 404 is an answer and asking again cannot change it.
 */
function silentServer(message) {
    return /Quá hạn|Không kết nối được/.test(message);
}
/**
 * Why this link could not be read. One line, no advice.
 *
 * What to do about it is not repeated here because the summary at the end of the install
 * already carries it — entry by entry, with the command to finish the job — and that is
 * the line still on screen when the install stops. This one is a hundred lines above it.
 */
function tokenGuidance(host) {
    return `[vsaf] ⚠ Chưa có credential cho ${host} — bỏ qua link nhóm này.`;
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
async function resolveInputs(entries, options = {}) {
    // A caller that names a credential means that one and no lookup — including a caller
    // that names `undefined` to say "pretend this machine has none". Everyone else gets the
    // chain: environment, then git's store, then the person at the terminal.
    const named = 'token' in options;
    const looked = new Map();
    const approved = new Set();
    const credentialFor = async (base) => {
        if (named) {
            const given = options.token;
            return typeof given === 'string' ? { secret: given, source: 'env' } : given;
        }
        // One lookup per host: twelve links to one server must not become twelve prompts.
        if (!looked.has(base)) {
            looked.set(base, (0, credentials_js_1.credentialForHost)(base, {
                env: options.env, run: options.run, isTTY: options.isTTY,
            }));
        }
        return looked.get(base);
    };
    const clone = [];
    const adopt = [];
    const unresolved = [];
    let toldAboutToken = false;
    for (const entry of entries) {
        if (!entry.trim())
            continue;
        const input = classifyInput(entry);
        if (input.kind === 'adopt') {
            adopt.push(input.path);
            continue;
        }
        if (input.kind === 'clone') {
            clone.push(input.url);
            continue;
        }
        const credential = await credentialFor(input.base);
        if (!credential) {
            // Once per run: repeating it for every link buries the instruction in itself.
            if (!toldAboutToken)
                console.log(tokenGuidance(new URL(input.base).host));
            toldAboutToken = true;
            unresolved.push({ entry, reason: 'không có credential cho máy chủ này' });
            continue;
        }
        try {
            const repos = await readGroupWithRetryOffer(input, credential, options);
            // It worked, so tell git to keep it — the step git takes after any successful command
            // of its own, and the one nothing takes here, because reading a repo list is a
            // `fetch`. Without it the password someone typed into their editor's popup was gone
            // by the next run, every run. Once per host: the second link to the same server has
            // nothing left to say.
            if (!approved.has(input.base)) {
                approved.add(input.base);
                (0, credentials_js_1.approveInGit)(input.base, credential, options.run);
            }
            if (repos.length === 0) {
                console.log(`[vsaf] ⚠ Nhóm dự án ${input.key} không có repo nào đọc được — bỏ qua link này.`);
                unresolved.push({ entry, reason: 'nhóm không có repo nào đọc được' });
                continue;
            }
            // Http before ssh: it is the same host the user just had open in a browser, so it
            // is reachable by definition and their credential helper already answers for it.
            // Ssh needs a key on the server and a port that is open — measured on
            // bitbucket.digital.vn, the ssh url the api advertises (port 8081) hangs, and the
            // port a page url would suggest (7999) refuses outright.
            const offered = repos
                .map(repo => ({ slug: repo.slug, url: repo.http ?? repo.ssh ?? '' }))
                .filter(repo => repo.url !== '');
            // A group of sixty repos is rarely a request for sixty repos. Asked per project, so
            // the numbers belong to one group and cannot be crossed with another's — and the
            // picker prints the numbered list itself, which is why nothing is listed above it.
            const chosen = await (0, pick_repos_js_1.askWhichRepos)(input.key, offered, {
                parent: options.beside,
                run: options.pickRun,
                isTTY: options.isTTY,
                ask: options.ask,
            });
            // Nothing chosen is a decision, not a failure: pressing Enter to skip a group must
            // not come back as a warning at the end of the install.
            for (const repo of chosen)
                clone.push(repo.url);
        }
        catch (error) {
            const why = error.message;
            console.log(`[vsaf] ⚠ Không đọc được nhóm dự án ${input.key} — ${why}`);
            // A timeout names no action on its own, and the one that fits is not the one a
            // person guesses. Measured against bitbucket.digital.vn while the account was
            // NOT locked: two reads in a row stalled for the full budget and the third
            // answered in 122 ms. So the fix is to ask again — not to hunt for a credential,
            // which is where the bare line "Quá hạn 15s" sends people.
            if (silentServer(why)) {
                console.log('[vsaf]   Đã chờ 45s — máy chủ này sinh danh sách ở lần hỏi đầu (đo được 20s),');
                console.log('[vsaf]   nên quá 45s là nó đang hỏng thật, không phải chậm.');
                console.log('[vsaf]   Đây KHÔNG phải lỗi token: token sai thì máy chủ trả lời ngay và báo 401.');
                console.log('[vsaf]   Dán thẳng url clone của từng repo thay cho link nhóm là đi tiếp được.');
            }
            console.log('[vsaf]   Bỏ qua link này, phần còn lại vẫn được cài.');
            unresolved.push({ entry, reason: why });
        }
    }
    return { clone: [...new Set(clone)], adopt: [...new Set(adopt)], unresolved };
}
/**
 * Read a project's repo list, and when the server stalls, offer to ask again here.
 *
 * The stall outlasts the retry window: measured on bitbucket.digital.vn, every attempt in
 * one run timed out and the identical link typed seconds later answered at once. What the
 * person then does is re-run the whole install and paste the link again — so the offer is
 * to spare them that, not to add patience the machine already spent. Only at a terminal:
 * a script has nobody to ask, and there it fails as before.
 */
async function readGroupWithRetryOffer(input, credential, options) {
    for (;;) {
        try {
            return await (0, bitbucket_js_1.listProjectRepos)(input.base, input.key, credential, options.fetchImpl ?? fetch);
        }
        catch (error) {
            const why = error.message;
            if (!silentServer(why) || !process.stdin.isTTY)
                throw error;
            console.log(`[vsaf] ⚠ ${input.key}: máy chủ nhận kết nối nhưng không trả lời.`);
            if (!(await askToAskAgain()))
                throw error;
        }
    }
}
/**
 * Wait at the prompt for permission to ask the server again.
 *
 * Through `readline`, not a raw read of fd 0: the repo question earlier in the same run
 * opens a readline interface over stdin and closes it, and after that a `readSync(0, …)`
 * comes back with zero bytes at once rather than blocking. The first version of this
 * offer did exactly that — it printed "Bấm Enter" and fell straight through to the
 * failure, which is worse than not offering, since the person is told they have a choice
 * they do not have. Measured against bitbucket.digital.vn on the run that found it.
 */
async function askToAskAgain() {
    if (!process.stdin.isTTY)
        return false;
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    try {
        await rl.question('[vsaf]   Enter để hỏi lại (khỏi chạy lại cả lệnh), Ctrl-C để bỏ qua link này: ');
        return true;
    }
    catch {
        return false; // Ctrl-D at the prompt reads as "give up on this link".
    }
    finally {
        rl.close();
    }
}
//# sourceMappingURL=resolve-inputs.js.map