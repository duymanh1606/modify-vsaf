export interface UninstallOptions {
    /** Also take back what was written outside the project. */
    global?: boolean;
}
export interface UninstallResult {
    /** Paths removed from the project. */
    removed: string[];
    /** Skills left in place because another installed pack needs them. */
    kept: string[];
    /** Paths removed from outside the project. */
    globalRemoved: string[];
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
export declare function execUninstall(input: string, projectPath: string, options?: UninstallOptions): UninstallResult;
//# sourceMappingURL=uninstall.d.ts.map