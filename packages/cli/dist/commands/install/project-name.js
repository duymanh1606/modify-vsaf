"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveProjectName = resolveProjectName;
exports.applyProjectName = applyProjectName;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
const PLACEHOLDER = '<PROJECT_NAME>';
/** Files the pack ships with the placeholder in them. */
const TARGETS = ['CLAUDE.md', (0, path_1.join)('_bmad', 'bmm', 'config.yaml')];
/**
 * Pick the project name: what the caller asked for, else the spec repo's own
 * directory name with a `-spec` or `-doc` suffix dropped, since those name the
 * repo rather than the project.
 */
function resolveProjectName(specRepo, given) {
    if (given)
        return given;
    return (0, path_1.basename)(specRepo).replace(/-(doc|spec)$/, '');
}
/**
 * Fill the project-name placeholder in the files that carry it.
 *
 * A file whose placeholder is already gone is left alone: the name there is a
 * decision someone made, and a reinstall must not overwrite it.
 *
 * Returns the files rewritten.
 */
function applyProjectName(specRepo, projectName) {
    const written = [];
    for (const target of TARGETS) {
        const path = (0, path_1.join)(specRepo, target);
        if (!(0, fs_1.existsSync)(path))
            continue;
        const current = (0, fs_1.readFileSync)(path, 'utf-8');
        if (!current.includes(PLACEHOLDER))
            continue;
        const next = current.replaceAll(PLACEHOLDER, projectName);
        (0, backup_js_1.backupIfModified)(path, next);
        (0, fs_1.writeFileSync)(path, next, 'utf-8');
        written.push(path);
    }
    return written;
}
//# sourceMappingURL=project-name.js.map