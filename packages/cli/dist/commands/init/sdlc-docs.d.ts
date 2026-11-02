/**
 * Scaffold the SDLC artifact tree: `.vsaf/docs/` with its trackers, a root
 * `CONTEXT.md`, and the index entries in `.gitignore`.
 *
 * Idempotent by design — re-running only fills gaps, so it is safe on a project
 * that has been carrying these documents for months.
 *
 * Returns the paths created or extended.
 */
export declare function scaffoldSdlcDocs(projectPath: string): string[];
//# sourceMappingURL=sdlc-docs.d.ts.map