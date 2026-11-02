export interface SyncOptions {
    /** Print the pack's script in full instead of only its warnings. */
    verbose?: boolean;
    dryRun?: boolean;
    skillsOnly?: boolean;
    rulesOnly?: boolean;
    clean?: boolean;
    /** Anything after a bare `--`, handed to the pack's script untouched. */
    passthrough?: string[];
}
/**
 * Push a pack's skill library and coding rules into the tool directories under the
 * user's home.
 *
 * Its own command rather than a flag on `install`, because the two answer to different
 * things. This one belongs to the machine: run once, shared by every project, and
 * needing no project to exist at all. Installing belongs to a project. Upstream keeps
 * them as two scripts for that reason, and folding them together would mean setting up
 * a project just to refresh a skill.
 *
 * It also covers the case a flag on `install` cannot: a fresh machine with no project
 * yet, where the editor should still show the skills.
 */
export declare function execSync(input: string, options?: SyncOptions): void;
//# sourceMappingURL=sync.d.ts.map