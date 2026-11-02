"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SPEC_REPO_MARKER = void 0;
exports.workspaceFileIn = workspaceFileIn;
exports.reposInWorkspaceFile = reposInWorkspaceFile;
exports.candidateName = candidateName;
exports.parseRepoChoice = parseRepoChoice;
exports.validateRepoNames = validateRepoNames;
exports.isCodeRepo = isCodeRepo;
exports.resolveWorkspace = resolveWorkspace;
const fs_1 = require("fs");
const path_1 = require("path");
/**
 * What marks the spec repo: the directory holding the NTAPP artifact tree. The
 * older bootstrap script used the same signal.
 */
exports.SPEC_REPO_MARKER = 'NTAPP-output';
/**
 * The repos this project already claims, read from its own workspace file.
 *
 * `<name>.code-workspace` sits at the spec repo root, is committed, and lists the spec
 * repo plus every code repo the wiring found — so it is the project's own answer to
 * "which repos are mine", identical for everyone on the team.
 *
 * Reading it means `--upgrade` does not have to ask a question it can already answer.
 * Before this, someone who cloned one more repo was asked to re-pick the other five, or
 * to spell them out on the command line — and a list retyped by hand is a list that
 * eventually loses an entry.
 *
 * Anything unreadable returns nothing: a hand-edited workspace file with a trailing comma
 * is not a reason to stop an install, and asking is a working fallback.
 */
/**
 * The workspace file's own name, read off disk rather than guessed.
 *
 * `<name>.code-workspace` is named after the project, and that name is not always the
 * folder someone typed: `--new` asks for it separately, `--clone` infers it from the
 * folder, and a hand-run bootstrap can rename it with `--project-name`. Only the file
 * itself is the answer — printing a path built from a name the code assumed is exactly
 * how a "here's what to open next" message ends up pointing at a file that is not there.
 *
 * `undefined` when there is none yet, or more than one and picking is a guess.
 */
function workspaceFileIn(specRepo) {
    let files;
    try {
        files = (0, fs_1.readdirSync)(specRepo).filter(name => name.endsWith('.code-workspace')).sort();
    }
    catch {
        return undefined;
    }
    return files.length === 1 ? files[0] : undefined;
}
function reposInWorkspaceFile(specRepo) {
    let files;
    try {
        files = (0, fs_1.readdirSync)(specRepo).filter(name => name.endsWith('.code-workspace')).sort();
    }
    catch {
        return [];
    }
    const found = [];
    for (const file of files) {
        let folders;
        try {
            folders = JSON.parse((0, fs_1.readFileSync)((0, path_1.join)(specRepo, file), 'utf-8')).folders;
        }
        catch {
            continue;
        }
        if (!Array.isArray(folders))
            continue;
        for (const folder of folders) {
            const at = folder?.path;
            if (typeof at !== 'string' || !at)
                continue;
            const path = (0, path_1.resolve)(specRepo, at);
            // The spec repo lists itself; it is not one of its own code repos. And a folder
            // named in the file but no longer on disk is not something to wire.
            if (path === specRepo || !(0, fs_1.existsSync)(path))
                continue;
            if (!found.includes(path))
                found.push(path);
        }
    }
    return found;
}
/** Build manifests that make a sibling directory a code repo. */
const MANIFESTS = [
    'package.json', 'pom.xml', 'build.gradle', 'build.gradle.kts',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'requirements.txt',
];
/**
 * Directories never looked into while scanning one level down.
 *
 * The same list `scan_skip_dir` uses in the pack's `bootstrap.sh`. `Pods`, `Carthage` and
 * `.build` hold the Xcode projects of *other people's* libraries, so a repo would look
 * like an Apple repo because of a dependency it merely vendored.
 */
const SKIP_DIRS = new Set([
    'node_modules', 'target', 'build', 'dist', 'out', 'vendor', '.git', '.idea', '.vscode',
    '.gradle', 'Pods', 'Carthage', 'DerivedData', '.build', '.swiftpm',
]);
/**
 * Files that mark an Apple repo, which carries none of the manifests above.
 *
 * Kept in step with `detect_apple_marker` in the pack's own `bootstrap.sh`: that script
 * decides which repos get wired, and a repo this installer refuses to name is a repo the
 * script never sees. When the two lists disagree, the disagreement is invisible — an iOS
 * repo either gets rejected here with "is not a code repo", or gets accepted here and
 * silently skipped there.
 */
const APPLE_FILES = ['Package.swift', 'Podfile'];
/** Bundle suffixes that mark an Apple repo. They are directories, not files. */
const APPLE_BUNDLES = ['.xcworkspace', '.xcodeproj'];
/** True when this exact directory holds an Apple project. */
function hasAppleMarker(path) {
    if (APPLE_FILES.some(file => (0, fs_1.existsSync)((0, path_1.join)(path, file))))
        return true;
    try {
        return (0, fs_1.readdirSync)(path, { withFileTypes: true }).some(entry => entry.isDirectory() && APPLE_BUNDLES.some(suffix => entry.name.endsWith(suffix)));
    }
    catch {
        return false;
    }
}
/** True when this exact directory carries a build manifest or an Apple project. */
function marksAProject(path) {
    return MANIFESTS.some(manifest => (0, fs_1.existsSync)((0, path_1.join)(path, manifest))) || hasAppleMarker(path);
}
/**
 * The same one-level-down look the pack's script takes — with its one exception.
 *
 * Monorepos put the manifest one directory in, and the script finds those, so this has to
 * as well: a repo the script accepts and this one refuses cannot be installed at all,
 * which is how an iOS repo came back as "is not a code repo" while the script would have
 * wired it happily.
 *
 * The exception is `pubspec.yaml`. A Flutter repo keeps real Xcode and Gradle projects in
 * `ios/` and `android/`, and the script deliberately stops at the root when it sees a
 * pubspec — so a Flutter repo with no marker of its own is not a code repo to it. Diving
 * anyway would make this installer accept a repo the script then skips in silence.
 */
function marksAProjectNearby(path) {
    if ((0, fs_1.existsSync)((0, path_1.join)(path, 'pubspec.yaml')))
        return false;
    try {
        return (0, fs_1.readdirSync)(path, { withFileTypes: true }).some(entry => entry.isDirectory() && !SKIP_DIRS.has(entry.name) && marksAProject((0, path_1.join)(path, entry.name)));
    }
    catch {
        return false;
    }
}
/**
 * How a candidate must be spelled on the command line.
 *
 * Always relative to the spec repo, because that is what resolution reads. Naming
 * them relative to anything else does not round-trip: a name that fails to resolve
 * falls back to a match by last path segment, which can silently pick a different
 * repo that happens to share the name.
 */
function candidateName(specRepo, candidate) {
    return (0, path_1.relative)(specRepo, candidate);
}
/**
 * Read what the user picked from the numbered list of candidates.
 *
 * Returns names spelled the way `--code-repos` accepts, or undefined for "nothing"
 * — an empty answer, or one that names nothing valid. Undefined means nothing is
 * wired, which is the safe reading of an answer that could not be understood.
 *
 * `a` takes every candidate; anything out of range is dropped rather than guessed at.
 */
function parseRepoChoice(answer, candidates, specRepo) {
    const trimmed = answer.trim().toLowerCase();
    if (trimmed === '')
        return undefined;
    const name = (path) => candidateName(specRepo, path);
    if (trimmed === 'a')
        return candidates.map(name);
    const picked = trimmed
        .split(',')
        .map(part => Number.parseInt(part.trim(), 10))
        .filter(n => Number.isInteger(n) && n >= 1 && n <= candidates.length)
        .map(n => name(candidates[n - 1]));
    return picked.length > 0 ? [...new Set(picked)] : undefined;
}
/** Code repos directly under a directory, skipping one path (the spec repo itself). */
function codeReposIn(dir, skip) {
    let entries;
    try {
        entries = (0, fs_1.readdirSync)(dir);
    }
    catch {
        return [];
    }
    return entries
        .map(name => (0, path_1.join)(dir, name))
        .filter(path => path !== skip && isCodeRepo(path))
        .sort();
}
/**
 * Whether every name would resolve to a code repo, without writing anything.
 *
 * The same reading `resolveWorkspace` does, split out so it can be run before the
 * install starts. It used to happen at the end of the wiring step, which is after the
 * skills, the hooks, the rules, the artifact tree and a git repo had all been written
 * — so a typo in `--code-repos` left a half-installed directory behind and no record
 * of it.
 *
 * Pure: it reads directories and nothing else. The marker for the spec repo is not
 * consulted, because the install is what creates it.
 */
function validateRepoNames(projectPath, names) {
    const candidates = [...codeReposIn(projectPath), ...codeReposIn((0, path_1.dirname)(projectPath), projectPath)];
    const unknown = names.filter(name => {
        const asPath = (0, path_1.resolve)(projectPath, name);
        if (asPath === projectPath)
            return true;
        if (isCodeRepo(asPath))
            return false;
        return !candidates.some(path => (0, path_1.basename)(path) === name);
    });
    if (unknown.length === 0)
        return { ok: true };
    return { ok: false, unknown, candidates: candidates.map(path => candidateName(projectPath, path)) };
}
function isCodeRepo(path) {
    try {
        if (!(0, fs_1.statSync)(path).isDirectory())
            return false;
    }
    catch {
        return false;
    }
    return marksAProject(path) || marksAProjectNearby(path);
}
/**
 * Work out the multi-repo layout around a spec repo.
 *
 * Nothing is selected unless the caller names it. Configuring every sibling that
 * merely looks like a repo is how the older script reached into unrelated projects
 * sharing the same parent directory, and that is not recoverable by guessing.
 *
 * A name that matches no sibling repo throws rather than quietly configuring
 * nothing — a typo would otherwise look like success.
 */
function resolveWorkspace(projectPath, names, options = {}) {
    // `assumeSpecRepo` is for describing an install before it runs: the install creates
    // the marker itself, so a plan that waited for the marker would report no code repos
    // for exactly the case that needs them most — a project being set up for the first
    // time.
    const isSpecRepo = options.assumeSpecRepo || (0, fs_1.existsSync)((0, path_1.join)(projectPath, exports.SPEC_REPO_MARKER));
    if (!isSpecRepo) {
        return { specRepo: projectPath, isSpecRepo: false, candidates: [], codeRepos: [] };
    }
    // Two layouts exist in practice: code repos beside the spec repo, and code repos
    // nested inside a workspace whose root holds the artifact tree. Both are offered.
    const candidates = [...codeReposIn(projectPath), ...codeReposIn((0, path_1.dirname)(projectPath), projectPath)];
    const codeRepos = (names ?? []).map(name => {
        // A plain name is read as a path inside the project first, so a nested repo wins
        // over a same-named directory beside the project. Reach outside with `../name`.
        const asPath = (0, path_1.resolve)(projectPath, name);
        if (asPath === projectPath) {
            throw new Error(`"${name}" is the spec repo — it cannot also be one of its code repos`);
        }
        if (isCodeRepo(asPath))
            return asPath;
        const sibling = candidates.find(path => (0, path_1.basename)(path) === name);
        if (!sibling) {
            throw new Error(`"${name}" is not a code repo in or beside ${(0, path_1.basename)(projectPath)}. `
                + `Found: ${candidates.map(p => candidateName(projectPath, p)).join(', ') || 'none'}`);
        }
        return sibling;
    });
    return { specRepo: projectPath, isSpecRepo, candidates, codeRepos };
}
//# sourceMappingURL=workspace.js.map