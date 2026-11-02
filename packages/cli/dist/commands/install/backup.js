"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.backupIfModified = backupIfModified;
const fs_1 = require("fs");
/**
 * Preserve a file the user may have edited before the installer overwrites it.
 *
 * Pass `incoming` when the new content is already known: identical content means
 * there is nothing to preserve, and skipping avoids littering the project with
 * backups on every reinstall. Omit it when the caller edits the file in place.
 *
 * Returns the backup path, or null when no backup was needed.
 */
function backupIfModified(filePath, incoming) {
    if (!(0, fs_1.existsSync)(filePath))
        return null;
    if (incoming !== undefined) {
        try {
            if ((0, fs_1.readFileSync)(filePath, 'utf-8') === incoming)
                return null;
        }
        catch {
            // Unreadable: fall through and back it up anyway — better a spare copy than data loss.
        }
    }
    // Second-resolution stamps collide when two writes land in the same second,
    // so add a short random suffix to keep every earlier backup.
    const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 15);
    const suffix = Math.random().toString(36).slice(2, 6);
    const backupPath = `${filePath}.bak.${stamp}-${suffix}`;
    (0, fs_1.copyFileSync)(filePath, backupPath);
    return backupPath;
}
//# sourceMappingURL=backup.js.map