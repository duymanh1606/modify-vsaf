/** What a node produced: file/LOC deltas in the project dir during its execution window. */
export interface NodeOutputMetrics {
    filesCreated: number;
    filesModified: number;
    locAdded: number;
    locRemoved: number;
    /** Created files matching the artifact prefixes (e.g. .vsaf/docs/**). */
    artifactsCreated: number;
    /** Up to 20 created paths for drill-down (artifacts first). */
    createdPaths: string[];
    /**
     * Same numbers split by which repo they came from. Totals above are the sum.
     *
     * NTAPP runs dual-repo: design artifacts live in the spec repo, source and tests
     * in one or more code repos. Measuring only the spec repo counted the documents and
     * scored the code as zero — the reverse of the intended priority. Reporting both the
     * sum and the split lets a dashboard tell "wrote 300 lines of design" apart from
     * "wrote 300 lines of working code" instead of blending them into one meaningless figure.
     */
    byRole?: Record<RepoRole, RoleMetrics>;
}
/** Which repo a measurement came from. */
export type RepoRole = 'spec' | 'code';
export type RoleMetrics = Omit<NodeOutputMetrics, 'createdPaths' | 'byRole'>;
export interface OutputMetricsOptions {
    /** Created files under these prefixes count as artifacts. */
    artifactPrefixes?: string[];
    /** Paths under these prefixes are tool/engine noise and never counted. */
    excludePrefixes?: string[];
    /** New untracked files larger than this are counted as created but not line-counted. */
    maxFileBytes?: number;
    /**
     * Extra git roots to measure besides the project dir, e.g. the code repos a spec
     * repo is wired to. Absolute paths. A root that is not a git repo, or has no commit
     * yet, is skipped on its own — it never disables the others.
     */
    codeRoots?: string[];
}
export declare const DEFAULT_EXCLUDE_PREFIXES: string[];
/**
 * Measures per-node output by diffing two git snapshots of every measured repo
 * (VSAF's MCP mode has AI nodes write directly into the working tree). Snapshots
 * are cheap (`git status` + `git diff --numstat`); a failure at any point
 * disables metrics for that repo alone — telemetry never breaks a run.
 */
export declare class OutputMetricsCollector {
    private readonly artifactPrefixes;
    private readonly excludePrefixes;
    private readonly maxFileBytes;
    /** nodeId -> (root path -> snapshot). */
    private snapshots;
    /** Per root, not global: one non-git code repo must not silence the spec repo. */
    private gitAvailable;
    /** Keeps temp index names distinct when several roots are measured in one snapshot. */
    private indexSeq;
    /** Per root: `HEAD`, or the empty tree while the repo has no commit. */
    private diffBases;
    private readonly roots;
    constructor(projectPath: string, options?: OutputMetricsOptions);
    /** Capture every root's state right before a node starts. */
    snapshot(nodeId: string): void;
    /** Diff every root's current state against the node's start snapshot. */
    delta(nodeId: string): NodeOutputMetrics | null;
    /**
     * Deltas for one root. Created paths are appended to the shared drill-down lists so
     * artifacts still sort first across all roots.
     */
    private deltaForRoot;
    private takeSnapshot;
    /**
     * Line counts for every changed path, untracked files included.
     *
     * `git diff` ignores untracked files, so a node that rewrote an artifact it had not
     * committed measured as nothing at all — zero on every counter, not even "modified".
     * That is precisely the re-run case: the second pass over a slice rewrites files the
     * first pass left uncommitted, and reported doing nothing.
     *
     * Intent-to-add in a throwaway index fixes it: the real index is copied aside, every
     * untracked path is registered there with `add -N` (which records the path, not the
     * content), and the diff then reports those files with exact line counts. The project's
     * own index is never touched. Any failure falls back to the plain diff — a measurement
     * that misses untracked files beats a run that breaks over telemetry.
     */
    private numstat;
    /**
     * What `git diff` measures against. `HEAD` normally, the empty tree in a repo with no
     * commit yet — there, `HEAD` is not a revision and git exits non-zero, which used to
     * disable measurement for the whole repo. Silently: telemetry never breaks a run, so
     * every span in a freshly initialised project arrived with no output numbers at all,
     * and nothing said why. A project sits in exactly that state between `git init` and
     * its first commit, which is where a new NTAPP project starts.
     */
    private diffBase;
    private isExcluded;
    private git;
    private countLines;
}
//# sourceMappingURL=output-metrics.d.ts.map