/**
 * Pick the project name: what the caller asked for, else the spec repo's own
 * directory name with a `-spec` or `-doc` suffix dropped, since those name the
 * repo rather than the project.
 */
export declare function resolveProjectName(specRepo: string, given?: string): string;
/**
 * Fill the project-name placeholder in the files that carry it.
 *
 * A file whose placeholder is already gone is left alone: the name there is a
 * decision someone made, and a reinstall must not overwrite it.
 *
 * Returns the files rewritten.
 */
export declare function applyProjectName(specRepo: string, projectName: string): string[];
//# sourceMappingURL=project-name.d.ts.map