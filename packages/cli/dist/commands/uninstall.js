"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execUninstall = execUninstall;
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
const manifest_js_1 = require("./install/manifest.js");
const skill_js_1 = require("./skill.js");
const ide_mirror_js_1 = require("./install/ide-mirror.js");
const hooks_js_1 = require("./install/hooks.js");
const rules_js_1 = require("./install/rules.js");
const repo_scope_js_1 = require("./install/repo-scope.js");
const gitignore_js_1 = require("./install/gitignore.js");
const global_sync_js_1 = require("./install/global-sync.js");
const spec_scaffold_js_1 = require("./install/spec-scaffold.js");
/**
 * Drop directories left empty once their files are gone, deepest first. An empty
 * `.claude/hooks` reads as "hooks are installed" to anyone looking.
 *
 * Two boundaries, both learned the hard way. The project root is never pruned: a
 * removed file at the root makes `dirname` the root itself, and pruning from there
 * walks the whole project deleting any empty directory — including the user's own.
 * And `.git` is never entered: a repo with no commits yet has empty `refs/heads`,
 * `refs/tags` and `branches`, so pruning them leaves git reporting "not a git
 * repository" and the repo unusable.
 */
function pruneEmptyDirs(dir, projectPath) {
    const inside = (0, path_1.relative)(projectPath, dir);
    if (inside === '' || inside.startsWith('..') || (0, path_1.isAbsolute)(inside))
        return;
    if (inside.split(path_1.sep).includes('.git'))
        return;
    if (!(0, fs_1.existsSync)(dir))
        return;
    for (const entry of (0, fs_1.readdirSync)(dir, { withFileTypes: true })) {
        if (entry.isDirectory())
            pruneEmptyDirs((0, path_1.join)(dir, entry.name), projectPath);
    }
    if ((0, fs_1.readdirSync)(dir).length === 0)
        (0, fs_1.rmSync)(dir, { recursive: true, force: true });
}
/** Files a hook run leaves behind: compiled bytecode and its cache directories. */
function removeGenerated(dir, removed) {
    if (!(0, fs_1.existsSync)(dir))
        return;
    for (const entry of (0, fs_1.readdirSync)(dir, { withFileTypes: true })) {
        const path = (0, path_1.join)(dir, entry.name);
        if (entry.isDirectory()) {
            if (entry.name === '__pycache__') {
                (0, fs_1.rmSync)(path, { recursive: true, force: true });
                removed.push(path);
            }
            else {
                removeGenerated(path, removed);
            }
            continue;
        }
        if (entry.name.endsWith('.pyc')) {
            (0, fs_1.rmSync)(path, { force: true });
            removed.push(path);
        }
    }
}
/**
 * Remove a pack, using the record written at install time.
 *
 * Without that record there is no way to tell the pack's files from the user's,
 * so an unrecorded pack removes nothing rather than deleting on a guess. Skills
 * another installed pack also declares are kept and reported — four bundled
 * skills are shared between `sdlc` and `NTAPP`, and taking them would break
 * whichever pack stays.
 */
function execUninstall(input, projectPath, options = {}) {
    // The record was written under the pack's canonical name, so read it by that.
    const pack = (0, skill_js_1.resolvePackName)(input);
    const record = (0, manifest_js_1.readInstall)(projectPath, pack);
    if (!record) {
        console.log(`[vsaf] No install record for "${pack}" — nothing to remove`);
        return { removed: [], kept: [], globalRemoved: [] };
    }
    const others = (0, manifest_js_1.otherInstalls)(projectPath, pack);
    const removed = [];
    const kept = [];
    /**
     * A skill is kept only in the directory the other pack actually uses. Keeping it
     * everywhere would leave copies in this pack's own directories, which no
     * remaining pack reads — residue that looks installed but is not.
     */
    const neededIn = (dir, skill) => others.some(other => (0, path_1.join)(projectPath, other.canonicalDir) === dir && other.skills.includes(skill));
    // Skills: the canonical copy and every IDE mirror of it.
    const skillDirs = [
        (0, path_1.join)(projectPath, record.canonicalDir),
        // Directories earlier installs used, so moving the canonical dir does not orphan
        // the copies left in the old one.
        ...(record.previousCanonicalDirs ?? []).map(dir => (0, path_1.join)(projectPath, dir)),
        ...ide_mirror_js_1.IDE_MIRRORS.map(m => (0, path_1.join)(projectPath, m)),
    ];
    for (const skill of record.skills) {
        let keptAnywhere = false;
        for (const dir of skillDirs) {
            const path = (0, path_1.join)(dir, skill);
            if (!(0, fs_1.existsSync)(path))
                continue;
            if (neededIn(dir, skill)) {
                keptAnywhere = true;
                continue;
            }
            (0, fs_1.rmSync)(path, { recursive: true, force: true });
            removed.push(path);
        }
        if (keptAnywhere)
            kept.push(skill);
    }
    // The IDE copies this pack made, which include skills another pack owns: those
    // copies only exist because this pack mirrored them.
    removed.push(...(0, ide_mirror_js_1.removeMirroredSkills)(projectPath, (0, path_1.join)(projectPath, record.canonicalDir)));
    // An IDE directory emptied of every skill still reads as "skills are installed".
    // Pruning is safe by definition: a directory another pack still uses is not empty.
    for (const dir of skillDirs) {
        pruneEmptyDirs(dir, projectPath);
        pruneEmptyDirs((0, path_1.dirname)(dir), projectPath);
    }
    // Hooks: unwire first so no event is left pointing at a script that is gone.
    const settingsPath = (0, hooks_js_1.unwireHooks)(projectPath, record.hooks);
    if (settingsPath)
        removed.push(settingsPath);
    // Two copies to take back: the one at the repo root and the agent's own.
    for (const dir of [(0, path_1.join)(projectPath, 'hooks'), (0, path_1.join)(projectPath, '.claude', 'hooks')]) {
        for (const hook of record.hooks) {
            const path = (0, path_1.join)(dir, hook);
            if (!(0, fs_1.existsSync)(path))
                continue;
            (0, fs_1.rmSync)(path, { force: true });
            removed.push(path);
        }
        removeGenerated(dir, removed);
        pruneEmptyDirs(dir, projectPath);
    }
    // Rules: the files, then the import block pointing at them.
    for (const rule of record.rules) {
        const path = (0, path_1.join)(projectPath, 'rules', rule);
        if (!(0, fs_1.existsSync)(path))
            continue;
        (0, fs_1.rmSync)(path, { force: true });
        removed.push(path);
    }
    if (record.rules.length > 0) {
        pruneEmptyDirs((0, path_1.join)(projectPath, 'rules'), projectPath);
        const claudeMd = (0, rules_js_1.removeRulesImport)(projectPath);
        if (claudeMd)
            removed.push(claudeMd);
    }
    // Workflows and slash commands.
    const workflowsDir = (0, path_1.join)(projectPath, '.vsaf', 'workflows', pack);
    if (record.hasWorkflows && (0, fs_1.existsSync)(workflowsDir)) {
        (0, fs_1.rmSync)(workflowsDir, { recursive: true, force: true });
        removed.push(workflowsDir);
    }
    for (const command of record.commands) {
        const path = (0, path_1.join)(projectPath, '.vsaf', 'commands', command);
        if (!(0, fs_1.existsSync)(path))
            continue;
        (0, fs_1.rmSync)(path, { force: true });
        removed.push(path);
    }
    // The gitignore block only listed paths this pack generates.
    const gitignore = (0, gitignore_js_1.removeGitignoreBlock)(projectPath);
    if (gitignore)
        removed.push(gitignore);
    // What the multi-repo wiring created — including in sibling repos. Recorded
    // relative to this project, so resolve before removing, and only remove what the
    // record names: never a whole directory in someone else's repo.
    for (const entry of record.wired ?? []) {
        const path = (0, path_1.resolve)(projectPath, entry);
        if (!(0, fs_1.existsSync)(path) && !(0, fs_1.lstatSync)(path, { throwIfNoEntry: false }))
            continue;
        (0, fs_1.rmSync)(path, { recursive: true, force: true });
        removed.push(path);
        // `docs/Process` leaves a bare `docs/` behind; a directory kept only by what was
        // just deleted is residue.
        pruneEmptyDirs((0, path_1.dirname)(path), projectPath);
    }
    // The artifact tree: keep it when it holds work, drop it when it holds nothing. It
    // was created by installing, so an empty one is residue like any other.
    pruneEmptyDirs((0, path_1.join)(projectPath, spec_scaffold_js_1.ARTIFACT_ROOT), projectPath);
    // Each wired code repo, repaired rather than emptied: these files hold the repo's
    // own content next to ours, so only our block or our own entries come out. Deleting
    // them outright once took a code repo's CLAUDE.md with it.
    for (const entry of record.scopedRepos ?? []) {
        const repo = (0, path_1.resolve)(projectPath, entry);
        if (!(0, fs_1.existsSync)(repo))
            continue;
        for (const path of [
            (0, repo_scope_js_1.removeScopeBlock)(repo),
            (0, rules_js_1.removeRulesImport)(repo),
            (0, gitignore_js_1.removeGitignoreBlock)(repo),
            (0, hooks_js_1.unwireHooks)(repo, record.hooks),
        ]) {
            if (path)
                removed.push(path);
        }
        // Our copies of the rule files, and the IDE copies of the project's own skills.
        for (const rule of record.rules) {
            const path = (0, path_1.join)(repo, 'rules', rule);
            if (!(0, fs_1.existsSync)(path))
                continue;
            (0, fs_1.rmSync)(path, { force: true });
            removed.push(path);
        }
        pruneEmptyDirs((0, path_1.join)(repo, 'rules'), repo);
        removed.push(...(0, ide_mirror_js_1.removeMirroredSkills)(repo, (0, path_1.join)(repo, '.claude', 'skills')));
        for (const mirror of ide_mirror_js_1.IDE_MIRRORS)
            pruneEmptyDirs((0, path_1.join)(repo, mirror), repo);
    }
    const globalRemoved = options.global ? (0, global_sync_js_1.cleanupGlobal)({ home: (0, os_1.homedir)(), pack }) : [];
    (0, manifest_js_1.forgetInstall)(projectPath, pack);
    console.log(`[vsaf] Removed ${removed.length} path(s) for "${pack}"`);
    if (kept.length > 0) {
        console.log(`[vsaf] Kept ${kept.length} skill(s) another installed pack needs: ${kept.join(', ')}`);
    }
    if (globalRemoved.length > 0) {
        console.log(`[vsaf] Removed ${globalRemoved.length} path(s) outside the project`);
    }
    return { removed, kept, globalRemoved };
}
//# sourceMappingURL=uninstall.js.map