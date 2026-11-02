"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.IDE_MIRRORS = void 0;
exports.resolveSkillTarget = resolveSkillTarget;
exports.removeMirroredSkills = removeMirroredSkills;
exports.mirrorProjectSkills = mirrorProjectSkills;
exports.mirrorToIde = mirrorToIde;
const fs_1 = require("fs");
const path_1 = require("path");
/** Where IDEs look for skills. These are derived copies, not the source of truth. */
exports.IDE_MIRRORS = ['.claude/skills', '.cursor/skills'];
/**
 * Names this installer put in each mirror, so a re-sync only touches its own copies.
 *
 * Kept out of `.vsaf/` on purpose. Two other places read `existsSync('.vsaf')` as
 * "this project has been initialised" — install decides whether to scaffold
 * workflows by it, and `vsaf init` refuses to run when it is there. Writing this
 * bookkeeping file used to create `.vsaf/` as a side effect, which flipped both:
 * a pack declaring `canonicalSkillsDir` (so mirroring runs at all) left every
 * fresh project looking initialised, and the documented `vsaf install` →
 * `vsaf init` sequence died on "already exists, pass --force" before writing any
 * config. `sdlc` never hit it only because it declares no canonical dir.
 */
const LEDGER = (0, path_1.join)('.claude', 'ide-mirror.json');
/** Pre-6.8.3 location. Read so an existing project keeps its cleanup history. */
const LEGACY_LEDGER = (0, path_1.join)('.vsaf', 'ide-mirror.json');
/**
 * Decide where a pack's skills belong.
 *
 * A pack that declares nothing keeps the existing behaviour — straight into
 * `.claude/skills` with no mirroring — so `sdlc` installs exactly as before.
 */
function resolveSkillTarget(projectPath, canonical) {
    if (!canonical) {
        return { target: (0, path_1.join)(projectPath, '.claude', 'skills'), mirror: false };
    }
    const target = (0, path_1.resolve)(projectPath, canonical);
    const inside = (0, path_1.relative)(projectPath, target);
    if (inside.startsWith('..') || (0, path_1.isAbsolute)(inside)) {
        throw new Error(`Canonical skill dir "${canonical}" resolves outside the project`);
    }
    return { target, mirror: true };
}
function readLedger(projectPath) {
    const path = [LEDGER, LEGACY_LEDGER]
        .map((name) => (0, path_1.join)(projectPath, name))
        .find((candidate) => (0, fs_1.existsSync)(candidate));
    if (!path)
        return {};
    try {
        return JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        return {}; // a damaged ledger loses cleanup history, but must not block installing
    }
}
function writeLedger(projectPath, ledger) {
    const path = (0, path_1.join)(projectPath, LEDGER);
    (0, fs_1.mkdirSync)((0, path_1.join)(projectPath, '.claude'), { recursive: true });
    (0, fs_1.writeFileSync)(path, `${JSON.stringify(ledger, null, 2)}\n`, 'utf-8');
    // A project installed before the move carries the old copy; drop it once its
    // contents have been rewritten here, so the two never drift apart.
    (0, fs_1.rmSync)((0, path_1.join)(projectPath, LEGACY_LEDGER), { force: true });
}
function skillNames(dir) {
    return (0, fs_1.readdirSync)(dir).filter(name => {
        const path = (0, path_1.join)(dir, name);
        return (0, fs_1.statSync)(path).isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(path, 'SKILL.md'));
    });
}
/**
 * Take back the copies mirroring made, using the ledger it wrote.
 *
 * The ledger is the only accurate list: a mirror of `.claude/skills` also carries
 * skills another pack put there, and those copies exist *because* this pack mirrored
 * them — leaving them behind would keep a directory alive that nothing maintains.
 * The canonical directory itself is never touched here; it holds the originals.
 *
 * Returns the paths removed.
 */
function removeMirroredSkills(projectPath, canonicalDir) {
    const ledger = readLedger(projectPath);
    const removed = [];
    for (const mirror of exports.IDE_MIRRORS) {
        const mirrorDir = (0, path_1.join)(projectPath, mirror);
        if (mirrorDir === canonicalDir || !(0, fs_1.existsSync)(mirrorDir))
            continue;
        for (const name of ledger[mirror] ?? []) {
            const path = (0, path_1.join)(mirrorDir, name);
            if (!(0, fs_1.existsSync)(path))
                continue;
            (0, fs_1.rmSync)(path, { recursive: true, force: true });
            removed.push(path);
        }
        delete ledger[mirror];
    }
    if (Object.keys(ledger).length === 0) {
        (0, fs_1.rmSync)((0, path_1.join)(projectPath, LEDGER), { force: true });
        (0, fs_1.rmSync)((0, path_1.join)(projectPath, LEGACY_LEDGER), { force: true });
    }
    else {
        writeLedger(projectPath, ledger);
    }
    return removed;
}
/**
 * Mirror the project's own skills — the ones a team writes for this project and
 * commits to the spec repo — into a code repo, so an IDE opened on that folder
 * offers them too.
 *
 * The pack's own skills are deliberately not copied here: they are installed per
 * project in the spec repo, and duplicating them into every code repo would add
 * megabytes per repo for no gain. A project with no skills of its own is the normal
 * starting state, and gets nothing written at all rather than empty directories.
 *
 * Returns the mirror directories written inside the code repo.
 */
function mirrorProjectSkills(specRepo, codeRepo) {
    const source = (0, path_1.join)(specRepo, '.agent', 'skills');
    if (codeRepo === specRepo || !(0, fs_1.existsSync)(source) || skillNames(source).length === 0)
        return [];
    return mirrorToIde(codeRepo, source);
}
/**
 * Refresh the IDE copies of the skills held in `canonicalDir`.
 *
 * Only copies this installer made are managed: a skill another pack wrote
 * straight into `.claude/skills` is left alone, and a skill that disappeared
 * from the canonical directory is removed from the mirrors.
 *
 * Returns the mirror directories written, all inside the project.
 */
function mirrorToIde(projectPath, canonicalDir) {
    if (!(0, fs_1.existsSync)(canonicalDir))
        return [];
    const names = skillNames(canonicalDir);
    const ledger = readLedger(projectPath);
    const written = [];
    for (const mirror of exports.IDE_MIRRORS) {
        const mirrorDir = (0, path_1.join)(projectPath, mirror);
        // A pack whose canonical directory is itself one of the IDE directories would
        // otherwise have each skill deleted and then copied from the hole left behind.
        if (mirrorDir === canonicalDir)
            continue;
        (0, fs_1.mkdirSync)(mirrorDir, { recursive: true });
        for (const stale of (ledger[mirror] ?? []).filter(name => !names.includes(name))) {
            (0, fs_1.rmSync)((0, path_1.join)(mirrorDir, stale), { recursive: true, force: true });
        }
        for (const name of names) {
            const dest = (0, path_1.join)(mirrorDir, name);
            (0, fs_1.rmSync)(dest, { recursive: true, force: true });
            (0, fs_1.cpSync)((0, path_1.join)(canonicalDir, name), dest, { recursive: true });
        }
        ledger[mirror] = names;
        written.push(mirrorDir);
    }
    writeLedger(projectPath, ledger);
    return written;
}
//# sourceMappingURL=ide-mirror.js.map