"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CONFIG_FILE = void 0;
exports.detectRepoStack = detectRepoStack;
exports.deployReposConfig = deployReposConfig;
exports.linkCanonicalSkills = linkCanonicalSkills;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
/** The config file the pack's skills read. Its name is fixed by those skills. */
exports.CONFIG_FILE = '.bmm-config.yaml';
/** Where a pack keeps the template rendered into each code repo. */
const TEMPLATE = (0, path_1.join)('config', 'bmm-config.template.yaml');
/** Canonical skills live in the spec repo; code repos reach them through a link. */
const SKILLS_LINK = (0, path_1.join)('.agent', 'skills');
const UNKNOWN = '<TODO>';
function jsDeps(repoPath) {
    const path = (0, path_1.join)(repoPath, 'package.json');
    if (!(0, fs_1.existsSync)(path))
        return null;
    try {
        return (0, fs_1.readFileSync)(path, 'utf-8');
    }
    catch {
        return null;
    }
}
function jsStack(deps) {
    if (deps.includes('"@angular/core"')) {
        return { language: 'typescript', framework: 'angular', ui_library: 'angular-material', build_tool: 'npm' };
    }
    if (deps.includes('"react"')) {
        return { language: 'typescript', framework: 'react', ui_library: '<react-component-lib>', build_tool: 'npm' };
    }
    if (deps.includes('"vue"')) {
        return { language: 'typescript', framework: 'vue', ui_library: '<vue-component-lib>', build_tool: 'npm' };
    }
    return { language: 'typescript', framework: 'node', ui_library: UNKNOWN, build_tool: 'npm' };
}
/** Manifest → stack, in the order a repo's own build file settles the question. */
const NON_JS = [
    {
        files: ['pom.xml'],
        stack: { language: 'java', framework: 'java', ui_library: 'n/a', build_tool: 'maven' },
    },
    {
        files: ['build.gradle', 'build.gradle.kts'],
        stack: { language: 'java', framework: UNKNOWN, ui_library: 'n/a', build_tool: 'gradle' },
    },
    {
        files: ['go.mod'],
        stack: { language: 'go', framework: UNKNOWN, ui_library: 'n/a', build_tool: 'go' },
    },
    {
        files: ['Cargo.toml'],
        stack: { language: 'rust', framework: UNKNOWN, ui_library: 'n/a', build_tool: 'cargo' },
    },
    {
        files: ['pyproject.toml', 'requirements.txt'],
        stack: { language: 'python', framework: UNKNOWN, ui_library: 'n/a', build_tool: 'pip' },
    },
];
/**
 * Work out a repo's stack from its build manifests.
 *
 * An unrecognised repo reports `<TODO>` rather than a guess, so the gap shows up
 * in the generated config instead of quietly steering skills the wrong way.
 */
function detectRepoStack(repoPath) {
    const deps = jsDeps(repoPath);
    if (deps !== null)
        return jsStack(deps);
    for (const { files, stack } of NON_JS) {
        if (!files.some(file => (0, fs_1.existsSync)((0, path_1.join)(repoPath, file))))
            continue;
        if (files[0] === 'pom.xml' && (0, fs_1.readFileSync)((0, path_1.join)(repoPath, 'pom.xml'), 'utf-8').includes('spring-boot')) {
            return { ...stack, framework: 'spring-boot' };
        }
        return stack;
    }
    return { language: UNKNOWN, framework: UNKNOWN, ui_library: UNKNOWN, build_tool: UNKNOWN };
}
/** Relative so a clone on another machine, or a renamed workspace, still resolves. */
function relativeTo(from, to) {
    return (0, path_1.relative)(from, to) || '.';
}
function render(template, repoPath, layout) {
    const stack = detectRepoStack(repoPath);
    const specRelative = relativeTo(repoPath, layout.specRepo);
    const dsSuffix = layout.designSystemRoots?.get(repoPath);
    const designSystem = (0, path_1.join)(specRelative, 'NTAPP-output', 'design-system', dsSuffix ?? '');
    const values = {
        PROJECT_NAME: layout.projectName ?? (0, path_1.basename)(layout.specRepo),
        CODE_REPO_NAME: (0, path_1.basename)(repoPath),
        SPEC_REPO_RELATIVE: specRelative,
        META_REPO_RELATIVE: layout.metaRepo ? relativeTo(repoPath, layout.metaRepo) : 'n/a',
        DS_ROOT: designSystem,
        LANG: stack.language,
        FRAMEWORK: stack.framework,
        UI_LIB: stack.ui_library,
        BUILD_TOOL: stack.build_tool,
        // Deliberately not a real clock reading: a timestamp would make every reinstall
        // rewrite the file and defeat the idempotency the installer promises.
        TIMESTAMP: 'managed by vsaf install',
    };
    let result = template;
    for (const [name, value] of Object.entries(values)) {
        result = result.replaceAll(`{{${name}}}`, value);
    }
    return result;
}
/**
 * Render the pack's config template into every code repo, filling in that repo's
 * own stack and its relative path back to the spec repo.
 *
 * Returns the config files written.
 */
function deployReposConfig(packDir, layout) {
    const templatePath = (0, path_1.join)(packDir, TEMPLATE);
    if (!(0, fs_1.existsSync)(templatePath))
        return [];
    const template = (0, fs_1.readFileSync)(templatePath, 'utf-8');
    const written = [];
    for (const repoPath of layout.codeRepos) {
        const target = (0, path_1.join)(repoPath, exports.CONFIG_FILE);
        const content = render(template, repoPath, layout);
        (0, backup_js_1.backupIfModified)(target, content);
        (0, fs_1.writeFileSync)(target, content, 'utf-8');
        written.push(target);
    }
    return written;
}
/**
 * Point each code repo at the spec repo's canonical skills through a relative
 * symlink, so one edit is seen by every repo in the workspace.
 *
 * A real directory already sitting at the link path is left alone — it may hold
 * the user's own files, and replacing it would destroy them.
 */
function linkCanonicalSkills(specRepo, codeRepos) {
    const source = (0, path_1.join)(specRepo, SKILLS_LINK);
    if (!(0, fs_1.existsSync)(source))
        return [];
    const written = [];
    for (const repoPath of codeRepos) {
        if (repoPath === specRepo)
            continue;
        const link = (0, path_1.join)(repoPath, SKILLS_LINK);
        if ((0, fs_1.existsSync)(link) || (0, fs_1.lstatSync)(link, { throwIfNoEntry: false })) {
            if (!(0, fs_1.lstatSync)(link).isSymbolicLink())
                continue;
            (0, fs_1.rmSync)(link, { force: true });
        }
        (0, fs_1.mkdirSync)((0, path_1.dirname)(link), { recursive: true });
        (0, fs_1.symlinkSync)(relativeTo((0, path_1.dirname)(link), source), link, 'dir');
        written.push(link);
    }
    return written;
}
//# sourceMappingURL=repos-config.js.map