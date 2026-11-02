"use strict";
/**
 * Read the repo list of a Bitbucket Server project.
 *
 * This is the whole point of accepting a project link: the list a person would otherwise
 * copy off the project page, one repo at a time, is a single read the tool can do.
 *
 * Only reads happen here, and only against the url the user pasted. The credential is put
 * in a header and is never written down, logged, or included in a message — an install
 * that leaks a credential into a workspace is worse than one that asks for twenty urls.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApiRefusal = void 0;
exports.listProjectRepos = listProjectRepos;
const credentials_js_1 = require("./credentials.js");
/** What the api serves per page unless asked otherwise. */
const PAGE_SIZE = 100;
/** The longest any single attempt waits — the ceiling used when reporting a timeout. */
const TIMEOUT_MS = 30_000;
/**
 * One attempt, and a patient one.
 *
 * Measured against bitbucket.digital.vn on this endpoint cold: dns 9 ms, connect 18 ms,
 * then **20.2 s** to the first byte — after which the same call answers in 70 ms. The
 * server builds the list on first ask and serves it from cache from then on.
 *
 * The old policy asked three times with 5 s, 5 s and 15 s. None of those could see a
 * 20-second answer, so all three aborted and the run called the server silent — while the
 * work they triggered finished anyway, which is exactly why the same link typed again
 * seconds later returned at once. Retrying a slow answer faster cannot help; waiting can.
 *
 * 30 s is that measurement with half again on top. One sample, so the margin is a
 * judgement, not a calculation; where a person is present the read offers to ask again
 * rather than guessing higher.
 */
const ATTEMPTS = [
    { waitMs: TIMEOUT_MS, thenPauseMs: 0 },
];
/**
 * The server answered, and the answer was no.
 *
 * The status is kept beside the sentence because one caller has to act on it: a 401 is the
 * only status worth trying a second credential form for, and reading that out of a
 * Vietnamese message would break the next time the message is reworded.
 */
class ApiRefusal extends Error {
    status;
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = 'ApiRefusal';
    }
}
exports.ApiRefusal = ApiRefusal;
function isPage(body) {
    return typeof body === 'object' && body !== null && Array.isArray(body.values);
}
/**
 * What to say about a status, in words that name the next thing to do.
 *
 * Never the token, or any part of it: a message is the easiest way for a credential to
 * end up in a terminal recording or a pasted bug report.
 */
function statusFailure(status, key) {
    // Not "đặt lại BITBUCKET_TOKEN" any more: the credential usually came from the machine's
    // git store, so the thing to fix is the entry git holds — or the account, when the
    // server is refusing it over a lock rather than over the secret.
    if (status === 401) {
        return 'Máy chủ không nhận credential này — token không đúng hoặc đã hết hạn.';
    }
    if (status === 403)
        return `Token thiếu quyền "Project read" trên nhóm ${key}.`;
    if (status === 404)
        return `Không có nhóm dự án nào tên "${key}" trên máy chủ này — kiểm tra lại key trong link.`;
    return `Máy chủ trả về HTTP ${status}.`;
}
/** What to say when the answer never arrived. */
function reachFailure(error, url, waitMs) {
    const host = (() => {
        try {
            return new URL(url).host;
        }
        catch {
            return url;
        }
    })();
    if (error?.name === 'AbortError') {
        return `Quá hạn ${waitMs / 1000}s khi chờ ${host} trả lời.`;
    }
    return `Không kết nối được tới ${host} — ${error?.message ?? 'không rõ nguyên nhân'}.`;
}
/**
 * Read one page, giving a silent server exactly one second chance.
 *
 * Measured on bitbucket.digital.vn: the first read after a burst of git traffic to the
 * same host times out at fifteen seconds five times out of nine, while `curl` answers in
 * sixty milliseconds a moment later — the server briefly stops answering a busy client.
 * Without the retry the whole feature quietly turns into "bỏ qua link này" and the user
 * is back to pasting urls one at a time.
 *
 * Only a silent server is retried. A rejection — 401, 403, 404 — is an answer, and asking
 * again cannot change it; on a forge that locks accounts after repeated failures, asking
 * again is actively harmful.
 */
async function readPageRetrying(url, key, authorization, fetchImpl) {
    for (let attempt = 0; attempt < ATTEMPTS.length; attempt += 1) {
        const { waitMs, thenPauseMs } = ATTEMPTS[attempt];
        const last = attempt === ATTEMPTS.length - 1;
        try {
            return await readPage(url, key, authorization, fetchImpl, waitMs);
        }
        catch (error) {
            // A rejection is an answer. Only silence is worth asking again about, and only
            // while there is another attempt left to ask with.
            if (last || !silentServer(error))
                throw error;
            console.log(`[vsaf] Máy chủ chưa trả lời — thử lại (${attempt + 2}/${ATTEMPTS.length})…`);
            await new Promise(resolve => setTimeout(resolve, thenPauseMs));
        }
    }
    // Unreachable: the last attempt either returns or throws. Here for the compiler.
    throw new Error(`Không đọc được nhóm dự án ${key}.`);
}
/** True when nothing came back at all: a timeout or a connection that never landed. */
function silentServer(error) {
    return /Quá hạn|Không kết nối được/.test(error?.message ?? '');
}
/** Read one page, or say plainly why it could not be read. */
async function readPage(url, key, authorization, fetchImpl, waitMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), waitMs);
    try {
        let response;
        try {
            response = await fetchImpl(url, {
                headers: { Authorization: authorization, Accept: 'application/json' },
                signal: controller.signal,
            });
        }
        catch (error) {
            throw new Error(reachFailure(error, url, waitMs));
        }
        if (!response.ok)
            throw new ApiRefusal(response.status, statusFailure(response.status, key));
        // A proxy or a login page answers 200 with html, which is not a failure the status
        // can describe.
        let body;
        try {
            body = await response.json();
        }
        catch {
            body = null;
        }
        if (!isPage(body))
            throw new Error('Phản hồi từ máy chủ không đọc được — không phải danh sách repo.');
        return body;
    }
    finally {
        clearTimeout(timer);
    }
}
/** Pick the clone urls out of a repo entry, keeping the hrefs exactly as served. */
function toRepo(value) {
    const entry = value;
    if (!entry?.slug)
        return null;
    const links = Array.isArray(entry.links?.clone) ? entry.links.clone : [];
    const href = (...names) => links.find(link => names.includes(String(link?.name)))?.href;
    const repo = { slug: entry.slug, name: entry.name ?? entry.slug };
    const ssh = href('ssh');
    const http = href('http', 'https');
    if (ssh)
        repo.ssh = ssh;
    if (http)
        repo.http = http;
    if (!ssh && !http) {
        console.log(`[vsaf] ⚠ ${repo.slug} không có url clone nào — bỏ qua`);
        return null;
    }
    return repo;
}
/**
 * The header for one form of the same credential.
 *
 * Built in `credentials.ts` now, beside the secret it wraps: the flows clone needs the
 * same header for the same server, and two copies of this would be two chances to pick
 * the wrong form.
 */
function header(credential, scheme) {
    return (0, credentials_js_1.authorizationHeader)(credential, scheme);
}
/**
 * True when the forge says this repo is archived.
 *
 * Bitbucket Data Center carries `archived` on every repository. Archived means read-only
 * and finished with, so offering one in a list of repos to bring into a project is offering
 * work that cannot be done — and a group of sixty is exactly where the retired ones pile
 * up. A server too old to send the field says nothing, and nothing is not "archived".
 *
 * Dropped without a word: an archived repo is not something the person chose and then lost,
 * it is something that was never on offer.
 */
function isArchived(value) {
    return value?.archived === true;
}
/** Read every page with one credential form, or fail on the first refusal. */
async function readAll(base, key, authorization, fetchImpl) {
    const root = base.replace(/\/+$/, '');
    const repos = [];
    let start = 0;
    for (;;) {
        const url = `${root}/rest/api/1.0/projects/${encodeURIComponent(key)}/repos?limit=${PAGE_SIZE}&start=${start}`;
        const page = await readPageRetrying(url, key, authorization, fetchImpl);
        for (const value of page.values) {
            if (isArchived(value))
                continue;
            const repo = toRepo(value);
            if (repo)
                repos.push(repo);
        }
        // A page that claims more but names no next one would otherwise be read forever.
        if (page.isLastPage !== false)
            break;
        if (typeof page.nextPageStart !== 'number' || page.nextPageStart <= start)
            break;
        start = page.nextPageStart;
    }
    return repos;
}
/**
 * List every repo of a project, following the pages to the end.
 *
 * The api serves a hundred at a time, so a project of more than a hundred repos looks
 * like a project of exactly a hundred to anything that reads the first page and stops.
 *
 * Two credential forms, at most, and only in this order. A credential taken from the
 * machine's git store is whatever that person typed the day they first cloned: on
 * Bitbucket Server that is usually a personal access token, which this server accepts as
 * `Bearer` and rejects as `Basic` — measured against bitbucket.digital.vn. But it can
 * equally be their login password, which is the other way round, and there is no way to
 * tell the two apart by looking.
 *
 * So a 401 buys exactly one more attempt in the other form. Not more, and not on any
 * other status: on Bitbucket Server a rejected credential counts as a failed login, and
 * three of those turn into a CAPTCHA lock that closes `git clone` for every repo in the
 * project — measured on this very account. 403 means the credential is fine and the
 * permission is not, so trying it a second way can only spend one of those three.
 *
 * `fetchImpl` exists so tests can answer without a network and without a credential;
 * nothing else should pass it.
 */
async function listProjectRepos(base, key, credential, fetchImpl = fetch) {
    // A bare string is a token and nothing else — the shape every caller used before the
    // credential could also come from git's store.
    const held = typeof credential === 'string'
        ? { secret: credential, source: 'env' }
        : credential;
    try {
        return await readAll(base, key, header(held, 'bearer'), fetchImpl);
    }
    catch (error) {
        const refused401 = error instanceof ApiRefusal && error.status === 401;
        if (!refused401 || !held.username)
            throw error;
        // Silent while it is still working. Which header form the server takes is machinery
        // the reader cannot act on, and the sentence that named the account lock read as a
        // threat for something the install had not done yet.
        try {
            return await readAll(base, key, header(held, 'basic'), fetchImpl);
        }
        catch (again) {
            if (!(again instanceof ApiRefusal))
                throw again;
            // Only now, and in what the person can do about it. No mention of Bearer or Basic:
            // both were tried, and neither is a thing they choose.
            throw new ApiRefusal(again.status, 'Máy chủ chưa nhận credential này. Kiểm tra lại token, hoặc mở Bitbucket trên'
                + ' trình duyệt đăng nhập lại một lần rồi thử lại — tránh chạy lại liên tục,'
                + ' vì nhiều lần liên tiếp sẽ bị máy chủ tạm chặn.');
        }
    }
}
//# sourceMappingURL=bitbucket.js.map