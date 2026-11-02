/**
 * Unwire hooks whose command mentions any of the given script names, dropping
 * events left with no hooks. Hooks the user wired themselves are untouched
 * because their commands name none of these scripts.
 *
 * Returns the settings path, or null when nothing changed.
 */
export declare function unwireHooks(projectPath: string, scriptNames: string[]): string | null;
/**
 * Install a pack's hooks: copy the scripts into `.claude/hooks/` and wire them
 * into `.claude/settings.json`.
 *
 * A pack with no `hooks/` directory is not an error — most packs ship none.
 * Returns every path written, all of them inside the project.
 */
export declare function deployHooks(packDir: string, projectPath: string): string[];
/**
 * Fold a pack's event declarations into a repo's `.claude/settings.json`.
 *
 * The block has to live in the committed settings file: Claude Code replaces the
 * whole `hooks` block from `settings.local.json` rather than merging it, so a
 * local override would silently switch every hook off.
 *
 * Returns the settings path, or null when the pack declares no events.
 */
export declare function mergeWiring(wiringPath: string, projectPath: string): string | null;
/**
 * Give a code repo the same event hooks as the spec repo: a relative link to the
 * spec repo's committed `hooks/`, plus the events wired into its own settings.
 *
 * A link rather than a copy so one edit in the spec repo reaches every repo at
 * once. Where links are unavailable — Windows without developer mode — a copy
 * keeps the hooks working, at the cost of needing a reinstall after an edit.
 *
 * Returns the paths written inside the code repo.
 */
export declare function wireHooksInto(packDir: string, specRepo: string, codeRepo: string): string[];
//# sourceMappingURL=hooks.d.ts.map