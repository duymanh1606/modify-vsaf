"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SHARED_IN_CODE_REPO = void 0;
exports.broughtLine = broughtLine;
exports.rerunCommand = rerunCommand;
exports.deploySharedAssets = deploySharedAssets;
exports.deploySkills = deploySkills;
exports.checkBinaries = checkBinaries;
exports.installGraphify = installGraphify;
exports.execInstall = execInstall;
const fs_1 = require("fs");
const path_1 = require("path");
const child_process_1 = require("child_process");
const os_1 = require("os");
const skill_js_1 = require("./skill.js");
const hooks_js_1 = require("./install/hooks.js");
const rules_js_1 = require("./install/rules.js");
const gitignore_js_1 = require("./install/gitignore.js");
const ide_mirror_js_1 = require("./install/ide-mirror.js");
const skills_lock_js_1 = require("./install/skills-lock.js");
const session_hook_js_1 = require("./install/session-hook.js");
const global_sync_js_1 = require("./install/global-sync.js");
const manifest_js_1 = require("./install/manifest.js");
const flow_source_js_1 = require("./install/flow-source.js");
const engine_range_js_1 = require("./install/engine-range.js");
const engine_version_js_1 = require("./install/engine-version.js");
const flow_script_js_1 = require("./install/flow-script.js");
const install_plan_js_1 = require("./install/install-plan.js");
const selftest_js_1 = require("./install/selftest.js");
const plan_js_1 = require("./install/plan.js");
const repos_config_js_1 = require("./install/repos-config.js");
const workspace_js_1 = require("./install/workspace.js");
const project_name_js_1 = require("./install/project-name.js");
const workspace_file_js_1 = require("./install/workspace-file.js");
const repo_scope_js_1 = require("./install/repo-scope.js");
const delegate_js_1 = require("./install/delegate.js");
const precommit_js_1 = require("./install/precommit.js");
const init_js_1 = require("./init.js");
const ds_registry_js_1 = require("./install/ds-registry.js");
const bootstrap_repo_js_1 = require("./install/bootstrap-repo.js");
const spec_scaffold_js_1 = require("./install/spec-scaffold.js");
/**
 * Câu tổng kết cho bước mang repo về: đã tải mấy cái, đã có sẵn mấy cái.
 *
 * Separate from the install so it can be read at a glance and tested without running one.
 *
 * `fetched` and `kept` are counted apart on purpose. `cloneInto` returns both — a repo
 * already sitting beside the project is kept and reported, which is right — and adding
 * them up told six people repos had come down when five had, the sixth being the spec
 * repo this very run had just created.
 *
 * `beside` is the `--code-repos` case: nothing was brought in because the repos are
 * already on disk, and saying "chưa clone repo nào" right after someone typed the flag
 * reads as the flag being ignored.
 */
function broughtLine(fetched, kept, beside) {
    // Ba tình huống, ba câu — nhưng khi có repo vừa tải thì LUÔN nói cả phần "đã có sẵn",
    // kể cả khi nó bằng 0. Tài liệu §2 dùng đúng dạng `Đã tải 3 repo, 0 đã có sẵn`, và
    // người đọc transcript cần phân biệt được "0 đã có sẵn" với "câu này không nói tới".
    if (fetched > 0)
        return `Đã tải ${fetched} repo, ${kept} đã có sẵn`;
    if (kept > 0)
        return `Dùng ${kept} repo đã có`;
    if (beside > 0)
        return `Dùng ${beside} repo đã có`;
    return 'Chưa clone repo nào';
}
/** Build manifests that mark a directory as holding code rather than documents. */
const CODE_MANIFESTS = [
    'pom.xml', 'build.gradle', 'build.gradle.kts', 'package.json',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'requirements.txt',
];
/**
 * Stop an install that would turn a code repo into a second project root.
 *
 * Installing a pack that ships a project skeleton means "this directory is the
 * project root" — it gets the artifact tree, the module config, a README announcing
 * itself as the documents repo. A code repo is not that; it gets wired from the
 * documents repo instead.
 *
 * Refusing rather than warning, because this already happened quietly: a service
 * repo was installed into three times and ended up with all of the above.
 *
 * Two ways past it: the artifact tree already being there (so it is the project
 * root), or saying so outright.
 */
/**
 * Whether the pack lays out a project around itself — the artifact tree, the module
 * config, the per-repo wiring. `sdlc`, `autotest-skill` and `vds-skill` do not: they
 * deploy skills and stop, and every rule below about repos and project roots is
 * meaningless for them.
 */
function shipsProjectSkeleton(packDir) {
    return (0, fs_1.existsSync)((0, path_1.join)(packDir, 'config', 'bmm-config.template.yaml'));
}
function assertProjectRoot(packDir, projectPath, declared) {
    if (declared)
        return;
    if (!shipsProjectSkeleton(packDir))
        return;
    if ((0, fs_1.existsSync)((0, path_1.join)(projectPath, workspace_js_1.SPEC_REPO_MARKER)))
        return;
    if (!CODE_MANIFESTS.some(manifest => (0, fs_1.existsSync)((0, path_1.join)(projectPath, manifest))))
        return;
    throw new Error(`${(0, path_1.basename)(projectPath)} looks like a code repo (it has a build manifest) and has no `
        + `${workspace_js_1.SPEC_REPO_MARKER}/ yet.\n`
        + 'This pack installs a project skeleton, which belongs in the documents repo. Code repos are\n'
        + 'wired from there instead:\n'
        + '    cd <documents-repo>\n'
        + `    vsaf install NTAPP --code-repos ${(0, path_1.basename)(projectPath)}\n`
        + 'If this repo really is the project root, re-run with --project-root.');
}
/**
 * Refuse anything the caller typed that cannot work, before a byte is written.
 *
 * Every one of these used to be found late — the repo names at the end of the wiring
 * step, the adopt paths just before the copy — which is after the skills, the hooks,
 * the rules, the artifact tree and a git repo are already on disk. Measured: an
 * install with one mistyped name in `--code-repos` left 55 skills, a scaffolded
 * project and no install record behind, and said one line about it.
 *
 * Reads directories; writes nothing.
 */
function assertInputsUsable(packDir, projectPath, options) {
    // Only for a pack that wires repos. `sdlc` and `autotest-skill` ignore these flags
    // entirely — refusing a name they were never going to read would fail an install
    // that used to succeed, over an argument that does nothing.
    if (!shipsProjectSkeleton(packDir))
        return;
    for (const given of options.adopt ?? []) {
        const problem = (0, bootstrap_repo_js_1.adoptProblem)(projectPath, given);
        if (problem) {
            throw new Error(`${problem}\n`
                + 'Dừng trước khi cài — chưa ghi skill, hook hay config nào. Sửa lại rồi chạy lại đúng lệnh cũ.');
        }
    }
    // A repo this run is about to bring in is not on disk yet, so it cannot be looked
    // for. Naming it in `--code-repos` as well is how a careful user spells out what
    // they expect to be wired, and refusing that would punish the clearer spelling.
    const arriving = new Set([
        ...(options.clone ?? []).map(bootstrap_repo_js_1.targetName),
        ...(options.adopt ?? []).map(given => (0, path_1.basename)((0, path_1.resolve)(projectPath, given))),
    ]);
    const named = (options.codeRepos ?? []).filter(name => !arriving.has((0, path_1.basename)(name)));
    // Kept apart from the list below because the answer is different: the name resolves
    // perfectly well, it just names this project.
    const itself = named.find(name => (0, path_1.resolve)(projectPath, name) === projectPath);
    if (itself) {
        throw new Error(`"${itself}" is the spec repo — it cannot also be one of its code repos.\n`
            + 'Dừng trước khi cài — chưa ghi skill, hook hay config nào. Bỏ tên đó khỏi --code-repos rồi chạy lại.');
    }
    const check = (0, workspace_js_1.validateRepoNames)(projectPath, named);
    if (check.ok)
        return;
    throw new Error(`${check.unknown.map(name => `"${name}"`).join(', ')} `
        + `is not a code repo in or beside ${(0, path_1.basename)(projectPath)}.\n`
        + `Found: ${check.candidates.join(', ') || 'none'}\n`
        + 'Dừng trước khi cài — chưa ghi skill, hook hay config nào. Sửa tên (hoặc bỏ --code-repos) rồi chạy lại.');
}
/**
 * The command that continues this install, spelled out.
 *
 * Rebuilt from the options rather than from `process.argv`, so it is the same string
 * whether the install was started from the command line, from another command, or
 * from a test.
 */
function rerunCommand(pack, options) {
    const parts = ['vsaf', 'install', pack];
    if (options.codeRepos?.length)
        parts.push('--code-repos', options.codeRepos.join(','));
    if (options.clone?.length)
        parts.push('--clone', options.clone.join(','));
    if (options.adopt?.length)
        parts.push('--adopt', options.adopt.join(','));
    if (options.projectName)
        parts.push('--project-name', options.projectName);
    if (options.force)
        parts.push('--force');
    if (options.refresh)
        parts.push('--refresh');
    if (options.projectRoot)
        parts.push('--project-root');
    if (options.skipDeps)
        parts.push('--skip-deps');
    if (options.syncGlobal)
        parts.push('--sync-global');
    return parts.join(' ');
}
/**
 * The steps that write, in the order they run. Named so a failure can say which one
 * it stopped at and what never happened, instead of only naming the error.
 */
const WRITING_STEPS = [
    'cài skill',
    'cài hook + rule',
    'nối dây repo (config, link, file workspace)',
    'sinh workflow + slash command',
];
/**
 * What to print when an install dies part way.
 *
 * Four things, because those are the four a person needs and the single error line
 * gave none of them: where it stopped, what is already done, what is not, and the
 * command that finishes the job. Re-running is safe — measured on the failure this
 * was written for: the same command a second time completed the install, kept every
 * hand edit and duplicated nothing.
 */
function reportFailure(pack, options, step, error, recorded) {
    const done = WRITING_STEPS.slice(0, step);
    const left = WRITING_STEPS.slice(step);
    console.error('');
    console.error(`[vsaf] ✗ Dừng ở bước ${step + 1}/${WRITING_STEPS.length}: ${WRITING_STEPS[step]}`);
    console.error(`[vsaf]   Nguyên nhân: ${error.message}`);
    console.error(`[vsaf]   Đã xong: ${done.length > 0 ? done.join(' · ') : 'chưa bước nào'}`);
    console.error(`[vsaf]   Còn thiếu: ${left.join(' · ')}`);
    console.error('[vsaf]   Sửa nguyên nhân ở trên rồi chạy lại đúng lệnh này — phần đã cài được giữ');
    console.error('[vsaf]   nguyên, không nhân đôi, không mất sửa tay:');
    console.error(`[vsaf]       ${rerunCommand(pack, options)}`);
    console.error(recorded
        ? '[vsaf]   Muốn xoá sạch phần đã cài rồi làm lại: vsaf uninstall ' + pack
        : '[vsaf]   Chưa ghi được sổ cài đặt (dự án chưa có .vsaf/ lẫn cây artifact) nên `vsaf uninstall`'
            + ' sẽ không dọn được — chạy `vsaf init` trước nếu muốn gỡ được về sau.');
    console.error('');
}
/**
 * Files in a code repo that hold the repo's own content alongside ours: an install
 * edits them in place, so they must never reach the list of paths an uninstall
 * deletes. They are restored by removing our block instead.
 */
exports.SHARED_IN_CODE_REPO = [
    (0, path_1.join)('.claude', 'settings.json'),
    'CLAUDE.md',
    '.gitignore',
    ...ide_mirror_js_1.IDE_MIRRORS,
];
/** Keep only the paths the installer owns outright and may therefore delete. */
function ownedBy(repo, paths) {
    const shared = new Set(exports.SHARED_IN_CODE_REPO.map(name => (0, path_1.join)(repo, name)));
    return paths.filter(path => !shared.has(path));
}
/**
 * Set up the multi-repo layout around a spec repo: fill in the project name, put a
 * commit guard in each repo, generate the config that tells a code repo where the
 * spec repo is, link the skills, record what kind of code each repo may hold, and
 * write the editor workspace file.
 *
 * Nothing reaches another repo unless the caller names it: writing into every
 * sibling that merely looks like a repo would touch unrelated projects sharing the
 * parent directory, which is not an install's decision to make.
 *
 * Paths come back relative to the spec repo, so one reaching into a sibling stays
 * correct after the workspace is moved or cloned.
 */
function wireWorkspace(packDir, projectPath, options) {
    const nothing = { created: [], scoped: [] };
    if (!(0, fs_1.existsSync)((0, path_1.join)(packDir, 'config', 'bmm-config.template.yaml')))
        return nothing;
    const projectName = (0, project_name_js_1.resolveProjectName)(projectPath, options.projectName);
    const written = [];
    const scoped = [];
    // Relative throughout, so a path reaching into a sibling repo stays correct after
    // the whole workspace is moved or cloned somewhere else.
    const snapshot = () => ({
        created: written.map(path => (0, path_1.relative)(projectPath, path)),
        scoped: [...scoped],
    });
    const progress = () => options.onProgress?.(snapshot());
    /**
     * Someone joining a project that is already set up recreates only what is
     * machine-local. The rest arrived with their clone, and rewriting a committed file
     * would put a diff in their working tree that nobody asked for — which is why the
     * older script kept this a separate mode.
     */
    const refresh = Boolean(options.refresh);
    // A project directory with no repo yet gets one, so the artifacts about to be
    // generated can be reviewed and committed. Nothing is committed here.
    if ((0, bootstrap_repo_js_1.initGitRepo)(projectPath))
        console.log('[vsaf] Started a git repo here');
    // Code repos given by url are cloned beside this one, which is where the layout
    // expects them. Naming them by url is consent enough to wire them afterwards.
    // Repos given by url are cloned in; repos already on disk are copied in. Both end up
    // beside this one, and both count as named — so they are wired without being asked
    // about again.
    const broughtIn = [
        ...(0, bootstrap_repo_js_1.cloneCodeRepos)(projectPath, options.clone ?? []),
        ...(0, bootstrap_repo_js_1.adoptCodeRepos)(projectPath, options.adopt ?? []),
    ].map(path => (0, path_1.relative)(projectPath, path));
    // The project's own skeleton, built first and unconditionally.
    //
    // Installing this pack means "this directory is the project root" — code repos are
    // never installed into, they are wired from here. Gating the skeleton on the
    // artifact tree already existing made it chicken-and-egg: a new project got the
    // skills and none of the skeleton, so 28 skills had no config to read.
    //
    // This half used to come from copying the base template, which is why replacing
    // only the bootstrap script left it missing.
    if (!refresh) {
        (0, spec_scaffold_js_1.scaffoldArtifactTree)(projectPath);
        // The design-system directory is only half of what its skills need: they read
        // their schemas and procedures out of `design-system/_shared/`, which scaffolding
        // left empty.
        written.push(...(0, spec_scaffold_js_1.deployDesignSystemShared)(packDir, projectPath));
        const keep = (0, spec_scaffold_js_1.reserveProjectSkills)(projectPath);
        if (keep)
            written.push(keep);
        const context = (0, spec_scaffold_js_1.deployProjectContext)(packDir, projectPath, projectName);
        if (context)
            written.push(context);
        const readme = (0, spec_scaffold_js_1.deployProjectReadme)(packDir, projectPath);
        if (readme)
            written.push(readme);
        written.push(...(0, spec_scaffold_js_1.deployRepoAssets)(packDir, projectPath));
        const moduleConfig = (0, spec_scaffold_js_1.deployModuleConfig)(packDir, projectPath);
        if (moduleConfig)
            written.push(moduleConfig);
        const specConfig = (0, spec_scaffold_js_1.writeSpecRepoConfig)(projectPath, projectName);
        if (specConfig)
            written.push(specConfig);
        (0, project_name_js_1.applyProjectName)(projectPath, projectName);
    }
    const specHook = (0, precommit_js_1.installPreCommitHook)(packDir, projectPath);
    if (specHook)
        written.push(specHook);
    progress();
    /**
     * The editor workspace file, written whether or not any code repo is wired yet.
     *
     * Committed, so a refresh leaves it as it came from git.
     */
    const emitWorkspaceFile = (repos) => {
        if (refresh)
            return;
        const file = (0, workspace_file_js_1.writeWorkspaceFile)(projectPath, projectName, repos);
        written.push(file);
        console.log(`[vsaf] Workspace file: ${(0, path_1.basename)(file)}`);
    };
    // Repos that arrived from a project link were never named one at a time. A project of
    // a dozen repos always holds a few that carry no build manifest — documents, shared
    // configuration, a sandbox — and those are skipped with a word rather than thrown at
    // the user, because what they typed was the project's name, not this repo's. A name
    // typed by hand into `--code-repos` still fails loudly: there, a typo is the likely
    // cause and silence would look like success.
    const wirable = broughtIn.filter(name => {
        if ((0, workspace_js_1.isCodeRepo)((0, path_1.resolve)(projectPath, name)))
            return true;
        console.log(`[vsaf] ${name} không có manifest build — giữ lại trên đĩa, không nối dây`);
        return false;
    });
    // Resolved after scaffolding, so the marker it looks for is already there.
    const workspace = (0, workspace_js_1.resolveWorkspace)(projectPath, [...new Set([...(options.codeRepos ?? []), ...wirable])]);
    if (workspace.codeRepos.length === 0) {
        if (workspace.candidates.length > 0) {
            // Listed, never pre-composed into a command: the list includes anything with a
            // build manifest nearby, and wiring all of it would reach into other projects.
            console.log('[vsaf] Code repos found near this spec repo:');
            for (const candidate of workspace.candidates) {
                console.log(`    ${(0, workspace_js_1.candidateName)(projectPath, candidate)}`);
            }
            console.log('[vsaf] Name only the ones belonging to this project: --code-repos <a>,<b>');
        }
        // The project still gets its workspace file, holding the documents repo alone.
        // Code repos are added to it by installing again once they exist.
        emitWorkspaceFile([]);
        progress();
        return snapshot();
    }
    // More than one front end means more than one design system, each namespaced so
    // one repo's tokens cannot overwrite another's.
    const designSystems = (0, ds_registry_js_1.resolveDesignSystems)(projectPath, workspace.codeRepos);
    if (designSystems.warning)
        console.log(`[vsaf] ${designSystems.warning}`);
    if (designSystems.registry) {
        written.push(designSystems.registry);
        console.log(`[vsaf] Design systems: ${designSystems.roots.size}, listed in ${ds_registry_js_1.DS_FAMILY}/${ds_registry_js_1.REGISTRY_FILE}`);
    }
    written.push(...(0, repos_config_js_1.deployReposConfig)(packDir, {
        specRepo: projectPath,
        codeRepos: workspace.codeRepos,
        projectName,
        designSystemRoots: designSystems.roots,
    }), ...(0, repos_config_js_1.linkCanonicalSkills)(projectPath, workspace.codeRepos));
    // Each code repo records what kind of code it may hold, and gets the hook that
    // enforces it. The record lives in the code repo, not the spec repo, because that
    // is where an agent about to write a file reads it.
    for (const repo of workspace.codeRepos) {
        // The block goes in the code repo's committed CLAUDE.md, so a refresh skips it.
        if (!refresh)
            (0, repo_scope_js_1.writeScopeBlock)(repo);
        // Recorded whether or not a block was written: this is the list of repos an
        // uninstall has to repair, and a repo that already had the block still received
        // everything below.
        scoped.push((0, path_1.relative)(projectPath, repo));
        const hook = (0, precommit_js_1.installPreCommitHook)(packDir, repo);
        if (hook)
            written.push(hook);
        // The same event hooks and coding rules as the spec repo: an agent writing code
        // runs with the code repo open, so gates wired only into the spec repo never fire.
        //
        // Files shared with the repo's own content are edited, never listed for removal —
        // an uninstall repairs them through `scopedRepos` instead. Listing them once
        // deleted a code repo's CLAUDE.md outright.
        written.push(...ownedBy(repo, (0, hooks_js_1.wireHooksInto)(packDir, projectPath, repo)));
        written.push(...ownedBy(repo, (0, ide_mirror_js_1.mirrorProjectSkills)(projectPath, repo)));
        if (!refresh) {
            written.push(...ownedBy(repo, (0, rules_js_1.deployRules)(packDir, repo, (0, rules_js_1.detectStack)(repo))));
            if (options.codeGitignore)
                (0, gitignore_js_1.updateGitignore)(repo, options.codeGitignore);
        }
        const detected = (0, repo_scope_js_1.detectRepoScope)(repo);
        console.log(`[vsaf]   ${(0, path_1.basename)(repo)}: ${detected.scope} — ${detected.signal}`);
        progress();
    }
    emitWorkspaceFile(workspace.codeRepos);
    console.log(`[vsaf] Wired ${workspace.codeRepos.length} code repo(s) as project "${projectName}"`);
    return snapshot();
}
/**
 * Every file a pack ships under `hooks/`, as paths relative to that directory.
 *
 * All of them are recorded, not just the scripts: the shared library, the test
 * folder and the README were installed too, and anything left out of the record
 * cannot be taken back.
 */
function hookFileNames(packDir, sub = '') {
    const dir = (0, path_1.join)(packDir, 'hooks', sub);
    if (!(0, fs_1.existsSync)(dir))
        return [];
    return (0, fs_1.readdirSync)(dir, { withFileTypes: true }).flatMap(entry => {
        const path = sub ? `${sub}/${entry.name}` : entry.name;
        if (entry.isDirectory())
            return hookFileNames(packDir, path);
        // The wiring file describes the hooks; it is never installed as one.
        return path === 'settings.json' ? [] : [path];
    });
}
// Skills excluded from global deployment — "setup" is replaced by `vsaf install` CLI command
const SKIP_SKILLS = ['setup'];
/**
 * Deploy a pack's `_shared/` assets (helper files skills reference at runtime,
 * e.g. the sonar-viettel quality profile/gate) to `<skillsDir>/_shared/<pack>/`.
 *
 * Namespaced by pack so two packs' helpers never collide, and always overwritten
 * (no --force) so helpers stay in sync with the skills that read them. Returns
 * the deployed entry name, or null when the pack ships no `_shared/`.
 *
 * Deploying skills is `vsaf install`'s job alone, so this belongs to it — the assets a
 * skill reads have to arrive with the skill.
 */
function deploySharedAssets(packDir, pack, skillsDir) {
    const sharedSrc = (0, path_1.join)(packDir, '_shared');
    if (!(0, fs_1.existsSync)(sharedSrc))
        return null;
    const sharedTarget = (0, path_1.join)(skillsDir, '_shared', pack);
    if ((0, fs_1.existsSync)(sharedTarget)) {
        (0, fs_1.rmSync)(sharedTarget, { recursive: true, force: true });
    }
    (0, fs_1.mkdirSync)((0, path_1.join)(skillsDir, '_shared'), { recursive: true });
    (0, fs_1.cpSync)(sharedSrc, sharedTarget, { recursive: true });
    return `_shared/${pack}`;
}
// ── Deploy Skills ──
function deploySkills(packDir, packName, skills, targetDir, options) {
    (0, fs_1.mkdirSync)(targetDir, { recursive: true });
    const result = { deployed: [], skipped: [] };
    for (const skill of skills) {
        if (SKIP_SKILLS.includes(skill))
            continue;
        const targetName = options.noPrefix ? skill : `${packName}-${skill}`;
        const sourceDir = (0, path_1.join)(packDir, skill);
        const destDir = (0, path_1.join)(targetDir, targetName);
        if (!(0, fs_1.existsSync)((0, path_1.join)(sourceDir, 'SKILL.md')))
            continue;
        if ((0, fs_1.existsSync)(destDir)) {
            if (options.force) {
                (0, fs_1.rmSync)(destDir, { recursive: true, force: true });
            }
            else {
                result.skipped.push(targetName);
                continue;
            }
        }
        (0, fs_1.cpSync)(sourceDir, destDir, { recursive: true });
        result.deployed.push(targetName);
    }
    return result;
}
// ── Check Binaries ──
const BINARIES = [
    { name: 'gh', required: true },
    { name: 'docker', required: false },
    { name: 'sonar-scanner', required: false },
];
function checkBinaries() {
    return BINARIES.map(({ name, required }) => {
        try {
            const output = (0, child_process_1.execSync)(`${name} --version`, { stdio: 'pipe', encoding: 'utf-8' });
            const version = output.trim().split('\n')[0] || undefined;
            return { name, found: true, required, version };
        }
        catch {
            return { name, found: false, required };
        }
    });
}
// ── Install Graphify ──
const IS_WIN = process.platform === 'win32';
const LOCAL_BIN = (0, path_1.join)((0, os_1.homedir)(), '.local', 'bin');
const PYTHON = IS_WIN ? 'python' : 'python3';
function resolveGraphifyBin() {
    try {
        (0, child_process_1.execSync)('graphify --help', { stdio: 'pipe' });
        return 'graphify';
    }
    catch { }
    // pipx installs to ~/.local/bin/ — may not be on PATH after fresh install
    const localPath = (0, path_1.join)(LOCAL_BIN, IS_WIN ? 'graphify.exe' : 'graphify');
    try {
        (0, child_process_1.execSync)(`"${localPath}" --help`, { stdio: 'pipe' });
        return `"${localPath}"`;
    }
    catch { }
    return null;
}
function ensurePipx() {
    // Already on PATH?
    try {
        (0, child_process_1.execSync)('pipx --version', { stdio: 'pipe' });
        return 'pipx';
    }
    catch { }
    // Try brew (macOS only) — skip auto-update for speed
    if (!IS_WIN) {
        try {
            (0, child_process_1.execSync)('HOMEBREW_NO_AUTO_UPDATE=1 brew install pipx', { stdio: 'inherit' });
            return 'pipx';
        }
        catch { }
    }
    // Fallback: pip install (cross-platform)
    try {
        (0, child_process_1.execSync)(`${PYTHON} -m pip install --user pipx`, { stdio: 'inherit' });
        return `${PYTHON} -m pipx`;
    }
    catch { }
    return null;
}
function installGraphify() {
    let version;
    let skillDeployed = false;
    // Check if graphify binary already exists
    let graphifyCmd = resolveGraphifyBin();
    if (!graphifyCmd) {
        // Need pipx to install graphify
        const pipxCmd = ensurePipx();
        if (!pipxCmd) {
            return {
                installed: false,
                skillDeployed: false,
                error: 'Could not install pipx — requires brew (macOS), python3+pip (Linux), or python+pip (Windows)',
            };
        }
        try {
            (0, child_process_1.execSync)(`${pipxCmd} install graphifyy`, { stdio: 'inherit' });
        }
        catch {
            // May fail if already installed via pipx but not on PATH
        }
        graphifyCmd = resolveGraphifyBin();
        if (!graphifyCmd) {
            return {
                installed: false,
                skillDeployed: false,
                error: 'graphify not found after install — restart terminal or run: pipx ensurepath',
            };
        }
    }
    // Deploy skill to Claude Code
    try {
        (0, child_process_1.execSync)(`${graphifyCmd} install --platform claude`, { stdio: 'pipe', encoding: 'utf-8' });
        skillDeployed = true;
    }
    catch {
        // Skill deployment failed but binary works
    }
    // Read version from deployed skill
    try {
        const versionFile = (0, path_1.join)((0, os_1.homedir)(), '.claude', 'skills', 'graphify', '.graphify_version');
        if ((0, fs_1.existsSync)(versionFile)) {
            version = (0, fs_1.readFileSync)(versionFile, 'utf-8').trim();
        }
    }
    catch {
        // Version file not available
    }
    return { installed: true, version, skillDeployed };
}
// ── Plugin Guide ──
const PLUGIN_GUIDE = `
┌──────────────────────────────────────────────────────────┐
│  Manual setup required:                                  │
│                                                          │
│  1. Claude plugin (inside Claude Code session):          │
│     superpowers   → /install-plugin superpowers           │
│                                                          │
│  2. GitHub CLI (if not installed):                       │
│     brew install gh      (macOS)                         │
│     apt install gh       (Linux)                         │
│     winget install GitHub.cli  (Windows)                 │
└──────────────────────────────────────────────────────────┘`;
// ── Main Install ──
/**
 * Install a pack that ships the script which wires a project up.
 *
 * The split of labour is deliberate. This function lays the project out — the
 * directory, its first commit, the pack's files, the code repos beside it — and then
 * hands over. The pack's script owns the wiring, and stays the source of truth for it:
 * those steps changed by 400 lines in twelve days upstream, and a second
 * implementation here would be chasing them forever.
 *
 * The record covers what this function wrote, and nothing the script wrote. That is
 * said out loud at the end rather than found out at uninstall time.
 */
function installDelegated(pack, packDir, projectPath, packInfo, options) {
    (0, delegate_js_1.refuseHomeDirectory)(projectPath);
    const verbose = options.verbose === true;
    const { bash } = (0, delegate_js_1.checkEnvironment)();
    const projectName = (0, project_name_js_1.resolveProjectName)(projectPath, options.projectName);
    // Both modes mean "the project is already laid out, wire it again", so neither
    // touches the files that are already there.
    const rewiring = options.refresh === true || options.upgrade === true;
    (0, delegate_js_1.assertWiringScriptPresent)(projectPath, packInfo, rewiring);
    const written = [];
    const wired = [];
    // Whether this run is the one that made the repo's only commit. Just this run's: an
    // install into a repo that already had history must not rewrite somebody else's commit.
    let firstCommit = false;
    if (rewiring) {
        console.log(`[vsaf] 1/2  ${(0, path_1.basename)(projectPath)} đã có — chỉ cấu hình lại`);
        // `--upgrade` is the lead adding repos to a project, so it fetches. `--refresh` is not:
        // it is the machine-local half of a project that already exists, and someone joining
        // uses `--clone`, which brings the spec repo this command has to run inside.
        if (options.upgrade) {
            wired.push(...(0, bootstrap_repo_js_1.cloneCodeRepos)(projectPath, options.clone ?? []));
            wired.push(...(0, bootstrap_repo_js_1.adoptCodeRepos)(projectPath, options.adopt ?? []));
        }
    }
    else {
        written.push(...(0, delegate_js_1.copyPackIntoProject)(packDir, projectPath, packInfo, { force: options.force }));
        (0, delegate_js_1.repairCommandFrontMatter)(projectPath);
        // One line, not three: the count and the repairs are the same fact — what arrived.
        // Which four files were repaired belongs in the log, not on screen.
        // Said as the job it is, not as the code that does it. "copy pack" and "vá front
        // matter file command" were this installer's own vocabulary, and the people running it
        // include PO and BA. The counts went too: how many files arrived, and how many command
        // headers needed fixing, are not things anybody decides anything with.
        console.log(`[vsaf] 1/4  Cài bộ ${pack} vào dự án`);
        // After the copy, not before: a repo made first has nothing to commit yet, and the
        // upstream instructions put their commit at the end of the copy step for the same
        // reason.
        // `initGitRepo` declines quietly in two cases — the directory already sits inside
        // another repo, or it holds repos of its own — and both leave the project without a
        // `.git`. The pack's script requires one and stops with "chưa là git repo", forty
        // lines into its own output, which reads as the script being broken. Measured on
        // Windows inside a OneDrive folder that was already under a repo. So check what
        // actually happened and say it here, where the cause is still visible.
        (0, bootstrap_repo_js_1.initGitRepo)(projectPath);
        firstCommit = (0, bootstrap_repo_js_1.commitInitial)(projectPath, `chore: bootstrap ${projectName} from ${pack} pack`);
        const started = (0, fs_1.existsSync)((0, path_1.join)(projectPath, '.git'));
        console.log(`[vsaf] 2/4  Tạo git + commit đầu cho thư mục dự án${started ? '' : ' — KHÔNG tạo được'}`);
        if (!started) {
            throw new Error(`${(0, path_1.basename)(projectPath)} chưa phải git repo, và script của pack đòi có.\n`
                + '  Thường vì thư mục này đã nằm TRONG một git repo khác — kiểm bằng:\n'
                + `    git -C "${projectPath}" rev-parse --show-toplevel\n`
                + '  Cách chữa: dựng dự án ở chỗ không nằm trong repo nào, hoặc "git init" tay ở đây rồi chạy lại.\n'
                + '  Bộ quy trình đã copy vào thư mục này ở bước 1/4; phần cấu hình thì chưa chạy — chưa cài hook,\n'
                + '  chưa sinh config cho code repo nào.');
        }
        // Snapshotted before the fetch, so the line below can tell a repo that arrived from
        // one that was already sitting there. `cloneInto` returns both — a repo already in
        // place is kept and reported, which is right, but counting it as cloned told people
        // six repos came down when five did.
        const parent = (0, path_1.dirname)(projectPath);
        const beforeFetch = new Set((0, fs_1.existsSync)(parent) ? (0, fs_1.readdirSync)(parent).map(name => (0, path_1.join)(parent, name)) : []);
        // Only brought in, not wired: the script detects whatever sits beside the project,
        // so putting them there is the whole contribution.
        wired.push(...(0, bootstrap_repo_js_1.cloneCodeRepos)(projectPath, options.clone ?? []));
        wired.push(...(0, bootstrap_repo_js_1.adoptCodeRepos)(projectPath, options.adopt ?? []));
        // `--code-repos` names siblings that are already on disk, so there is nothing to
        // bring in for them — but printing "không có repo nào" right after the user typed the
        // flag reads as "your flag was ignored", when in fact the wiring step below picks
        // them up. Say which of the two happened.
        const beside = options.codeRepos ?? [];
        // Three different things happened, so three different sentences — a verb and a count
        // each. The repo names are not repeated: git already printed a `Cloning` line per
        // repo just above, and twelve of them made this line longer than everything else.
        const fetched = wired.filter(path => !beforeFetch.has(path)).length;
        console.log(`[vsaf] 3/4  ${broughtLine(fetched, wired.length - fetched, beside.length)}`);
    }
    // Before handing over: the script decides a project's scope by looking at what sits
    // beside it, and unattended it accepts all of it. Only proceed when this install put
    // those siblings there, or was told which ones count.
    const named = (options.codeRepos?.length ?? 0) > 0
        || (options.clone?.length ?? 0) > 0
        || (options.adopt?.length ?? 0) > 0;
    (0, delegate_js_1.assertScopeIsKnown)(projectPath, wired, named, pack);
    (0, delegate_js_1.warnUnwirableRepos)(projectPath, options.codeRepos ?? []);
    const passthrough = [];
    if (options.refresh)
        passthrough.push('--refresh');
    if (options.upgrade)
        passthrough.push('--upgrade');
    if (options.dryRun)
        passthrough.push('--dry-run');
    passthrough.push(...(options.passthrough ?? []));
    // Printed always, not only with `--verbose`. Counting 1/4, 2/4, 3/4 and then stopping
    // reads as a step that went missing — while in fact the longest one is about to run, and
    // saying so is what tells someone the terminal is working rather than stuck.
    console.log(`[vsaf] ${rewiring ? '2/2  Cấu hình lại' : '4/4  Cấu hình repo'}`);
    (0, delegate_js_1.runWiring)(bash, projectPath, packInfo, { projectName, passthrough, verbose });
    // The wiring is what sets the project's real name, and it runs after the commit — so
    // fold its edits in, or the commit a lead pushes still carries the template's name and
    // every teammate's install stops at the pack's self-test. Silent when it works: this is
    // the commit the previous line already announced, not a step of its own.
    // Right after the wiring, before anything reads the settings again: the pack's script
    // merges its event hooks by replacing the whole `hooks` object, which takes vsaf's
    // `SessionStart` with it. `init` puts it back on a first install and is skipped on every
    // later run, so without this a refresh, a clone or an upgrade ends with telemetry that
    // has no session id — and says nothing about it.
    if (!options.dryRun)
        (0, session_hook_js_1.ensureSessionHook)(projectPath);
    if (firstCommit)
        (0, bootstrap_repo_js_1.refreshInitialCommit)(projectPath);
    // Recorded so an uninstall can take the copy back. Deliberately not claiming the
    // wiring: the script wrote it, and guessing at that list would delete files it
    // never made.
    const record = {
        pack,
        canonicalDir: packInfo.skillsRoot ?? '.claude/skills',
        skills: packInfo.skillsKeepInProject ?? [],
        hooks: [],
        rules: [],
        commands: [],
        hasWorkflows: Object.keys(packInfo.workflows).length > 0,
        wired: wired.map(path => (0, path_1.relative)(projectPath, path)),
        scopedRepos: [],
    };
    try {
        (0, manifest_js_1.recordInstall)(projectPath, record);
    }
    catch (error) {
        console.log(`[vsaf] ⚠ Không ghi được sổ cài đặt — ${error.message}`);
    }
    // Nothing closing here. The only thing left to say is what to run next, and the CLI
    // decides that: an init still owed prints its own hint, otherwise `doctor`. Saying
    // "done, run doctor" above a hint pointing at `init` named the wrong next step.
    return {
        deploy: { deployed: [], skipped: [] },
        binaries: [],
        depsRan: false,
        graphify: { installed: false, skillDeployed: false },
        scaffold: { commandsCreated: [], commandsSkipped: [], workflowsCreated: [] },
        globalSynced: [],
        wired,
        problems: [],
        flowDir: packDir,
    };
}
/**
 * Kết quả để in ra, dựng lại từ sổ sau khi script của flow đã chạy xong.
 *
 * Script của flow chạy trong một tiến trình khác, nên engine không nhìn thấy nó rải
 * được những gì — chỉ sổ ghi nó để lại mới nói được. Sổ rỗng thì kết quả rỗng, chứ
 * không phải một con số đoán ra.
 *
 * `problems` đến từ chính lưới an toàn của engine chạy lại trên sổ đó, không phải một
 * mảng rỗng cho có: trả rỗng thì `if (result.problems.length > 0) process.exit(1)` ở
 * lớp lệnh không bao giờ bắn, và một lượt cài thủng lỗ đọc ra y hệt một lượt cài sạch.
 */
function readInstallResult(projectPath, record, packDir) {
    return {
        flowDir: packDir,
        deploy: { deployed: record?.skills ?? [], skipped: [] },
        binaries: [],
        depsRan: false,
        graphify: { installed: false, skillDeployed: false },
        scaffold: { commandsCreated: record?.commands ?? [], commandsSkipped: [], workflowsCreated: [] },
        globalSynced: [],
        wired: record?.wired ?? [],
        problems: record ? (0, selftest_js_1.selfTest)(projectPath, record) : [],
    };
}
/**
 * Cảnh báo khi cần cho lượt cài do script của flow làm.
 *
 * Engine không rải file nào ở nhánh này nên không có gì để tự thuật lại lúc thành công —
 * tài liệu §2 kết thúc bằng dòng chỉ bước tiếp theo, không có dòng "cài xong" hay đếm
 * skill chen vào sau đó. Lượt HỎNG thì khác: im lặng ở đó đọc ra như đã xong, nên hàm vẫn
 * phải nói flow đến từ đâu và ở bản nào.
 */
function reportFlowScriptInstall(pack, source, projectPath, record, result, failed = false) {
    // Không tường thuật "cài xong" ở đây nữa, và không in số skill trong sổ: tài liệu §2
    // kết thúc bằng dòng chỉ bước tiếp theo, và hai dòng đó chen vào đúng sau nó. Bản flow
    // vẫn tra được bằng `vsaf status`, vẫn nằm trong sổ cài đặt (`flowCommit`) và trong
    // `.vsaf/install.log` — không mất dấu vết, chỉ không chiếm màn hình.
    //
    // Lượt HỎNG thì vẫn phải nói, vì im lặng ở đó là để người dùng tưởng đã xong.
    if (failed) {
        const from = source.origin === 'repo'
            ? `repo flows @ ${source.commit?.slice(0, 8) ?? '?'}`
            : 'bản kèm theo gói npm';
        console.log(`\n[vsaf] Flow "${pack}" — file cài của chính nó đã dừng giữa chừng (${from})`);
    }
    // Không sổ thì không có con số nào để nói, và "0 skill" ngay sau một lượt vừa rải một
    // skill là nói sai với người dùng. Nói đúng thứ đang xảy ra: engine không nhìn được
    // vào tiến trình con, nên sổ là thứ duy nhất kể lại được — thiếu nó thì cả tự kiểm
    // lẫn `vsaf uninstall` đều mất chỗ bám.
    //
    // Hai nguyên nhân khác nhau, hai lời khuyên khác nhau, và `recordPaths` phân biệt
    // được: dự án không có chỗ nào để ghi, hay có chỗ mà script không ghi. Khuyên chạy
    // `vsaf init` ở ca thứ hai là khuyên một việc không thể có tác dụng — `init` không bao
    // giờ ghi sổ cài đặt, chỉ `install`/`apply-pack` ghi.
    if (!record) {
        console.log('[vsaf] ⚠ Lượt cài này không có sổ — engine không tự kiểm được, và `vsaf uninstall` sẽ không dọn được');
        if ((0, manifest_js_1.recordPaths)(projectPath, pack).length === 0) {
            console.log('[vsaf]   → dự án chưa có .vsaf/ lẫn cây artifact nên không có chỗ nào để ghi sổ');
            console.log('[vsaf]   → chạy `vsaf init` rồi cài lại nếu cần gỡ về sau');
        }
        else {
            console.log(`[vsaf]   → file cài của flow "${pack}" không ghi sổ: nó cần gọi \`vsaf apply-pack\` để engine ghi hộ`);
            console.log('[vsaf]   → cài lại cũng không đổi được điều đó — cần sửa ở chính flow');
        }
        return;
    }
    if (result.problems.length > 0) {
        // Nói thẳng mối liên hệ khi script vừa thoát khác 0: `apply-pack` thoát 1 đúng vì
        // lưới an toàn thấy những vấn đề dưới đây, nên đây là câu trả lời cho "vì sao hỏng",
        // không phải một ghi chú bên lề.
        console.log(failed
            ? `\n[vsaf] ⚠ Tự kiểm thấy ${result.problems.length} vấn đề — đây cũng là lý do file cài của flow thoát khác 0:`
            : `\n[vsaf] ⚠ Tự kiểm thấy ${result.problems.length} vấn đề:`);
        for (const problem of result.problems)
            console.log(`    ${problem}`);
        console.log('[vsaf] Chạy lại lệnh này là an toàn — phần đã cài được giữ nguyên.');
    }
}
/**
 * Ghi thư mục sản phẩm mà flow khai vào phần telemetry của project.
 *
 * Đây từng là việc của `vsaf init`, và chính nó là lý do `init` phải đi lấy flow về —
 * một lệnh chỉ dựng thư mục mà lại chạm git. Việc này thuộc về `install`: đây là lệnh
 * biết flow nào đang được cài, và nó đã cầm sẵn thư mục flow trong tay.
 *
 * Bỏ qua khi chưa có `.vsaf/config.yaml`: tạo file cấu hình là việc của `init`, và một
 * project chỉ có mỗi config do `install` đẻ ra sẽ đọc ra là đã init trong khi chưa.
 *
 * Đọc `pack.yaml` không ra thì im lặng bỏ qua — bước rải skill mới là chỗ báo lỗi đó,
 * và làm hỏng cả lượt cài ở đây chỉ biến một lỗi thành hai.
 */
function applyFlowTelemetry(projectPath, flowDir) {
    if (!flowDir)
        return;
    const configPath = (0, path_1.join)(projectPath, '.vsaf', 'config.yaml');
    if (!(0, fs_1.existsSync)(configPath))
        return;
    let artifacts;
    try {
        artifacts = (0, skill_js_1.readPackInfoFrom)(flowDir).telemetry?.artifacts;
    }
    catch {
        return;
    }
    if (!artifacts)
        return;
    (0, init_js_1.writeProjectConfig)(configPath, artifacts);
}
/**
 * Cài một flow vào project.
 *
 * Vỏ mỏng quanh `runInstall` để phần telemetry của flow được ghi trên MỌI đường cài —
 * script của chính flow, script `wiring` của pack, hay đường engine tự rải. Ba đường đó
 * `return` ở ba chỗ khác nhau, nên đặt bước này ở từng chỗ là ba lần phải nhớ; ở đây
 * thì không nhớ cũng đúng. Chạy thử không trả về `flowDir`, nên nó không ghi gì.
 */
function execInstall(input, projectPath, options = {}) {
    const result = runInstall(input, projectPath, options);
    applyFlowTelemetry(projectPath, result.flowDir);
    return result;
}
function runInstall(input, projectPath, options = {}) {
    // Validate pack is a simple name (no URLs or paths)
    if (input.includes('/') || input.includes('\\') || input.startsWith('.') || input.startsWith('http')) {
        throw new Error(`"${input}" is not a valid pack name. Use a built-in pack name (e.g. "sdlc").`);
    }
    // Canonical spelling from here on: the skill prefix, the install record and the
    // workflow directory all have to agree, whatever casing was typed.
    const pack = (0, skill_js_1.resolvePackName)(input);
    // Step 0: A pack pinning third-party skills must not deploy them unverified.
    (0, skills_lock_js_1.assertSkillsLock)(projectPath);
    // Test và lệnh `apply-pack` đưa thẳng thư mục vào, nên nhánh đó không đi qua repo
    // flows. Đường người dùng gõ thì có.
    let flowSource;
    let packDir;
    if (options._packDir) {
        packDir = options._packDir;
    }
    else if (options.dryRun) {
        // "Nothing will be written" phải đúng với cả những gì nằm ngoài project. Kéo flow
        // về là ghi vào cache dưới VSAF_HOME — đo được 228 KB sau một lượt chạy thử — và
        // trên đường mặc định còn là trả giá một lượt clone qua mạng cho một lệnh chỉ để
        // đọc. Nên chạy thử chỉ đọc bản đã có sẵn trên máy.
        const local = (0, flow_source_js_1.localFlowDir)(pack);
        if (!local) {
            throw new Error(`Chưa có bản nào của flow "${pack}" trên máy để dựng kế hoạch.\n`
                + '  Chạy thử không kéo gì từ repo flows, vì nó hứa không ghi gì — kể cả cache.\n'
                + `  Bỏ --dry-run để engine kéo flow về:  vsaf install ${pack}`);
        }
        packDir = local;
        console.log(`[vsaf] Chạy thử đọc bản flow đã có trên máy (${local}) — không kéo gì từ repo flows`);
    }
    else {
        // `flowSourceForRun` chứ không phải `fetchFlow`: một lệnh như `install <flow> --new`
        // chạy `init` trước rồi mới tới đây, và cả hai đều cần nội dung flow. Câu "đang dùng
        // bản kèm theo" cũng do nó in, đúng một lần cho cả lệnh.
        flowSource = (0, flow_source_js_1.flowSourceForRun)(pack, { refresh: options.refreshFlows === true });
        packDir = flowSource.dir;
    }
    const packInfo = (0, skill_js_1.readPackInfoFrom)(packDir);
    // Trước khi ghi bất cứ thứ gì: flow đòi engine mới hơn thì dừng tại đây, để project
    // không ở lại trạng thái cài dở mà không ai biết.
    (0, engine_range_js_1.assertEngineSatisfies)(pack, packInfo.requiresEngine, (0, engine_version_js_1.resolveEngineVersion)());
    // Before anything is written: refuse to make a code repo into a project root, and
    // refuse anything typed that cannot resolve. Both belong here, ahead of `--dry-run`
    // — a plan drawn from input that will not work is a plan of something that will
    // never happen.
    assertProjectRoot(packDir, projectPath, options.projectRoot);
    assertInputsUsable(packDir, projectPath, options);
    // A plan and nothing else. Printed before any write so it can be read by whoever is
    // about to hand this command to someone else.
    if (options.dryRun) {
        console.log(`\n[vsaf] Plan for "${pack}" — nothing will be written\n`);
        for (const line of (0, plan_js_1.planInstall)(packDir, pack, projectPath, packInfo, options)) {
            console.log(line ? `  ${line}` : '');
        }
        console.log('\n[vsaf] Nothing written. Drop --dry-run to apply.\n');
        return {
            deploy: { deployed: [], skipped: [] },
            binaries: [],
            depsRan: false,
            graphify: { installed: false, skillDeployed: false },
            scaffold: { commandsCreated: [], commandsSkipped: [], workflowsCreated: [] },
            globalSynced: [],
            wired: [],
            problems: [],
        };
    }
    // Flow lấy từ repo LUÔN chạy bằng file cài của chính nó.
    //
    // Cổng này từng là "có repo VÀ có file cài cho OS đang chạy", và cái `VÀ` đó là một lỗ:
    // flow thiếu `install.sh` thì điều kiện false, lượt cài lặng lẽ rơi xuống đường engine
    // cũ, và câu lỗi đúng theo §6 spec — đã viết sẵn trong `runFlowScript` — không đường
    // nào tới được. Đo được: repo có flow chỉ mang `install.ps1`, cài trên Linux ra 62
    // skill với `flowOrigin: repo` và zero cảnh báo. Nguy hơn: NTAPP quên `install.ps1` thì
    // Windows đi đường engine còn Linux đi script của flow — hai OS, một flow, hai kết quả,
    // đúng thứ §7 spec đặt ra để chặn.
    //
    // Bản kèm gói npm vẫn đi đường engine: nó là đường lùi, và §5.1 spec giữ nguyên nó.
    if (flowSource?.origin === 'repo') {
        // Lỗi của script không được nuốt mất phần chẩn đoán.
        //
        // `apply-pack` thoát khác 0 chính là *vì* lưới an toàn thấy thủng lỗ, và ném ngay tại
        // đây khiến `reportFlowScriptInstall` — chỗ duy nhất in danh sách vấn đề — không bao
        // giờ chạy. Đo được: tiến trình con in "0 issue(s)", lệnh ngoài exit 1 với câu quy
        // tội cho file cài của flow, còn vấn đề thật (`.bmm-config.yaml` thiếu
        // `bmad.code_repo_root`) không hiện ra ở đâu — và chạy lại thì y hệt.
        // Ý định của lượt cài đi bằng file, không bằng cờ. Xem `install-plan.ts` cho lý do.
        const plan = (0, install_plan_js_1.buildInstallPlan)({
            flow: pack,
            engineVersion: (0, engine_version_js_1.resolveEngineVersion)(),
            projectPath,
            options,
        });
        // Đo trước, so sau — không đoán. Flow có tự đồng bộ skill ra máy hay không là việc của
        // `install.sh` của nó, nên chỗ duy nhất biết chắc là so hai lần đo.
        const thieuSkillTruocLuot = (0, delegate_js_1.skillsLibraryMissing)(packDir, packInfo);
        const planPath = (0, install_plan_js_1.writeInstallPlan)(plan);
        (0, install_plan_js_1.logInstallPlan)(projectPath, plan);
        let scriptError;
        try {
            (0, flow_script_js_1.runFlowScript)({
                source: flowSource,
                flow: pack,
                projectPath,
                projectName: options.projectName ?? (0, path_1.basename)(projectPath),
                engineVersion: (0, engine_version_js_1.resolveEngineVersion)(),
                planPath,
                // Cờ engine nhận ở dòng lệnh phải tới được lượt cài thật. Trước đây chỉ
                // `passthrough` (phần sau `--`) được chuyển, nên `--skip-deps`, `--force`,
                // `--project-root`, `--verbose` đứng lại ở tiến trình cha.
                flags: {
                    force: options.force === true,
                    skipDeps: options.skipDeps === true,
                    skipGraphify: options._skipGraphify === true,
                    projectRoot: options.projectRoot === true,
                    verbose: options.verbose === true,
                },
                passthrough: options.passthrough ?? [],
            });
        }
        catch (error) {
            // Script chưa hề chạy thì không có sổ nào để soi, và ba dòng chẩn đoán "flow không
            // ghi sổ" ở đó chỉ sai hướng — câu lỗi đã nói đúng thứ cần sửa.
            if (error instanceof flow_script_js_1.FlowScriptNotRunError) {
                (0, install_plan_js_1.dropInstallPlan)(planPath);
                throw error;
            }
            scriptError = error;
        }
        finally {
            (0, install_plan_js_1.dropInstallPlan)(planPath);
        }
        // Đo lại SAU khi script chạy — dùng chung cho cả dòng báo "đã đồng bộ" bên dưới lẫn
        // cảnh báo `--sync-global` phía sau: cùng một phép đo, không lặp lại lời gọi.
        const thieuSkillSauLuot = (0, delegate_js_1.skillsLibraryMissing)(packDir, packInfo);
        // Một dòng, và chỉ khi máy vừa có thư viện skill nhờ lượt này. Máy đã có sẵn thì im —
        // đúng transcript §2, vốn mô tả máy đã chạy `vsaf sync` từ trước.
        if (thieuSkillTruocLuot && !thieuSkillSauLuot) {
            console.log('[vsaf] Đã đồng bộ thư viện skill ra máy (một lần cho cả máy).');
        }
        // Sổ ghi là của lượt cài mà script vừa làm — engine chỉ đóng thêm dấu "lấy từ
        // đâu". Script chưa ghi được sổ nào thì cũng không dựng sổ hộ nó: một sổ rỗng
        // do engine bịa ra sẽ khiến `vsaf uninstall` tưởng không có gì để dọn.
        // Đọc một lần rồi tự dựng bản đã đóng dấu, thay vì ghi xong đọc lại: `recordInstall`
        // gộp bản mới vào bản cũ, mà bản mới ở đây chính là bản cũ cộng hai trường — nên
        // thứ nằm trên đĩa đúng bằng thứ vừa dựng.
        const previous = (0, manifest_js_1.readInstall)(projectPath, pack);
        const record = previous
            ? { ...previous, flowOrigin: flowSource.origin, flowCommit: flowSource.commit }
            : null;
        if (record)
            (0, manifest_js_1.recordInstall)(projectPath, record);
        // Chính engine không tự đọc `syncGlobal` ở nhánh flow tự cài (KHÔNG phải vì biên nữa —
        // kế hoạch lượt cài đã mang cờ này sang tiến trình con; lý do sâu hơn và có từ trước
        // bước tách flow: `installDelegated` return ở trên, còn chỗ đọc `syncGlobal`
        // (`if (packInfo.global && options.syncGlobal)`) nằm sau nó nên nhánh wiring không bao
        // giờ tới — sửa chỗ đó đổi hành vi NTAPP vượt phạm vi lượt này).
        //
        // Nhưng bản thân flow (`install.sh` của NTAPP) có thể tự gọi `vsaf sync` ở BƯỚC RIÊNG
        // của nó — không nhờ engine đọc cờ này. Nên cảnh báo chỉ đúng khi thư viện skill THẬT
        // SỰ vẫn còn thiếu sau lượt chạy (`thieuSkillSauLuot`, đo lại ở trên): gõ cờ, lệnh báo
        // thành công, mà skill vẫn chưa về máy — đó mới là ca cần nói ra. Bỏ qua điều kiện này
        // sẽ in cảnh báo NGAY CẢ KHI thư viện đã về máy nhờ chính flow, mâu thuẫn với dòng "Đã
        // đồng bộ…" vừa in phía trên — hai câu cùng đúng riêng lẻ nhưng đọc chung là sai thông
        // tin, và câu sau còn bảo người dùng làm lại việc vừa xong.
        if (options.syncGlobal === true && thieuSkillSauLuot) {
            console.log('[vsaf] ⚠ --sync-global chưa có tác dụng với flow cài bằng file cài của chính nó.');
            console.log(`[vsaf]   Đồng bộ ra máy bằng lệnh riêng:  vsaf sync ${pack}`);
        }
        const result = readInstallResult(projectPath, record, packDir);
        reportFlowScriptInstall(pack, flowSource, projectPath, record, result, scriptError !== undefined);
        if (scriptError)
            throw scriptError;
        return result;
    }
    // A pack that ships its own wiring script takes the other route. Checked here, after
    // the plan and the pre-flight, so `--dry-run` and the refusals behave the same for
    // both kinds of pack.
    if (packInfo.wiring) {
        return installDelegated(pack, packDir, projectPath, packInfo, options);
    }
    // Where the skills belong. A pack declaring nothing keeps the old behaviour, so
    // `sdlc` installs exactly as it did before the canonical/mirror split existed.
    const canonical = (0, ide_mirror_js_1.resolveSkillTarget)(projectPath, packInfo.canonicalSkillsDir);
    const skillsDir = options._skillsDir ?? canonical.target;
    /**
     * What this run has written so far.
     *
     * Filled in step by step and saved after each one, because it is the only list
     * `vsaf uninstall` has. Written once at the very end, as it used to be, it was
     * never written at all by a run that died half way — so the files that run made
     * could not be taken back.
     *
     * `skills` and `hasWorkflows` say what the pack ships rather than what this run
     * happened to create: on a second install the files are already there, and
     * recording "none created" would make them undeletable.
     */
    const state = {
        pack,
        canonicalDir: (0, path_1.relative)(projectPath, skillsDir),
        skills: [],
        hooks: [],
        rules: [],
        commands: [],
        hasWorkflows: Object.keys(packInfo.workflows).length > 0,
        wired: [],
        scopedRepos: [],
    };
    let recorded = false;
    const keepRecord = () => {
        // Never the reason an install fails, and never what a failing install reports:
        // this runs from inside the failure handler too, and a record that cannot be
        // written there would replace the real error with its own.
        try {
            if ((0, manifest_js_1.recordInstall)(projectPath, state) !== null)
                recorded = true;
        }
        catch (error) {
            console.log(`[vsaf] ⚠ Không ghi được sổ cài đặt — ${error.message}`);
        }
    };
    let deploy = { deployed: [], skipped: [] };
    let wired = { created: [], scoped: [] };
    let scaffold = { commandsCreated: [], commandsSkipped: [], workflowsCreated: [] };
    let workflowCommands = { created: [], owned: [] };
    // Mục `_shared` mà bước 1c thêm vào `deploy.deployed`, nếu pack có. Giữ ở đây để câu
    // tổng kết cuối hàm đếm được đúng số skill.
    let sharedDeployed = null;
    let step = 0;
    try {
        // Step 1: Deploy skills (prefixed with pack name)
        deploy = deploySkills(packDir, pack, packInfo.skillNames, skillsDir, { force: options.force });
        // Step 1b: Deploy bundled skills (no prefix — external dependencies)
        if (packInfo.bundledNames.length > 0) {
            const bundled = deploySkills(packDir, pack, packInfo.bundledNames, skillsDir, { force: options.force, noPrefix: true });
            deploy.deployed.push(...bundled.deployed);
            deploy.skipped.push(...bundled.skipped);
        }
        // Step 1c: Deploy _shared/ helper assets the pack's skills read at runtime
        sharedDeployed = deploySharedAssets(packDir, pack, skillsDir);
        if (sharedDeployed)
            deploy.deployed.push(sharedDeployed);
        // Step 1d: Copies for the IDEs, so editing the canonical skill is enough.
        if (canonical.mirror)
            (0, ide_mirror_js_1.mirrorToIde)(projectPath, skillsDir);
        state.skills = [
            ...packInfo.skillNames.filter(name => !SKIP_SKILLS.includes(name)).map(name => `${pack}-${name}`),
            ...packInfo.bundledNames,
        ];
        keepRecord();
        step = 1;
        // Step 1e: Hooks and coding rules the pack declares. Both are no-ops for a pack
        // that ships neither, which is why `sdlc` is unaffected.
        const hooksWritten = (0, hooks_js_1.deployHooks)(packDir, projectPath);
        const stack = (0, rules_js_1.detectStack)(projectPath);
        const rulesWritten = (0, rules_js_1.deployRules)(packDir, projectPath, stack);
        // Step 1f: Keep the machine-local paths just generated out of git. A repo with a
        // recognised stack is a code repo and regenerates everything; anything else is a
        // documents repo and keeps its canonical skills in version control.
        const policy = stack.length > 0 ? packInfo.gitignore?.code : packInfo.gitignore?.spec;
        if (policy && !options.refresh)
            (0, gitignore_js_1.updateGitignore)(projectPath, policy);
        state.hooks = hooksWritten.length > 0 ? hookFileNames(packDir) : [];
        state.rules = rulesWritten.filter(path => path.endsWith('.md')).map(path => (0, path_1.basename)(path));
        keepRecord();
        step = 2;
        // Step 1g: Multi-repo wiring. The pack's skills read `.bmm-config.yaml` to find
        // their way back to the spec repo, so without this they look in the wrong place.
        //
        // The longest step by far, and the one that reaches into other repos, so the
        // record is updated from inside it rather than only once it returns.
        wired = wireWorkspace(packDir, projectPath, {
            codeRepos: options.codeRepos,
            projectName: options.projectName,
            clone: options.clone,
            adopt: options.adopt,
            refresh: options.refresh,
            codeGitignore: packInfo.gitignore?.code,
            onProgress: partial => {
                state.wired = partial.created;
                state.scopedRepos = partial.scoped;
                keepRecord();
            },
        });
        state.wired = wired.created;
        state.scopedRepos = wired.scoped;
        state.specConfig = (0, fs_1.existsSync)((0, path_1.join)(projectPath, '.bmm-config.yaml')) ? '.bmm-config.yaml' : undefined;
        keepRecord();
        step = 3;
        // Step 1h: Scaffold the pack's workflows and slash commands. Without this an
        // installed pack has no way to be invoked — only `vsaf init` used to do it, and
        // only for the default pack.
        //
        // A project that has not been initialised is left untouched: scaffolding into it
        // would leave a `.vsaf/` holding commands but no config, which reads as an
        // initialised project to every later command.
        // The marker is the directory, not a config file inside it: a project may hold
        // workflows, commands and docs under `.vsaf/` while keeping its configuration
        // elsewhere, and refusing to scaffold there would silently skip the whole step.
        //
        // Workflows and slash commands are committed too — a refresh gets them from git.
        if ((0, fs_1.existsSync)((0, path_1.join)(projectPath, '.vsaf')) && !options.refresh) {
            const scaffoldNames = packInfo.skillNames
                .filter(name => !SKIP_SKILLS.includes(name))
                .map(name => `${pack}-${name}`);
            scaffold = (0, skill_js_1.skillInit)(pack, projectPath, scaffoldNames, {
                workflows: packInfo.workflows,
                overwriteWorkflows: options.force,
            });
            // Command files for the `command:` nodes of the pack's workflows — the ones
            // `skillInit` does not write, because it only knows skills carrying the pack
            // prefix. Same gate as the scaffolding above and for the same reason: without a
            // `.vsaf/` the workflows were never written, so commands alone would have
            // nothing to serve.
            workflowCommands = (0, skill_js_1.scaffoldWorkflowCommands)(packInfo.workflows, projectPath, skillsDir, { overwrite: options.force });
        }
        else if (!options.refresh) {
            // Đúng thứ tự của hai lệnh: `init` dựng `.vsaf/`, rồi lượt cài này chạy lại mới có
            // chỗ để đặt workflow và lệnh slash. `vsaf init --pack <flow>` không còn nữa —
            // `init` không cài flow.
            console.log('[vsaf] Project not initialised — run `vsaf init` for the config, then re-run '
                + `\`vsaf install ${pack}\` for the workflows and slash commands`);
        }
        // Both routes write command files, deduplicated: with `--force`, the workflow
        // pass rewrites the very files `skillInit` has just created.
        state.commands = [...new Set([
                ...scaffold.commandsCreated, ...scaffold.commandsSkipped, ...workflowCommands.owned,
            ])].map(name => `${name}.md`);
        keepRecord();
    }
    catch (error) {
        // Whatever got as far as being written is still recorded, so it can be undone.
        keepRecord();
        reportFailure(pack, options, step, error, recorded);
        // Said once: the caller prints the bare message, and after the report above that
        // would be the same failure told twice.
        error.reported = true;
        throw error;
    }
    // Đóng dấu "lấy từ đâu" cho lượt cài engine tự làm, đúng như nhánh chạy script của
    // flow đã làm ở trên. Chỉ đóng khi đã cài xong: một lượt cài gãy giữa chừng mà mang
    // dấu này sẽ đọc ra là đã cài trọn vẹn từ mã commit đó.
    if (flowSource) {
        state.flowOrigin = flowSource.origin;
        state.flowCommit = flowSource.commit;
        keepRecord();
    }
    // The record is written wherever the project allows one. Saying so is the only
    // honest thing to do when it does not: uninstall will find nothing to remove.
    if (!recorded && (0, manifest_js_1.recordPaths)(projectPath, pack).length === 0) {
        console.log('[vsaf] ⚠ Chưa ghi được sổ cài đặt (dự án chưa có .vsaf/ lẫn cây artifact)');
        console.log('[vsaf]   → `vsaf uninstall` sẽ không dọn được. Chạy `vsaf init` rồi cài lại nếu cần gỡ về sau.');
    }
    // Step 1k: Check the install against what it just claimed to write. The failures
    // it catches are the silent ones — a hook without its execute bit never runs, a
    // cross-repo link resolving nowhere breaks only when a skill reads through it.
    //
    // Handed back rather than only printed: the command exits non-zero on them, so a
    // script that installs and carries on cannot read a broken install as a good one.
    const problems = (0, selftest_js_1.selfTest)(projectPath, state);
    if (problems.length > 0) {
        console.log(`\n[vsaf] ⚠ Tự kiểm thấy ${problems.length} vấn đề:`);
        for (const problem of problems)
            console.log(`    ${problem}`);
        console.log('[vsaf] Chạy lại lệnh này là an toàn — phần đã cài được giữ nguyên:');
        console.log(`[vsaf]     ${rerunCommand(pack, options)}`);
    }
    console.log(`\n[vsaf] Skills deployed to ${skillsDir}`);
    for (const name of deploy.deployed)
        console.log(`  ✓ ${name}`);
    for (const name of deploy.skipped)
        console.log(`  ⊘ ${name} (exists, use --force to overwrite)`);
    console.log(`  ${deploy.deployed.length} deployed, ${deploy.skipped.length} skipped\n`);
    if (scaffold.workflowsCreated.length > 0) {
        console.log(`[vsaf] Workflows deployed to .vsaf/workflows/${pack}/`);
        for (const f of scaffold.workflowsCreated)
            console.log(`  ✓ ${f}`);
        console.log('');
    }
    if (workflowCommands.created.length > 0) {
        console.log(`[vsaf] Commands deployed to .vsaf/commands/ (workflow node entry points)`);
        for (const name of workflowCommands.created)
            console.log(`  ✓ ${name}.md`);
        console.log('');
    }
    // Step 2: Install graphify (pipx + skill deployment)
    let graphify = { installed: false, skillDeployed: false };
    if (!options._skipGraphify) {
        console.log('[vsaf] Installing graphify...\n');
        graphify = installGraphify();
        if (graphify.installed) {
            console.log(`  ✓ graphify ${graphify.version ?? ''}`);
            if (graphify.skillDeployed) {
                console.log('  ✓ graphify skill deployed');
            }
            else {
                console.log('  ⚠ graphify skill deployment failed — run: graphify install --platform claude');
            }
        }
        else {
            console.log(`  ✗ graphify — ${graphify.error}`);
        }
        console.log();
    }
    // Step 3: Run install-deps.mjs (unless --skip-deps)
    let depsRan = false;
    if (!options.skipDeps) {
        const depsScript = (0, path_1.join)(packDir, 'install-deps.mjs');
        if ((0, fs_1.existsSync)(depsScript)) {
            console.log('[vsaf] Installing npm dependencies...\n');
            try {
                (0, child_process_1.execSync)(`node "${depsScript}" "${projectPath}" "${packDir}"`, { cwd: projectPath, stdio: 'inherit' });
                depsRan = true;
            }
            catch {
                console.error('[vsaf] ⚠ install-deps.mjs failed — run manually later');
            }
        }
        else {
            console.log('[vsaf] No install-deps.mjs found in pack — skipping deps\n');
        }
    }
    // Step 4: Check binaries
    console.log('[vsaf] Checking system binaries...\n');
    const binaries = checkBinaries();
    for (const bin of binaries) {
        if (bin.found) {
            console.log(`  ✓ ${bin.name} ${bin.version ?? ''}`);
        }
        else if (bin.required) {
            console.log(`  ✗ ${bin.name} — REQUIRED, install: brew install gh (macOS) / apt install gh (Linux) / winget install GitHub.cli (Windows)`);
        }
        else {
            console.log(`  ⚠ ${bin.name} — optional, not installed`);
        }
    }
    // Step 5: Print plugin guide
    console.log(PLUGIN_GUIDE);
    // Summary
    const unresolved = options.unresolved ?? [];
    const issues = binaries.filter(b => b.required && !b.found).length
        + (!options._skipGraphify && !graphify.installed ? 1 : 0)
        + unresolved.length;
    // Đếm skill, không đếm cả thư mục `_shared/<pack>`.
    //
    // `deploy.deployed` mang thêm một mục cho `_shared` — tài sản dùng chung mà skill của
    // pack đọc lúc chạy, không phải một skill. Đếm nó vào đây làm hai dòng liền nhau nói hai
    // con số cho cùng một lượt cài: "Install complete: 62 skills" ở tiến trình con, rồi
    // "61 skill trong sổ" ở tiến trình cha — sổ vốn không ghi `_shared`.
    const skillsDeployed = deploy.deployed.filter(name => name !== sharedDeployed).length;
    console.log(`\n[vsaf] Install complete: ${skillsDeployed} skills, ${issues} issue(s)`);
    // Last, where it is still on screen. Said once before the install too, a hundred
    // lines further up — which is exactly as good as not saying it.
    for (const line of unresolved)
        console.log(`[vsaf] ⚠ ${line}`);
    // Only where it means something. A pack that deploys skills and stops wires no
    // repos by design, and "0 repos wired" reads as a failure rather than as silence.
    if (shipsProjectSkeleton(packDir)) {
        console.log(`[vsaf] Số code repo đã nối dây: ${wired.scoped.length}`);
    }
    // Next-step hint depends on the pack. `sdlc`'s dedicated bootstrap command
    // (`/sdlc-init`) predates the generic workflow runner and stays the
    // documented entry point (README "SDLC Skill Pack › Setup"). Any other
    // pack — especially one advertised as standalone/no-SDLC-needed, like
    // autotest-skill — must not be told to run a command that was never
    // installed for it; point at its own workflow entry point instead.
    if (pack === 'sdlc') {
        console.log('[vsaf] Next: open Claude in your project → /sdlc-init\n');
    }
    else if (Object.keys(packInfo.workflows).length > 0) {
        const [firstWorkflowFile] = Object.keys(packInfo.workflows);
        const workflowName = firstWorkflowFile.replace(/\.ya?ml$/, '');
        console.log(`[vsaf] Next: open Claude in your project → /vsaf ${pack}/${workflowName}\n`);
    }
    else {
        console.log('[vsaf] Next: open Claude in your project and try one of the deployed skills above.\n');
    }
    // Step 6: Push the skills to the other tools, only if the pack asked and the user
    // agreed. Silence here means the user's personal configuration stays untouched.
    let globalSynced = [];
    if (packInfo.global && options.syncGlobal) {
        globalSynced = (0, global_sync_js_1.syncToGlobal)({
            home: (0, os_1.homedir)(),
            canonicalDir: skillsDir,
            rulesDir: (0, path_1.join)(projectPath, '.claude', 'rules'),
            declaration: { pack, ...packInfo.global },
            approved: true,
        });
        console.log(`[vsaf] Synced ${globalSynced.length} path(s) outside the project`);
    }
    else if (packInfo.global) {
        console.log('[vsaf] Pack can also sync skills to your other tools — re-run with --sync-global');
    }
    return { deploy, binaries, depsRan, graphify, scaffold, globalSynced, wired: wired.created, problems, flowDir: packDir };
}
//# sourceMappingURL=install.js.map