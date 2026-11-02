/**
 * Preserve a file the user may have edited before the installer overwrites it.
 *
 * Pass `incoming` when the new content is already known: identical content means
 * there is nothing to preserve, and skipping avoids littering the project with
 * backups on every reinstall. Omit it when the caller edits the file in place.
 *
 * Returns the backup path, or null when no backup was needed.
 */
export declare function backupIfModified(filePath: string, incoming?: string): string | null;
//# sourceMappingURL=backup.d.ts.map