/**
 * Real package version, read from the root package.json at runtime.
 *
 * Walks up from this file (dist/commands/install → … → package root) and picks the
 * first package.json whose name is the published root (`…/vsaf`), skipping the
 * workspace's own `@vsaf/cli`. Reading it at runtime keeps `vsaf --version` truthful
 * after a release bump — the previous hardcoded '0.1.0' reported the (never-bumped)
 * workspace version instead.
 *
 * Lives here rather than in `index.ts` because the install path needs it too: the
 * `requiresEngine` gate compares a flow's demand against this number, and a version it
 * cannot read means the gate never refuses anything. Left unexported in `index.ts` it
 * was unreachable from there, so the gate would have passed every flow in silence.
 */
export declare function resolveEngineVersion(): string;
//# sourceMappingURL=engine-version.d.ts.map