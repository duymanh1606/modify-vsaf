"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MANIFEST_FILE = void 0;
exports.syncToGlobal = syncToGlobal;
exports.cleanupGlobal = cleanupGlobal;
const fs_1 = require("fs");
const path_1 = require("path");
/** Record of everything written outside the project, so it can be taken back. */
exports.MANIFEST_FILE = (0, path_1.join)('.vsaf', 'global-manifest.json');
function readManifest(home) {
    const path = (0, path_1.join)(home, exports.MANIFEST_FILE);
    if (!(0, fs_1.existsSync)(path))
        return {};
    try {
        return JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        return {}; // a damaged manifest loses cleanup history; it must not block anything
    }
}
function writeManifest(home, manifest) {
    const path = (0, path_1.join)(home, exports.MANIFEST_FILE);
    (0, fs_1.mkdirSync)((0, path_1.join)(home, '.vsaf'), { recursive: true });
    (0, fs_1.writeFileSync)(path, `${JSON.stringify(manifest, null, 2)}\n`, 'utf-8');
}
/** A declared target must stay under home — otherwise a pack could write anywhere. */
function resolveTarget(home, target) {
    const path = (0, path_1.resolve)(home, target);
    const inside = (0, path_1.relative)(home, path);
    if (inside.startsWith('..') || (0, path_1.isAbsolute)(inside)) {
        throw new Error(`Global target "${target}" resolves outside the home directory`);
    }
    return path;
}
function skillNames(dir) {
    if (!(0, fs_1.existsSync)(dir))
        return [];
    return (0, fs_1.readdirSync)(dir).filter(name => {
        const path = (0, path_1.join)(dir, name);
        return (0, fs_1.statSync)(path).isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(path, 'SKILL.md'));
    });
}
function ruleNames(dir) {
    if (!dir || !(0, fs_1.existsSync)(dir))
        return [];
    return (0, fs_1.readdirSync)(dir).filter(name => name.endsWith('.md'));
}
/**
 * Push the pack's skills, and its rule files, into the tool directories the pack
 * declared — the only sanctioned way anything reaches outside the project.
 *
 * Three things gate it: the pack must declare the targets, the user must approve,
 * and every path written is recorded so `cleanupGlobal` can take back exactly
 * this installer's copies and nothing the user put there.
 */
function syncToGlobal(options) {
    const { home, canonicalDir, rulesDir, declaration } = options;
    const skills = skillNames(canonicalDir);
    const rules = declaration.ruleTarget ? ruleNames(rulesDir) : [];
    if (declaration.skillTargets.length === 0 && rules.length === 0)
        return [];
    if (!options.approved) {
        throw new Error(`Pack "${declaration.pack}" writes outside the project into ${declaration.skillTargets.join(', ')}. `
            + 'Re-run with approval to allow it.');
    }
    const manifest = readManifest(home);
    const entry = {};
    const written = [];
    for (const target of declaration.skillTargets) {
        const dir = resolveTarget(home, target);
        (0, fs_1.mkdirSync)(dir, { recursive: true });
        for (const name of skills) {
            const dest = (0, path_1.join)(dir, name);
            (0, fs_1.rmSync)(dest, { recursive: true, force: true });
            (0, fs_1.cpSync)((0, path_1.join)(canonicalDir, name), dest, { recursive: true });
            written.push(dest);
        }
        entry[target] = skills;
    }
    if (declaration.ruleTarget && rules.length > 0) {
        const dir = resolveTarget(home, declaration.ruleTarget);
        (0, fs_1.mkdirSync)(dir, { recursive: true });
        for (const name of rules) {
            const dest = (0, path_1.join)(dir, name);
            (0, fs_1.copyFileSync)((0, path_1.join)(rulesDir, name), dest);
            written.push(dest);
        }
        entry[declaration.ruleTarget] = rules;
    }
    manifest[declaration.pack] = entry;
    writeManifest(home, manifest);
    written.push((0, path_1.join)(home, exports.MANIFEST_FILE));
    return written;
}
/**
 * Take back what this installer wrote outside the project.
 *
 * Only entries named in the manifest are removed, so skills the user installed
 * for themselves survive. No manifest means no record of what was ours, and
 * removing nothing is then the only safe answer.
 */
function cleanupGlobal(options) {
    const { home, pack } = options;
    const manifest = readManifest(home);
    const entry = manifest[pack];
    if (!entry)
        return [];
    const removed = [];
    for (const [target, names] of Object.entries(entry)) {
        const dir = resolveTarget(home, target);
        for (const name of names) {
            const path = (0, path_1.join)(dir, name);
            if (!(0, fs_1.existsSync)(path))
                continue;
            (0, fs_1.rmSync)(path, { recursive: true, force: true });
            removed.push(path);
        }
    }
    delete manifest[pack];
    writeManifest(home, manifest);
    return removed;
}
//# sourceMappingURL=global-sync.js.map