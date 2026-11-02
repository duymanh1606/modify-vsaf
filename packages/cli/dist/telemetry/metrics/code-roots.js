"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveCodeRoots = resolveCodeRoots;
// packages/cli/src/telemetry/metrics/code-roots.ts
const fs_1 = require("fs");
const path_1 = require("path");
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
function resolveCodeRoots(projectPath, configured) {
    const candidates = configured?.length ? configured : readWorkspaceFolders(projectPath);
    const roots = [];
    const seen = new Set([(0, path_1.resolve)(projectPath)]);
    for (const candidate of candidates) {
        const full = (0, path_1.isAbsolute)(candidate) ? (0, path_1.resolve)(candidate) : (0, path_1.resolve)(projectPath, candidate);
        if (seen.has(full))
            continue;
        seen.add(full);
        if (!isGitRepo(full))
            continue;
        roots.push(full);
    }
    return roots;
}
/** `folders[].path` from the spec repo's `<project>.code-workspace`, if there is one. */
function readWorkspaceFolders(projectPath) {
    try {
        const files = (0, fs_1.readdirSync)(projectPath)
            .filter((name) => name.endsWith('.code-workspace'))
            .sort();
        for (const name of files) {
            const parsed = parseWorkspace((0, path_1.join)(projectPath, name));
            if (parsed.length > 0)
                return parsed;
        }
    }
    catch {
        /* no readable project dir — no extra roots */
    }
    return [];
}
function parseWorkspace(path) {
    try {
        const raw = (0, fs_1.readFileSync)(path, 'utf-8');
        const parsed = JSON.parse(stripLineComments(raw));
        if (!Array.isArray(parsed.folders))
            return [];
        return parsed.folders
            .map((folder) => folder?.path)
            .filter((p) => typeof p === 'string' && p.trim().length > 0);
    }
    catch {
        return [];
    }
}
/**
 * Editors accept comments in workspace files, `JSON.parse` does not. Only whole
 * comment lines are dropped, so a `//` inside a string value stays intact.
 */
function stripLineComments(raw) {
    return raw
        .split('\n')
        .filter((line) => !line.trimStart().startsWith('//'))
        .join('\n');
}
function isGitRepo(path) {
    try {
        // `.git` is a directory in a normal clone and a file in a linked worktree.
        return (0, fs_1.statSync)(path).isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(path, '.git'));
    }
    catch {
        return false;
    }
}
//# sourceMappingURL=code-roots.js.map