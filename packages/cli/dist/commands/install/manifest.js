"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.recordPaths = recordPaths;
exports.recordInstall = recordInstall;
exports.readInstall = readInstall;
exports.forgetInstall = forgetInstall;
exports.allInstalls = allInstalls;
exports.otherInstalls = otherInstalls;
const fs_1 = require("fs");
const path_1 = require("path");
const spec_scaffold_js_1 = require("./spec-scaffold.js");
/** One file per installed pack, holding exactly what that install wrote. */
const IN_VSAF = (0, path_1.join)('.vsaf', 'installed');
/**
 * Where the record goes when the project has no `.vsaf/` yet.
 *
 * A project can hold the artifact tree long before anyone runs `vsaf init`, and an
 * install into it still has to be undoable. Creating `.vsaf/` to hold the record is
 * not an option: every later command reads that directory as "this project is
 * initialised", so making one behind the user's back changes what the tool does next.
 */
const IN_ARTIFACTS = (0, path_1.join)(spec_scaffold_js_1.ARTIFACT_ROOT, '.installed');
function isDir(path) {
    try {
        return (0, fs_1.statSync)(path).isDirectory();
    }
    catch {
        return false;
    }
}
/**
 * Every place this project's record for a pack may live, best first.
 *
 * `[0]` is where a new record is written; the whole list is what a read has to look
 * through. Two places rather than one because the single old location, `.vsaf/`,
 * does not exist in a project that was never initialised — and an install there
 * recorded nothing at all, which is how a half-finished install became impossible
 * to undo.
 *
 * An empty list means there is nowhere to write yet. That is reported, never fixed
 * by creating a directory the user did not ask for.
 */
function recordPaths(projectPath, pack) {
    return recordDirs(projectPath).map(dir => (0, path_1.join)(dir, `${pack}.json`));
}
/** Cùng danh sách chỗ như `recordPaths`, nhưng ở mức thư mục — để quét được cả sổ. */
function recordDirs(projectPath) {
    const places = [];
    if (isDir((0, path_1.join)(projectPath, '.vsaf')))
        places.push((0, path_1.join)(projectPath, IN_VSAF));
    if (isDir((0, path_1.join)(projectPath, spec_scaffold_js_1.ARTIFACT_ROOT)))
        places.push((0, path_1.join)(projectPath, IN_ARTIFACTS));
    return places;
}
function union(a = [], b = []) {
    return [...new Set([...a, ...b])].sort();
}
/** Fold an older record into a newer one, keeping everything either of them lists. */
function merge(previous, record) {
    return {
        ...record,
        previousCanonicalDirs: union(union(previous.previousCanonicalDirs, record.previousCanonicalDirs), previous.canonicalDir === record.canonicalDir ? [] : [previous.canonicalDir]),
        skills: union(previous.skills, record.skills),
        hooks: union(previous.hooks, record.hooks),
        rules: union(previous.rules, record.rules),
        commands: union(previous.commands, record.commands),
        hasWorkflows: previous.hasWorkflows || record.hasWorkflows,
        wired: union(previous.wired, record.wired),
        scopedRepos: union(previous.scopedRepos, record.scopedRepos),
        specConfig: record.specConfig ?? previous.specConfig,
    };
}
function readOne(path) {
    if (!(0, fs_1.existsSync)(path))
        return null;
    try {
        return JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        // An unreadable record means we cannot tell what was ours. Deleting on a guess
        // could take the user's own files, so treat it as nothing to remove.
        return null;
    }
}
/**
 * Write the record, folding in whatever an earlier install of the same pack left.
 *
 * Recording only what the current run created loses everything an earlier run made
 * and this one skipped as "already there" — the workflows, the generated config, the
 * skills in a directory the pack has since moved away from. Uninstall reads the
 * record, so anything that falls out of it becomes undeletable.
 *
 * Called after every step of an install rather than once at the end: a run that dies
 * half way still has to leave behind a list of what it made.
 *
 * Returns the file written, or null when the project offers nowhere to write one.
 */
function recordInstall(projectPath, record) {
    const [path] = recordPaths(projectPath, record.pack);
    if (!path)
        return null;
    const previous = readInstall(projectPath, record.pack);
    const merged = previous ? merge(previous, record) : record;
    (0, fs_1.mkdirSync)((0, path_1.dirname)(path), { recursive: true });
    (0, fs_1.writeFileSync)(path, `${JSON.stringify(merged, null, 2)}\n`, 'utf-8');
    return path;
}
let warnedAboutTwoRecords = false;
/**
 * The record for a pack, merged across every place one was found.
 *
 * Both places hold a true account of a different install, so the union is the only
 * safe reading: dropping either one leaves files nothing will ever remove.
 */
function readInstall(projectPath, pack) {
    const found = recordPaths(projectPath, pack)
        .map(readOne)
        .filter((record) => record !== null);
    if (found.length === 0)
        return null;
    // Said once a run: the record is read after every step of an install, and repeating
    // the same notice a dozen times would bury the lines that need reading.
    if (found.length > 1 && !warnedAboutTwoRecords) {
        warnedAboutTwoRecords = true;
        console.log(`[vsaf] Sổ cài đặt "${pack}" có ở cả .vsaf/ và ${spec_scaffold_js_1.ARTIFACT_ROOT}/ — đã gộp cả hai lại.`);
    }
    return found.reduce((all, record) => merge(all, record));
}
function forgetInstall(projectPath, pack) {
    for (const path of recordPaths(projectPath, pack))
        (0, fs_1.rmSync)(path, { force: true });
}
/**
 * Sổ cài đặt của mọi flow trong dự án này.
 *
 * Quét cả hai chỗ và gộp lại, cùng luật với `readInstall`. Dùng cho `vsaf status`: §6 spec
 * hứa "bản flow đang dùng … hiện ra ở `vsaf status`", và hai trường `flowOrigin` /
 * `flowCommit` được ghi từ nhánh trước nhưng chưa ai đọc — nên câu "máy này đang chạy bản
 * flow nào" vẫn chưa trả lời được bằng một lệnh.
 */
function allInstalls(projectPath) {
    const byPack = new Map();
    for (const dir of recordDirs(projectPath)) {
        // `recordDirs` trả về chỗ được PHÉP ghi, không phải chỗ đã có: một dự án có `.vsaf/`
        // mà chưa cài gì thì `.vsaf/installed/` chưa tồn tại, và `readdirSync` ở đó ném ENOENT.
        if (!isDir(dir))
            continue;
        for (const file of (0, fs_1.readdirSync)(dir)) {
            if (!file.endsWith('.json'))
                continue;
            const record = readOne((0, path_1.join)(dir, file));
            if (!record)
                continue;
            const seen = byPack.get(record.pack);
            byPack.set(record.pack, seen ? merge(seen, record) : record);
        }
    }
    return [...byPack.values()].sort((a, b) => a.pack.localeCompare(b.pack));
}
/**
 * Records of every other installed pack — what must not be removed.
 *
 * Both locations are scanned. Missing one means missing a pack, and an uninstall
 * that cannot see a pack takes the skills that pack still reads.
 */
function otherInstalls(projectPath, pack) {
    const byPack = new Map();
    for (const path of recordPaths(projectPath, pack)) {
        const dir = (0, path_1.dirname)(path);
        if (!isDir(dir))
            continue;
        for (const file of (0, fs_1.readdirSync)(dir)) {
            if (!file.endsWith('.json') || file === `${pack}.json`)
                continue;
            const record = readOne((0, path_1.join)(dir, file));
            if (!record)
                continue;
            const seen = byPack.get(record.pack);
            byPack.set(record.pack, seen ? merge(seen, record) : record);
        }
    }
    return [...byPack.values()];
}
//# sourceMappingURL=manifest.js.map