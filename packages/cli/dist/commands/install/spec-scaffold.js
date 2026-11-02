"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ARTIFACT_DIRS = exports.ARTIFACT_ROOT = void 0;
exports.scaffoldArtifactTree = scaffoldArtifactTree;
exports.reserveProjectSkills = reserveProjectSkills;
exports.deployModuleConfig = deployModuleConfig;
exports.deployDesignSystemShared = deployDesignSystemShared;
exports.deployProjectContext = deployProjectContext;
exports.deployProjectReadme = deployProjectReadme;
exports.deployRepoAssets = deployRepoAssets;
exports.writeSpecRepoConfig = writeSpecRepoConfig;
const fs_1 = require("fs");
const path_1 = require("path");
/** Where the flow writes its artifacts, and the config file that points at it. */
exports.ARTIFACT_ROOT = 'NTAPP-output';
const CONFIG_FILE = '.bmm-config.yaml';
const MODULE_DIR = '_bmad';
/** Where a design system keeps the schemas and procedures shared by every design system. */
const SHARED_DIR = '_shared';
/**
 * The directories the flow's stages write into.
 *
 * Created up front because a skill that cannot find its output directory fails in
 * the middle of a run, after the expensive part.
 */
exports.ARTIFACT_DIRS = [
    'Stage_1_Discovery',
    'Stage_2_Architecture',
    'Stage_3_Specs',
    'Stage_4_Design',
    'Stage_5_Build_Verify',
    'design-system',
    'evaluation',
    '_notifications',
];
/** Create the artifact tree. Existing artifacts are the user's work and stay. */
function scaffoldArtifactTree(specRepo) {
    return exports.ARTIFACT_DIRS.map(sub => {
        const path = (0, path_1.join)(specRepo, exports.ARTIFACT_ROOT, sub);
        (0, fs_1.mkdirSync)(path, { recursive: true });
        return path;
    });
}
/**
 * Reserve the place for skills written for this one project.
 *
 * Left empty on purpose, with a keep-file so git tracks the directory. The pack's
 * own skills do not go here — they are reinstallable and live where git ignores
 * them. This directory is the one a code repo is linked at, so a skill added here
 * is seen by every repo in the workspace.
 *
 * Returns the keep-file, or null when the directory already holds something.
 */
function reserveProjectSkills(specRepo) {
    const dir = (0, path_1.join)(specRepo, '.agent', 'skills');
    (0, fs_1.mkdirSync)(dir, { recursive: true });
    if ((0, fs_1.readdirSync)(dir).length > 0)
        return null;
    const keep = (0, path_1.join)(dir, '.gitkeep');
    (0, fs_1.writeFileSync)(keep, '', 'utf-8');
    return keep;
}
/**
 * Copy the module configuration the pack's skills read at runtime.
 *
 * An existing copy is left alone: it holds per-project edits, and a reinstall
 * overwriting them would undo work silently.
 *
 * Returns the directory written, or null when there was nothing to write.
 */
function deployModuleConfig(packDir, specRepo) {
    const source = (0, path_1.join)(packDir, MODULE_DIR);
    if (!(0, fs_1.existsSync)(source))
        return null;
    const target = (0, path_1.join)(specRepo, MODULE_DIR);
    if ((0, fs_1.existsSync)(target))
        return null;
    (0, fs_1.cpSync)(source, target, { recursive: true });
    return target;
}
/**
 * Install the shared reference files the design-system skills read at runtime.
 *
 * They do not live beside the skills: every skill resolves them through the artifact
 * tree, as `{design_system_root}/_shared/<name>.md`, so that one project's schemas
 * and procedures are the ones its skills follow. Scaffolding created
 * `design-system` and left it empty, which pointed 153 references across the pack at
 * files no install ever wrote — the bootstrap skill went looking for its own schema
 * and found nothing there.
 *
 * Copied file by file rather than as a directory, for two reasons. A project set up
 * before this shipped already has the directory and none of the files, and must be
 * repaired by reinstalling. And a file already there is the project's copy, which
 * may have been tuned — it stays.
 *
 * Returns the files written, one path each, never the directory holding them. The
 * difference is what an uninstall takes back: the record it reads is a list of paths
 * it deletes, and naming the directory there meant deleting everything inside it —
 * including a file the project put there itself, which the installer never wrote and
 * has no business removing.
 */
function deployDesignSystemShared(packDir, specRepo) {
    const source = (0, path_1.join)(packDir, 'templates', 'design-system', SHARED_DIR);
    if (!(0, fs_1.existsSync)(source))
        return [];
    const target = (0, path_1.join)(specRepo, exports.ARTIFACT_ROOT, 'design-system', SHARED_DIR);
    const missing = (0, fs_1.readdirSync)(source)
        .filter(name => name.endsWith('.md') || name.endsWith('.yaml'))
        .filter(name => !(0, fs_1.existsSync)((0, path_1.join)(target, name)));
    if (missing.length === 0)
        return [];
    (0, fs_1.mkdirSync)(target, { recursive: true });
    return missing.map(name => {
        const path = (0, path_1.join)(target, name);
        (0, fs_1.copyFileSync)((0, path_1.join)(source, name), path);
        return path;
    });
}
/**
 * Put the pack's project-context document in place, but only when the project has
 * none. `CLAUDE.md` is the file the agent reads first and the one a team is most
 * likely to have written themselves; overwriting it would replace their words.
 *
 * The copy ships with the project-name placeholder, which the naming step fills in.
 *
 * Returns the file written, or null when one was already there.
 */
function deployProjectContext(packDir, specRepo, projectName) {
    // The name is filled in as the file is written, so a fresh install does not
    // immediately back up a file it created one line earlier.
    return copyTemplate(packDir, specRepo, 'CLAUDE.md', projectName);
}
/**
 * Put the pack's README in place — the page that tells whoever opens this repo next
 * how the flow runs. Same rule: only when the project has none.
 */
function deployProjectReadme(packDir, specRepo) {
    return copyTemplate(packDir, specRepo, 'README.md');
}
/**
 * Directories the pack ships that belong at the repo root, where the flow's own
 * documents point at them. Copied whole, never overwritten: a team edits the manual
 * and adds tools of its own.
 */
const REPO_ASSETS = ['scripts', (0, path_1.join)('docs', 'Process')];
function deployRepoAssets(packDir, specRepo) {
    const written = [];
    for (const asset of REPO_ASSETS) {
        const source = (0, path_1.join)(packDir, asset);
        if (!(0, fs_1.existsSync)(source))
            continue;
        const target = (0, path_1.join)(specRepo, asset);
        if ((0, fs_1.existsSync)(target))
            continue;
        (0, fs_1.mkdirSync)((0, path_1.dirname)(target), { recursive: true });
        (0, fs_1.cpSync)(source, target, { recursive: true });
        written.push(target);
    }
    // The rule documents themselves, kept at the root as the copy a team reads. Which
    // one applies to which repo is decided per code repo, from its stack — this is the
    // source, not the decision. The pack's own mapping file stays out of the project.
    const rulesSource = (0, path_1.join)(packDir, 'rules');
    const rulesTarget = (0, path_1.join)(specRepo, 'rules');
    if ((0, fs_1.existsSync)(rulesSource) && !(0, fs_1.existsSync)(rulesTarget)) {
        (0, fs_1.mkdirSync)(rulesTarget, { recursive: true });
        for (const file of (0, fs_1.readdirSync)(rulesSource).filter(name => name.endsWith('.md'))) {
            (0, fs_1.copyFileSync)((0, path_1.join)(rulesSource, file), (0, path_1.join)(rulesTarget, file));
        }
        written.push(rulesTarget);
    }
    return written;
}
function copyTemplate(packDir, specRepo, name, projectName) {
    const source = (0, path_1.join)(packDir, 'templates', name);
    if (!(0, fs_1.existsSync)(source))
        return null;
    const target = (0, path_1.join)(specRepo, name);
    if ((0, fs_1.existsSync)(target))
        return null;
    if (projectName) {
        (0, fs_1.writeFileSync)(target, (0, fs_1.readFileSync)(source, 'utf-8').replaceAll('<PROJECT_NAME>', projectName), 'utf-8');
    }
    else {
        (0, fs_1.copyFileSync)(source, target);
    }
    return target;
}
/**
 * Write the spec repo's own `.bmm-config.yaml`.
 *
 * Generated rather than copied on purpose. The file that shipped with the old
 * template was a leftover from running the bootstrap inside the template itself:
 * it announced itself as a code-repo config and pointed `spec_repo_root` at a
 * personal folder on one machine. Every spec repo made by copying the template
 * inherited that, so 28 skills have been reading paths that resolve nowhere.
 *
 * An existing config is left alone — it may have been tuned by hand.
 *
 * Returns the file written, or null when one was already there.
 */
function writeSpecRepoConfig(specRepo, projectName) {
    const path = (0, path_1.join)(specRepo, CONFIG_FILE);
    if ((0, fs_1.existsSync)(path))
        return null;
    const content = [
        `# ${CONFIG_FILE} — spec repo config, generated by vsaf install`,
        '#',
        '# Đây là repo tài liệu, nên mọi đường dẫn trỏ về chính nó. Sửa tay được:',
        '# lần cài lại sẽ giữ nguyên file này.',
        '',
        `project_name: ${projectName}`,
        '',
        'bmad:',
        '  spec_repo_root: .',
        '  code_repo_root: .',
        `  design_system_root: ${exports.ARTIFACT_ROOT}/design-system`,
        '  meta_repo_root: n/a',
        '',
        '# Repo tài liệu không có stack lập trình. Khai ở từng code repo.',
        'stack:',
        '  language: n/a',
        '  framework: n/a',
        '  ui_library: n/a',
        '  build_tool: n/a',
        '',
        '# Nơi ghi artifact của các skill kiểm thử.',
        'bmad-testarch-framework:',
        `  test_artifacts: "{project-root}/${exports.ARTIFACT_ROOT}/test-artifacts"`,
        '',
        'bmad-testarch-atdd:',
        `  test_artifacts: "{project-root}/${exports.ARTIFACT_ROOT}/test-artifacts"`,
        '  tests_output: "{project-root}/tests"',
        '',
    ].join('\n');
    (0, fs_1.writeFileSync)(path, content, 'utf-8');
    return path;
}
//# sourceMappingURL=spec-scaffold.js.map