/** Pins the exact content of skills that come from outside this repo. */
export declare const LOCK_FILE = "skills-lock.json";
export interface LockedSkill {
    /** Where the skill came from, e.g. `owner/repo`. Recorded for humans. */
    source?: string;
    sourceType?: string;
    /** Path to the skill file, relative to the project root. */
    skillPath: string;
    computedHash: string;
}
export interface LockViolation {
    skill: string;
    reason: 'missing' | 'hash-mismatch';
    path: string;
    expected?: string;
    actual?: string;
}
export declare function computeSkillHash(filePath: string): string;
/**
 * Check every third-party skill against the hash the project pinned.
 *
 * A project with no lock file pins nothing and passes. A lock file that cannot be
 * parsed throws instead of passing: treating it as "no lock" would silently turn a
 * damaged pin into an unpinned install, which is the exact thing pinning prevents.
 *
 * Verification is purely local — nothing is fetched, so no network means no hang.
 */
export declare function verifySkillsLock(projectPath: string): LockViolation[];
/** Stop the install rather than deploy a third-party skill nobody vouched for. */
export declare function assertSkillsLock(projectPath: string): void;
//# sourceMappingURL=skills-lock.d.ts.map