/** Where IDEs look for skills. These are derived copies, not the source of truth. */
export declare const IDE_MIRRORS: readonly [".claude/skills", ".cursor/skills"];
export interface SkillTarget {
    /** Directory the pack's skills are written to. */
    target: string;
    /** Whether that directory needs mirroring for IDEs to see the skills. */
    mirror: boolean;
}
/**
 * Decide where a pack's skills belong.
 *
 * A pack that declares nothing keeps the existing behaviour — straight into
 * `.claude/skills` with no mirroring — so `sdlc` installs exactly as before.
 */
export declare function resolveSkillTarget(projectPath: string, canonical?: string): SkillTarget;
/**
 * Take back the copies mirroring made, using the ledger it wrote.
 *
 * The ledger is the only accurate list: a mirror of `.claude/skills` also carries
 * skills another pack put there, and those copies exist *because* this pack mirrored
 * them — leaving them behind would keep a directory alive that nothing maintains.
 * The canonical directory itself is never touched here; it holds the originals.
 *
 * Returns the paths removed.
 */
export declare function removeMirroredSkills(projectPath: string, canonicalDir: string): string[];
/**
 * Mirror the project's own skills — the ones a team writes for this project and
 * commits to the spec repo — into a code repo, so an IDE opened on that folder
 * offers them too.
 *
 * The pack's own skills are deliberately not copied here: they are installed per
 * project in the spec repo, and duplicating them into every code repo would add
 * megabytes per repo for no gain. A project with no skills of its own is the normal
 * starting state, and gets nothing written at all rather than empty directories.
 *
 * Returns the mirror directories written inside the code repo.
 */
export declare function mirrorProjectSkills(specRepo: string, codeRepo: string): string[];
/**
 * Refresh the IDE copies of the skills held in `canonicalDir`.
 *
 * Only copies this installer made are managed: a skill another pack wrote
 * straight into `.claude/skills` is left alone, and a skill that disappeared
 * from the canonical directory is removed from the mirrors.
 *
 * Returns the mirror directories written, all inside the project.
 */
export declare function mirrorToIde(projectPath: string, canonicalDir: string): string[];
//# sourceMappingURL=ide-mirror.d.ts.map