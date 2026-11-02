"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.repoKey = repoKey;
exports.reposAlreadyBeside = reposAlreadyBeside;
exports.parseSelection = parseSelection;
exports.inColumns = inColumns;
exports.offerLines = offerLines;
exports.askWhichRepos = askWhichRepos;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const path_1 = require("path");
const promises_1 = require("node:readline/promises");
const prompt_read_js_1 = require("./prompt-read.js");
/** How wide to assume the terminal is when it will not say. */
const FALLBACK_WIDTH = 80;
/** Gap between columns, wide enough that slugs do not read as one word. */
const GUTTER = 3;
const runGit = args => (0, child_process_1.execFileSync)('git', args, { encoding: 'utf-8', stdio: ['ignore', 'pipe', 'pipe'] });
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
function repoKey(url) {
    const cleaned = url.trim().replace(/\.git$/i, '').replace(/\/+$/, '');
    const segments = cleaned.split(/[/:]/).filter(Boolean);
    return segments.slice(-2).join('/').toLowerCase();
}
/**
 * The repos already sitting beside the project, by identity.
 *
 * Only immediate children, and only ones holding a `.git` — a directory of loose files is
 * not a repo, and walking deeper would find the repos inside a workspace nobody meant to
 * include. A child without an `origin` is skipped rather than guessed at.
 */
function reposAlreadyBeside(parent, run = runGit) {
    const found = new Map();
    let children;
    try {
        children = (0, fs_1.readdirSync)(parent, { withFileTypes: true })
            .filter(entry => entry.isDirectory())
            .map(entry => entry.name);
    }
    catch {
        return found; // No such directory yet: nothing is beside anything.
    }
    for (const name of children) {
        const path = (0, path_1.join)(parent, name);
        if (!(0, fs_1.existsSync)((0, path_1.join)(path, '.git')))
            continue;
        try {
            const url = run(['-C', path, 'remote', 'get-url', 'origin']).trim();
            if (url)
                found.set(repoKey(url), name);
        }
        catch {
            // A repo with no origin, or one git refuses to read. Neither is a match.
        }
    }
    return found;
}
/**
 * Read `1,3-5` — and `a`, and an empty line.
 *
 * Commas or spaces, either way: people type both, and rejecting one of them over
 * punctuation would be its own small insult. A number outside the list is reported, not
 * clamped: clamping `70` to `63` clones a repo nobody asked for.
 */
function parseSelection(answer, count) {
    const value = answer.trim();
    if (!value)
        return { picked: [], unknown: [] };
    if (/^a$/i.test(value)) {
        return { picked: Array.from({ length: count }, (_, at) => at), unknown: [] };
    }
    const picked = new Set();
    const unknown = [];
    for (const token of value.split(/[,\s]+/).filter(Boolean)) {
        const range = /^(\d+)\s*-\s*(\d+)$/.exec(token);
        if (range) {
            const from = Number(range[1]);
            const to = Number(range[2]);
            if (from < 1 || to > count || from > to) {
                unknown.push(token);
                continue;
            }
            for (let at = from; at <= to; at += 1)
                picked.add(at - 1);
            continue;
        }
        if (/^\d+$/.test(token)) {
            const one = Number(token);
            if (one < 1 || one > count)
                unknown.push(token);
            else
                picked.add(one - 1);
            continue;
        }
        unknown.push(token);
    }
    return { picked: [...picked].sort((left, right) => left - right), unknown };
}
/**
 * Lay labels out across the terminal, filling down each column.
 *
 * Down rather than across, so a list read top-to-bottom stays in order in the first
 * column — reading order matters more than packing when the numbers are what you type.
 */
function inColumns(labels, width = process.stdout.columns) {
    if (labels.length === 0)
        return [];
    // A terminal that reports 0 — a pty with no size set, a redirected stream — is a
    // terminal of unknown width, not a terminal eight characters wide. `?? FALLBACK` does
    // not catch it: `0 ?? 80` is 0, and every label then went on its own line.
    const usable = Number.isFinite(width) && width > 0
        ? width : FALLBACK_WIDTH;
    const widest = Math.max(...labels.map(label => label.length));
    const perRow = Math.max(1, Math.floor((usable - 8) / (widest + GUTTER)));
    const rows = Math.ceil(labels.length / perRow);
    const lines = [];
    for (let row = 0; row < rows; row += 1) {
        const cells = [];
        for (let column = 0; column < perRow; column += 1) {
            const label = labels[column * rows + row];
            if (label !== undefined)
                cells.push(label.padEnd(widest + GUTTER));
        }
        lines.push(cells.join('').trimEnd());
    }
    return lines;
}
/** Read one line at the terminal. Separate so the flow above can be driven by a test. */
async function atTerminal(question) {
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    try {
        return await rl.question(question);
    }
    finally {
        rl.close();
    }
}
/** The numbered lines to show, one per repo, marking the ones already on disk. */
function offerLines(repos, beside) {
    const pad = String(repos.length).length;
    return repos.map((repo, at) => {
        const here = beside.get(repoKey(repo.url));
        return `${String(at + 1).padStart(pad)} ${repo.slug}${here ? ` ✓đã có` : ''}`;
    });
}
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
async function askWhichRepos(key, repos, options = {}) {
    if (repos.length === 0)
        return [];
    const interactive = options.isTTY ?? process.stdin.isTTY ?? false;
    const beside = options.parent ? reposAlreadyBeside(options.parent, options.run) : new Map();
    if (!interactive)
        return repos;
    console.log(`[vsaf] ${key} — ${repos.length} repo:`);
    for (const line of inColumns(offerLines(repos, beside)))
        console.log(`[vsaf]   ${line}`);
    let answer;
    try {
        answer = await (options.ask ?? atTerminal)('[vsaf]   Clone repo nào? (1,3-5 · a = tất cả · Enter = bỏ qua): ');
    }
    catch (error) {
        // Ctrl-C or Ctrl-D at the prompt means "none from this project", and saying that back
        // to the person who just typed it would be noise.
        if ((0, prompt_read_js_1.promptWasCutOff)(error))
            return [];
        // Every other failure is an answer that got lost, and it has to be said. Returning an
        // empty list quietly here is how a typed `1-3` over 13 repos became "Chưa clone repo
        // nào" with no line of output anywhere: three repos asked for, none attempted, and
        // nothing on screen to tell the difference between that and pressing Enter.
        console.log(`[vsaf]   ⚠ Không đọc được câu trả lời cho ${key} — ${(0, prompt_read_js_1.promptFailureReason)(error)}`);
        console.log(`[vsaf]     Chưa chọn repo nào của ${key} — KHÔNG phải bạn bỏ qua, mà là câu trả lời`
            + ' bị mất. Làm lại riêng phần này:');
        console.log(`[vsaf]     vsaf install <flow> --clone <link nhóm ${key}>`);
        return [];
    }
    const { picked, unknown } = parseSelection(answer, repos.length);
    if (unknown.length > 0) {
        console.log(`[vsaf]   ⚠ Không hiểu: ${unknown.join(', ')} — bỏ qua phần đó.`);
    }
    const all = /^a$/i.test(answer.trim());
    const chosen = picked
        .map(at => repos[at])
        // `a` skips what is already here; a number does not.
        .filter(repo => !(all && beside.has(repoKey(repo.url))));
    return chosen;
}
//# sourceMappingURL=pick-repos.js.map