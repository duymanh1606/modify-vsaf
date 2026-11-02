"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.unwireHooks = unwireHooks;
exports.deployHooks = deployHooks;
exports.mergeWiring = mergeWiring;
exports.wireHooksInto = wireHooksInto;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
/** The file a pack uses to declare which events its hooks listen on. */
const WIRING_FILE = 'settings.json';
/** Hook scripts are invoked by the agent, so they have to carry the execute bit. */
function makeExecutable(dir) {
    for (const entry of (0, fs_1.readdirSync)(dir)) {
        const path = (0, path_1.join)(dir, entry);
        if ((0, fs_1.statSync)(path).isDirectory()) {
            makeExecutable(path);
        }
        else if (/\.(sh|py)$/.test(entry)) {
            (0, fs_1.chmodSync)(path, 0o755);
        }
    }
}
/** Same event and same matcher means the two groups describe the same trigger. */
function findGroup(groups, matcher) {
    return groups.find(g => g.matcher === matcher);
}
/**
 * Fold the pack's hook declarations into whatever the project already has.
 *
 * Merging by command string makes a repeated install a no-op instead of stacking
 * the same hook again, and leaves events the user configured themselves untouched.
 */
function mergeHooks(current, incoming) {
    const merged = { ...current };
    for (const [event, groups] of Object.entries(incoming)) {
        const target = merged[event] ? [...merged[event]] : [];
        for (const group of groups) {
            const existing = findGroup(target, group.matcher);
            if (!existing) {
                target.push(group);
                continue;
            }
            const seen = new Set(existing.hooks.map(h => h.command));
            existing.hooks = [...existing.hooks, ...group.hooks.filter(h => !seen.has(h.command))];
        }
        merged[event] = target;
    }
    return merged;
}
/**
 * Unwire hooks whose command mentions any of the given script names, dropping
 * events left with no hooks. Hooks the user wired themselves are untouched
 * because their commands name none of these scripts.
 *
 * Returns the settings path, or null when nothing changed.
 */
function unwireHooks(projectPath, scriptNames) {
    const settingsPath = (0, path_1.join)(projectPath, '.claude', WIRING_FILE);
    if (!(0, fs_1.existsSync)(settingsPath) || scriptNames.length === 0)
        return null;
    let settings;
    try {
        settings = JSON.parse((0, fs_1.readFileSync)(settingsPath, 'utf-8'));
    }
    catch {
        return null; // cannot edit what cannot be parsed; leave it to the user
    }
    const hooks = (settings.hooks ?? {});
    const ours = (command) => scriptNames.some(name => command.includes(name));
    const next = {};
    for (const [event, groups] of Object.entries(hooks)) {
        const kept = groups
            .map(group => ({ ...group, hooks: group.hooks.filter(hook => !ours(hook.command)) }))
            .filter(group => group.hooks.length > 0);
        // An event left with no hooks is residue: it still reads as "something is wired
        // here" to anyone looking at the file, and nothing runs.
        if (kept.length > 0)
            next[event] = kept;
    }
    const remaining = { ...settings };
    if (Object.keys(next).length > 0) {
        remaining.hooks = next;
    }
    else {
        delete remaining.hooks;
    }
    // Settings holding nothing but our block are ours to take back; anything the user
    // configured keeps the file alive.
    if (Object.keys(remaining).length === 0) {
        (0, fs_1.rmSync)(settingsPath, { force: true });
        return settingsPath;
    }
    (0, fs_1.writeFileSync)(settingsPath, `${JSON.stringify(remaining, null, 2)}\n`, 'utf-8');
    return settingsPath;
}
/**
 * Install a pack's hooks: copy the scripts into `.claude/hooks/` and wire them
 * into `.claude/settings.json`.
 *
 * A pack with no `hooks/` directory is not an error — most packs ship none.
 * Returns every path written, all of them inside the project.
 */
function deployHooks(packDir, projectPath) {
    const source = (0, path_1.join)(packDir, 'hooks');
    if (!(0, fs_1.existsSync)(source))
        return [];
    const written = [];
    // Two places on purpose, matching the layout the flow's documents describe:
    // `hooks/` at the repo root is the copy a team reads and commits, and the agent
    // reads its own copy under `.claude/`, which is machine-local and gitignored.
    const rootDir = (0, path_1.join)(projectPath, 'hooks');
    (0, fs_1.cpSync)(source, rootDir, {
        recursive: true,
        filter: src => (0, path_1.relative)(source, src) !== WIRING_FILE,
    });
    makeExecutable(rootDir);
    written.push(rootDir);
    const targetDir = (0, path_1.join)(projectPath, '.claude', 'hooks');
    // Repos set up by the older NTAPP template keep this path as a symlink to a
    // sibling directory. Copying a directory onto a symlink fails outright, so drop
    // the link first; the directory it pointed at keeps its own content.
    const existing = (0, fs_1.lstatSync)(targetDir, { throwIfNoEntry: false });
    if (existing && !existing.isDirectory()) {
        (0, fs_1.rmSync)(targetDir, { force: true });
    }
    (0, fs_1.mkdirSync)(targetDir, { recursive: true });
    // The wiring file describes the hooks; it is not a hook itself.
    (0, fs_1.cpSync)(source, targetDir, {
        recursive: true,
        filter: src => (0, path_1.relative)(source, src) !== WIRING_FILE,
    });
    makeExecutable(targetDir);
    written.push(targetDir);
    const settingsPath = mergeWiring((0, path_1.join)(source, WIRING_FILE), projectPath);
    if (settingsPath)
        written.push(settingsPath);
    return written;
}
/**
 * Fold a pack's event declarations into a repo's `.claude/settings.json`.
 *
 * The block has to live in the committed settings file: Claude Code replaces the
 * whole `hooks` block from `settings.local.json` rather than merging it, so a
 * local override would silently switch every hook off.
 *
 * Returns the settings path, or null when the pack declares no events.
 */
function mergeWiring(wiringPath, projectPath) {
    if (!(0, fs_1.existsSync)(wiringPath))
        return null;
    let declared;
    try {
        declared = (JSON.parse((0, fs_1.readFileSync)(wiringPath, 'utf-8')).hooks ?? {});
    }
    catch (error) {
        throw new Error(`Invalid hook wiring in ${wiringPath}: ${error.message}`);
    }
    const settingsPath = (0, path_1.join)(projectPath, '.claude', WIRING_FILE);
    let settings = {};
    if ((0, fs_1.existsSync)(settingsPath)) {
        try {
            settings = JSON.parse((0, fs_1.readFileSync)(settingsPath, 'utf-8'));
        }
        catch (error) {
            throw new Error(`Cannot merge hooks into malformed ${settingsPath}: ${error.message}`);
        }
    }
    const next = {
        ...settings,
        hooks: mergeHooks((settings.hooks ?? {}), declared),
    };
    const content = `${JSON.stringify(next, null, 2)}\n`;
    (0, fs_1.mkdirSync)((0, path_1.join)(projectPath, '.claude'), { recursive: true });
    (0, backup_js_1.backupIfModified)(settingsPath, content);
    (0, fs_1.writeFileSync)(settingsPath, content, 'utf-8');
    return settingsPath;
}
/**
 * Give a code repo the same event hooks as the spec repo: a relative link to the
 * spec repo's committed `hooks/`, plus the events wired into its own settings.
 *
 * A link rather than a copy so one edit in the spec repo reaches every repo at
 * once. Where links are unavailable — Windows without developer mode — a copy
 * keeps the hooks working, at the cost of needing a reinstall after an edit.
 *
 * Returns the paths written inside the code repo.
 */
function wireHooksInto(packDir, specRepo, codeRepo) {
    const source = (0, path_1.join)(specRepo, 'hooks');
    if (!(0, fs_1.existsSync)(source) || codeRepo === specRepo)
        return [];
    const written = [];
    const claudeDir = (0, path_1.join)(codeRepo, '.claude');
    const target = (0, path_1.join)(claudeDir, 'hooks');
    (0, fs_1.mkdirSync)(claudeDir, { recursive: true });
    // Whatever sits there was put there by an earlier install of this same pack;
    // replacing it is how a re-run picks up hooks the pack has added since.
    if ((0, fs_1.lstatSync)(target, { throwIfNoEntry: false })) {
        (0, fs_1.rmSync)(target, { recursive: true, force: true });
    }
    try {
        (0, fs_1.symlinkSync)((0, path_1.relative)(claudeDir, source), target, 'dir');
    }
    catch {
        (0, fs_1.cpSync)(source, target, { recursive: true });
        makeExecutable(target);
    }
    written.push(target);
    const settingsPath = mergeWiring((0, path_1.join)(packDir, 'hooks', WIRING_FILE), codeRepo);
    if (settingsPath)
        written.push(settingsPath);
    return written;
}
//# sourceMappingURL=hooks.js.map