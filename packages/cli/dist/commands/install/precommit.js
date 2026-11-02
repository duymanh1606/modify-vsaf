"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.installPreCommitHook = installPreCommitHook;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
/**
 * Where a pack keeps the hook, and where git expects it.
 *
 * Kept apart from the pack's `hooks/` directory on purpose: those are the agent's
 * event hooks, copied into the project and wired into its settings. This one is a
 * git hook, and mixing them would install each in the wrong place.
 */
const SOURCE = (0, path_1.join)('git-hooks', 'pre-commit');
const TARGET = (0, path_1.join)('.git', 'hooks', 'pre-commit');
/**
 * Install the pack's pre-commit hook into a repo.
 *
 * Skips a directory that is not a git repo rather than failing: a workspace often
 * holds a mix, and the rest of the install has nothing to do with git.
 *
 * A hook already in place is copied aside first — it may be the user's own. Only
 * when it differs from the one being installed: backing up unconditionally left a
 * fresh `.bak` in every repo on every run, and re-running the install is the normal
 * way to finish one that stopped half way, so the copies piled up.
 *
 * Returns the hook path, or null when there was nothing to install.
 */
function installPreCommitHook(packDir, repoPath) {
    const source = (0, path_1.join)(packDir, SOURCE);
    if (!(0, fs_1.existsSync)(source))
        return null;
    const hooksDir = (0, path_1.join)(repoPath, '.git', 'hooks');
    if (!(0, fs_1.existsSync)(hooksDir))
        return null;
    const target = (0, path_1.join)(repoPath, TARGET);
    (0, backup_js_1.backupIfModified)(target, (0, fs_1.readFileSync)(source, 'utf-8'));
    (0, fs_1.copyFileSync)(source, target);
    (0, fs_1.chmodSync)(target, 0o755);
    return target;
}
//# sourceMappingURL=precommit.js.map