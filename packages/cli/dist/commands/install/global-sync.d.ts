/** Record of everything written outside the project, so it can be taken back. */
export declare const MANIFEST_FILE: string;
/** What a pack declares in `pack.yaml` about writing outside the project. */
export interface GlobalDeclaration {
    pack: string;
    /** Tool directories, relative to home, that want a copy of the skills. */
    skillTargets: string[];
    /** Directory, relative to home, that wants the coding rules. */
    ruleTarget?: string;
}
export interface SyncOptions {
    /** Home directory to write into. Injected so tests never touch the real `~`. */
    home: string;
    canonicalDir: string;
    rulesDir?: string;
    declaration: GlobalDeclaration;
    /** Writing into personal configuration requires the user to say yes. */
    approved?: boolean;
}
/**
 * Push the pack's skills, and its rule files, into the tool directories the pack
 * declared — the only sanctioned way anything reaches outside the project.
 *
 * Three things gate it: the pack must declare the targets, the user must approve,
 * and every path written is recorded so `cleanupGlobal` can take back exactly
 * this installer's copies and nothing the user put there.
 */
export declare function syncToGlobal(options: SyncOptions): string[];
export interface CleanupOptions {
    home: string;
    pack: string;
}
/**
 * Take back what this installer wrote outside the project.
 *
 * Only entries named in the manifest are removed, so skills the user installed
 * for themselves survive. No manifest means no record of what was ours, and
 * removing nothing is then the only safe answer.
 */
export declare function cleanupGlobal(options: CleanupOptions): string[];
//# sourceMappingURL=global-sync.d.ts.map