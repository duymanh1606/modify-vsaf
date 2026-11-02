import type { InstallRecord } from './manifest.js';
/**
 * Check that what the install claims to have written is really usable.
 *
 * Every check is against the install record, so it verifies the promise actually
 * made rather than a fixed expectation. Catching this here matters because the
 * failures are all silent ones: a hook missing its execute bit never runs, a link
 * resolving nowhere fails only when a skill reads through it, and a missing
 * workflow directory shows up as "no workflows" long after installing.
 *
 * Returns one line per problem found; empty means the install is sound.
 */
export declare function selfTest(projectPath: string, record: InstallRecord): string[];
//# sourceMappingURL=selftest.d.ts.map