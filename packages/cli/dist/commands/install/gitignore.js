"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.removeGitignoreBlock = removeGitignoreBlock;
exports.updateGitignore = updateGitignore;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
const BLOCK_BEGIN = '# >>> vsaf install (auto-managed, do not edit) >>>';
const BLOCK_END = '# <<< vsaf install <<<';
/** Everything except the managed block — i.e. the part that belongs to the user. */
function stripBlock(content) {
    const start = content.indexOf(BLOCK_BEGIN);
    const end = content.indexOf(BLOCK_END);
    if (start === -1 || end <= start)
        return content;
    return content.slice(0, start) + content.slice(end + BLOCK_END.length);
}
function entriesOutsideBlock(content) {
    return new Set(stripBlock(content)
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0 && !line.startsWith('#')));
}
/**
 * Drop the managed block, leaving every entry the user wrote themselves.
 * Returns the file path, or null when there was no block.
 */
function removeGitignoreBlock(projectPath) {
    const path = (0, path_1.join)(projectPath, '.gitignore');
    if (!(0, fs_1.existsSync)(path))
        return null;
    const current = (0, fs_1.readFileSync)(path, 'utf-8');
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    if (start === -1 || end <= start)
        return null;
    const next = (current.slice(0, start) + current.slice(end + BLOCK_END.length)).replace(/\n{3,}$/, '\n');
    (0, fs_1.writeFileSync)(path, next, 'utf-8');
    return path;
}
/**
 * Keep the installer's machine-local artifacts out of git through a marker block
 * that a reinstall rewrites wholesale — so switching policy (spec repo vs code
 * repo) cannot leave the previous policy's entries behind.
 *
 * Entries the user already ignores are left to them rather than duplicated.
 * Returns the `.gitignore` path, or null when there was nothing to manage.
 */
function updateGitignore(projectPath, entries) {
    if (entries.length === 0)
        return null;
    const path = (0, path_1.join)(projectPath, '.gitignore');
    const current = (0, fs_1.existsSync)(path) ? (0, fs_1.readFileSync)(path, 'utf-8') : '';
    const alreadyIgnored = entriesOutsideBlock(current);
    const managed = entries.filter(entry => !alreadyIgnored.has(entry.trim()));
    const block = managed.length > 0
        ? [BLOCK_BEGIN, ...managed, BLOCK_END].join('\n')
        : '';
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    let next;
    if (start !== -1 && end > start) {
        next = current.slice(0, start) + block + current.slice(end + BLOCK_END.length);
    }
    else {
        const base = current.length === 0 || current.endsWith('\n') ? current : `${current}\n`;
        next = block.length > 0 ? `${base}${block}\n` : base;
    }
    (0, backup_js_1.backupIfModified)(path, next);
    (0, fs_1.writeFileSync)(path, next, 'utf-8');
    return path;
}
//# sourceMappingURL=gitignore.js.map