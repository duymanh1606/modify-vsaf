"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OutputMetricsCollector = exports.DEFAULT_EXCLUDE_PREFIXES = void 0;
// packages/cli/src/telemetry/metrics/output-metrics.ts
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
const EMPTY_ROLE = {
    filesCreated: 0, filesModified: 0, locAdded: 0, locRemoved: 0, artifactsCreated: 0,
};
const DEFAULT_ARTIFACT_PREFIXES = ['.vsaf/docs/'];
// Internal files written by Claude Code / the VSAF engine during a node's
// window (settings tmp files, run storage, session marker, worktrees).
exports.DEFAULT_EXCLUDE_PREFIXES = ['.claude/', '.vsaf/storage/', '.vsaf/worktrees/', '.vsaf/.claude-session'];
const DEFAULT_MAX_FILE_BYTES = 1_000_000;
/** git's constant hash for the empty tree — a diff base that exists in every repo. */
const EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904';
/**
 * Measures per-node output by diffing two git snapshots of every measured repo
 * (VSAF's MCP mode has AI nodes write directly into the working tree). Snapshots
 * are cheap (`git status` + `git diff --numstat`); a failure at any point
 * disables metrics for that repo alone — telemetry never breaks a run.
 */
class OutputMetricsCollector {
    artifactPrefixes;
    excludePrefixes;
    maxFileBytes;
    /** nodeId -> (root path -> snapshot). */
    snapshots = new Map();
    /** Per root, not global: one non-git code repo must not silence the spec repo. */
    gitAvailable = new Map();
    /** Keeps temp index names distinct when several roots are measured in one snapshot. */
    indexSeq = 0;
    /** Per root: `HEAD`, or the empty tree while the repo has no commit. */
    diffBases = new Map();
    roots;
    constructor(projectPath, options = {}) {
        this.artifactPrefixes = options.artifactPrefixes ?? DEFAULT_ARTIFACT_PREFIXES;
        this.excludePrefixes = options.excludePrefixes ?? exports.DEFAULT_EXCLUDE_PREFIXES;
        this.maxFileBytes = options.maxFileBytes ?? DEFAULT_MAX_FILE_BYTES;
        // Same path listed twice would be measured twice, so keep one entry per path.
        // A code repo *nested* inside the spec repo needs no special handling: git does
        // not descend into a nested repository, so the outer `git status` never reports
        // the inner repo's files. (Verified — the inner tree shows up as one directory
        // entry, which contributes no lines.)
        const seen = new Set([(0, path_1.resolve)(projectPath)]);
        this.roots = [{ path: projectPath, role: 'spec' }];
        for (const root of options.codeRoots ?? []) {
            if (!root || seen.has((0, path_1.resolve)(root)))
                continue;
            seen.add((0, path_1.resolve)(root));
            this.roots.push({ path: root, role: 'code' });
        }
    }
    /** Capture every root's state right before a node starts. */
    snapshot(nodeId) {
        const perRoot = new Map();
        for (const { path } of this.roots) {
            const snap = this.takeSnapshot(path);
            if (snap)
                perRoot.set(path, snap);
        }
        if (perRoot.size > 0)
            this.snapshots.set(nodeId, perRoot);
    }
    /** Diff every root's current state against the node's start snapshot. */
    delta(nodeId) {
        const beforeByRoot = this.snapshots.get(nodeId);
        this.snapshots.delete(nodeId);
        if (!beforeByRoot)
            return null;
        const byRole = { spec: { ...EMPTY_ROLE }, code: { ...EMPTY_ROLE } };
        const artifactPaths = [];
        const otherPaths = [];
        let measuredAny = false;
        for (const { path: rootPath, role } of this.roots) {
            const before = beforeByRoot.get(rootPath);
            if (!before)
                continue;
            const after = this.takeSnapshot(rootPath);
            // A repo we snapshotted at node start but cannot read now would leave a
            // partial sum that still looks like a complete one. Reporting no number is
            // recoverable; reporting a number that is quietly too small is not.
            if (!after)
                return null;
            measuredAny = true;
            const one = this.deltaForRoot(rootPath, role, before, after, artifactPaths, otherPaths);
            const acc = byRole[role];
            acc.filesCreated += one.filesCreated;
            acc.filesModified += one.filesModified;
            acc.locAdded += one.locAdded;
            acc.locRemoved += one.locRemoved;
            acc.artifactsCreated += one.artifactsCreated;
        }
        if (!measuredAny)
            return null;
        return {
            filesCreated: byRole.spec.filesCreated + byRole.code.filesCreated,
            filesModified: byRole.spec.filesModified + byRole.code.filesModified,
            locAdded: byRole.spec.locAdded + byRole.code.locAdded,
            locRemoved: byRole.spec.locRemoved + byRole.code.locRemoved,
            artifactsCreated: byRole.spec.artifactsCreated + byRole.code.artifactsCreated,
            createdPaths: [...artifactPaths, ...otherPaths].slice(0, 20),
            byRole,
        };
    }
    /**
     * Deltas for one root. Created paths are appended to the shared drill-down lists so
     * artifacts still sort first across all roots.
     */
    deltaForRoot(rootPath, role, before, after, artifactPaths, otherPaths) {
        const created = [];
        let locAdded = 0;
        let locRemoved = 0;
        let filesModified = 0;
        // Untracked files now reach numstat too (see `numstat`), so counting their lines here
        // as well would count them twice. This loop only decides which paths are new.
        const createdNow = new Set();
        for (const path of after.untracked) {
            if (before.seen.has(path) || this.isExcluded(path))
                continue;
            createdNow.add(path);
        }
        // numstat is cumulative against the diff base, so the node's own delta is the
        // difference between the two snapshots.
        for (const [path, [addAfter, delAfter]] of after.numstat) {
            if (this.isExcluded(path))
                continue;
            const [addBefore, delBefore] = before.numstat.get(path) ?? [0, 0];
            const addDiff = addAfter - addBefore;
            const delDiff = delAfter - delBefore;
            if (addDiff === 0 && delDiff === 0)
                continue;
            locAdded += Math.max(0, addDiff);
            // A file that is not committed yet counts as pure additions against the base, so
            // shrinking it lowers that number instead of raising the removals. Read the drop as
            // what it is: lines this node took out. Left clamped at zero, a rewrite that cut a
            // document in half reported no change at all.
            locRemoved += Math.max(0, delDiff) + Math.max(0, -addDiff);
            // Created means the path was not there before: untracked-and-new, or newly staged as
            // an addition. A clean tracked file is absent from porcelain, so "not seen before"
            // on its own must not imply created.
            const isNewlyAdded = (after.statusByPath.get(path) ?? '').includes('A') && !before.seen.has(path);
            if (createdNow.has(path) || isNewlyAdded) {
                created.push(path);
            }
            else {
                filesModified += 1;
            }
        }
        // A new file numstat could not measure (binary, or over the size guard) is still
        // something this node produced.
        for (const path of createdNow) {
            if (!after.numstat.has(path))
                created.push(path);
        }
        // Artifact prefixes are spec-repo conventions; code repos hold source, not artifacts.
        const isArtifact = (p) => role === 'spec' && this.artifactPrefixes.some((prefix) => p.startsWith(prefix));
        // Same relative path can exist in both repos, so label which repo a path came from.
        const prefix = role === 'code' ? `${(0, path_1.basename)(rootPath)}/` : '';
        let artifactsCreated = 0;
        for (const path of created) {
            if (isArtifact(path)) {
                artifactsCreated += 1;
                artifactPaths.push(prefix + path);
            }
            else {
                otherPaths.push(prefix + path);
            }
        }
        return { filesCreated: created.length, filesModified, locAdded, locRemoved, artifactsCreated };
    }
    takeSnapshot(rootPath) {
        if (this.gitAvailable.get(rootPath) === false)
            return null;
        try {
            const porcelain = this.git(['status', '--porcelain', '-uall'], rootPath);
            const numstatRaw = this.numstat(rootPath);
            this.gitAvailable.set(rootPath, true);
            const untracked = new Set();
            const statusByPath = new Map();
            const seen = new Set();
            for (const line of porcelain.split('\n')) {
                if (!line.trim())
                    continue;
                const status = line.slice(0, 2);
                const path = normalizeGitPath(line.slice(3));
                seen.add(path);
                statusByPath.set(path, status);
                if (status === '??')
                    untracked.add(path);
            }
            const numstat = new Map();
            for (const line of numstatRaw.split('\n')) {
                if (!line.trim())
                    continue;
                const [add, del, ...rest] = line.split('\t');
                const path = normalizeGitPath(rest.join('\t'));
                if (add === '-' || del === '-')
                    continue; // binary
                numstat.set(path, [Number(add) || 0, Number(del) || 0]);
                seen.add(path);
            }
            return { numstat, untracked, statusByPath, seen };
        }
        catch {
            if (!this.gitAvailable.has(rootPath))
                this.gitAvailable.set(rootPath, false);
            return null;
        }
    }
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
    numstat(rootPath) {
        const base = this.diffBase(rootPath);
        let indexFile;
        try {
            const real = this.git(['rev-parse', '--path-format=absolute', '--git-path', 'index'], rootPath).trim();
            indexFile = (0, path_1.join)((0, os_1.tmpdir)(), `vsaf-index-${process.pid}-${this.indexSeq++}`);
            // A repo that has never staged anything has no index file yet. Copying is how staged
            // state is preserved; with nothing staged there is nothing to preserve, and git
            // creates the temp index itself. Insisting on the copy threw away the measurement for
            // exactly the freshest projects.
            if ((0, fs_1.existsSync)(real))
                (0, fs_1.copyFileSync)(real, indexFile);
            const env = { ...process.env, GIT_INDEX_FILE: indexFile };
            (0, child_process_1.execFileSync)('git', ['add', '-A', '-N'], { cwd: rootPath, env, stdio: 'ignore', windowsHide: true });
            return (0, child_process_1.execFileSync)('git', ['diff', '--numstat', base], {
                cwd: rootPath, env, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024, windowsHide: true,
            });
        }
        catch {
            return this.git(['diff', '--numstat', base], rootPath);
        }
        finally {
            if (indexFile) {
                try {
                    (0, fs_1.rmSync)(indexFile, { force: true });
                }
                catch { /* a leftover temp index harms nothing */ }
            }
        }
    }
    /**
     * What `git diff` measures against. `HEAD` normally, the empty tree in a repo with no
     * commit yet — there, `HEAD` is not a revision and git exits non-zero, which used to
     * disable measurement for the whole repo. Silently: telemetry never breaks a run, so
     * every span in a freshly initialised project arrived with no output numbers at all,
     * and nothing said why. A project sits in exactly that state between `git init` and
     * its first commit, which is where a new NTAPP project starts.
     */
    diffBase(rootPath) {
        const cached = this.diffBases.get(rootPath);
        if (cached)
            return cached;
        let base = EMPTY_TREE;
        try {
            // stderr silenced: "fatal: Needed a single revision" is the answer here, not a
            // problem, and printing it during a run reads like something went wrong.
            this.git(['rev-parse', '--verify', 'HEAD'], rootPath, { quiet: true });
            base = 'HEAD';
        }
        catch {
            // No commit yet — every tracked path is an addition against the empty tree.
        }
        this.diffBases.set(rootPath, base);
        return base;
    }
    isExcluded(path) {
        return this.excludePrefixes.some((prefix) => path.startsWith(prefix));
    }
    git(args, rootPath, options = {}) {
        return (0, child_process_1.execFileSync)('git', args, {
            cwd: rootPath,
            encoding: 'utf-8',
            maxBuffer: 10 * 1024 * 1024,
            windowsHide: true,
            stdio: options.quiet ? ['ignore', 'pipe', 'ignore'] : undefined,
        });
    }
    countLines(rootPath, relPath) {
        try {
            const full = (0, path_1.join)(rootPath, relPath);
            const stat = (0, fs_1.statSync)(full);
            if (!stat.isFile() || stat.size > this.maxFileBytes)
                return 0;
            const content = (0, fs_1.readFileSync)(full);
            if (content.includes(0))
                return 0; // binary
            let lines = 0;
            for (const byte of content)
                if (byte === 10)
                    lines += 1;
            if (content.length > 0 && content[content.length - 1] !== 10)
                lines += 1;
            return lines;
        }
        catch {
            return 0;
        }
    }
}
exports.OutputMetricsCollector = OutputMetricsCollector;
function normalizeGitPath(raw) {
    let path = raw.trim();
    // git quotes paths containing special chars
    if (path.startsWith('"') && path.endsWith('"'))
        path = path.slice(1, -1);
    // rename syntax "old -> new"
    const arrow = path.indexOf(' -> ');
    if (arrow !== -1)
        path = path.slice(arrow + 4);
    return path;
}
//# sourceMappingURL=output-metrics.js.map