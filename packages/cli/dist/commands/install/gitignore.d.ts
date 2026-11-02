/**
 * Drop the managed block, leaving every entry the user wrote themselves.
 * Returns the file path, or null when there was no block.
 */
export declare function removeGitignoreBlock(projectPath: string): string | null;
/**
 * Keep the installer's machine-local artifacts out of git through a marker block
 * that a reinstall rewrites wholesale — so switching policy (spec repo vs code
 * repo) cannot leave the previous policy's entries behind.
 *
 * Entries the user already ignores are left to them rather than duplicated.
 * Returns the `.gitignore` path, or null when there was nothing to manage.
 */
export declare function updateGitignore(projectPath: string, entries: string[]): string | null;
//# sourceMappingURL=gitignore.d.ts.map