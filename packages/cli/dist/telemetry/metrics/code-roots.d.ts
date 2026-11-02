/**
 * The code repos belonging to a spec repo, for output measurement.
 *
 * A dual-repo project keeps its documents in one git repo and its source in others,
 * so measuring only the run's project dir scores the design and reports the code as
 * zero. `telemetry.artifacts.code_roots` names the repos explicitly; with nothing
 * configured we read the workspace file `vsaf install` already writes and maintains,
 * so an existing project needs no new setup to be measured correctly.
 *
 * Returns absolute paths of directories that exist and are git repos. Never throws:
 * an unreadable or hand-mangled workspace file yields no extra roots, which degrades
 * to the old spec-repo-only numbers rather than breaking the run.
 */
export declare function resolveCodeRoots(projectPath: string, configured?: string[]): string[];
//# sourceMappingURL=code-roots.d.ts.map