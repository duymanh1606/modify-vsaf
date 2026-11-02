"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.planInstall = planInstall;
const fs_1 = require("fs");
const path_1 = require("path");
const rules_js_1 = require("./rules.js");
const repo_scope_js_1 = require("./repo-scope.js");
const ds_registry_js_1 = require("./ds-registry.js");
const ide_mirror_js_1 = require("./ide-mirror.js");
const workspace_js_1 = require("./workspace.js");
const spec_scaffold_js_1 = require("./spec-scaffold.js");
/** `create` or `keep`, so the reader can tell a first install from a repeat. */
function verdict(path, force = false) {
    if (!(0, fs_1.existsSync)(path))
        return 'create';
    return force ? 'overwrite' : 'keep as is';
}
function planSkills(packName, projectPath, info, force) {
    const target = (0, ide_mirror_js_1.resolveSkillTarget)(projectPath, info.canonicalSkillsDir).target;
    const names = [
        ...info.skillNames.filter(name => name !== 'setup').map(name => `${packName}-${name}`),
        ...info.bundledNames,
    ];
    const present = names.filter(name => (0, fs_1.existsSync)((0, path_1.join)(target, name, 'SKILL.md')));
    return [
        `skills → ${(0, path_1.relative)(projectPath, target) || '.'}`,
        `    ${names.length} total · ${names.length - present.length} to add · ${present.length} already there`
            + `${present.length > 0 && !force ? ' (kept — use --force to overwrite)' : ''}`,
    ];
}
/**
 * Describe what an install would do, without touching anything.
 *
 * Every line is derived from the same detection the install itself uses — the stack,
 * the repo scope, the workspace layout — so the two cannot disagree about those. What
 * it cannot promise is the exact file count of a copy, so it reports intent rather
 * than inventing numbers.
 */
/**
 * The plan for a pack that wires projects with its own script.
 *
 * Short on purpose. Only the steps on this side are described; the wiring itself is
 * the script's, and it has a `--dry-run` of its own that prints a far better account
 * of what it would do than a second-hand summary here could. Describing it from
 * outside is how a plan drifts from the thing it claims to describe.
 */
function planDelegated(packName, projectPath, info, options) {
    const lines = [];
    const rewiring = Boolean(options.refresh) || Boolean(options.upgrade);
    const wiring = info.wiring?.script ?? 'scripts/bootstrap.sh';
    lines.push(`project: ${projectPath}`);
    lines.push(rewiring
        ? `mode: ${options.refresh ? 'refresh' : 'upgrade'} — project đã bố trí rồi, chỉ nối dây lại`
        : 'mode: full');
    lines.push('');
    if (!rewiring) {
        const kept = info.skillsKeepInProject ?? [];
        lines.push(`1  copy pack → project (trừ ${info.skillsRoot ?? 'thư viện skill'}`
            + `${kept.length > 0 ? `, giữ ${kept.join(', ')}` : ''}; trừ pack.yaml)`);
        lines.push('2  git init + commit đầu');
        const named = [...(options.codeRepos ?? []), ...(options.clone ?? []), ...(options.adopt ?? [])];
        if (named.length === 0) {
            lines.push('3  code repo: không nêu repo nào');
        }
        else {
            lines.push('3  code repo:');
            for (const repo of options.codeRepos ?? []) {
                const path = (0, path_1.join)(projectPath, repo);
                const scope = (0, fs_1.existsSync)(path) ? (0, repo_scope_js_1.detectRepoScope)(path) : null;
                lines.push(`     ${(0, path_1.basename)(repo)}${scope ? ` — ${scope.scope}` : ' — chưa có trên đĩa'}`);
            }
            for (const url of options.clone ?? [])
                lines.push(`     clone ${url}`);
            for (const path of options.adopt ?? [])
                lines.push(`     copy vào ${(0, path_1.basename)(path)}`);
        }
    }
    lines.push(`${rewiring ? '1' : '4'}  nối dây: bash ${wiring} --dry-run`);
    lines.push('     ↑ script của pack tự in kế hoạch của nó — không tóm tắt hộ ở đây');
    lines.push('');
    lines.push('rồi gõ riêng:  vsaf init   (telemetry + SessionStart + .mcp.json)');
    lines.push('');
    lines.push(`thư viện skill: để ở máy, không vào project — \`vsaf sync ${packName}\``);
    return lines;
}
function planInstall(packDir, packName, projectPath, info, options = {}) {
    // A pack that hands the wiring to its own script gets a plan of what happens on this
    // side, and a pointer at the script's own dry run for the rest.
    if (info.wiring)
        return planDelegated(packName, projectPath, info, options);
    const lines = [];
    const force = Boolean(options.force);
    const refresh = Boolean(options.refresh);
    lines.push(`project: ${projectPath}`);
    if (refresh) {
        lines.push('mode: refresh — only machine-local files, committed ones left as they came from git');
    }
    lines.push('');
    lines.push(...planSkills(packName, projectPath, info, force));
    const canonical = (0, ide_mirror_js_1.resolveSkillTarget)(projectPath, info.canonicalSkillsDir);
    if (canonical.mirror) {
        lines.push('copies for IDEs → .claude/skills, .cursor/skills');
    }
    if ((0, fs_1.existsSync)((0, path_1.join)(packDir, 'hooks'))) {
        const files = (0, fs_1.readdirSync)((0, path_1.join)(packDir, 'hooks')).filter(name => name !== 'settings.json');
        lines.push(`hooks → ${refresh ? '.claude/hooks' : 'hooks/ and .claude/hooks'} (${files.length} entries)`);
        lines.push('    events wired into .claude/settings.json, merged by command so a repeat adds nothing');
    }
    const stack = (0, rules_js_1.detectStack)(projectPath);
    if ((0, fs_1.existsSync)((0, path_1.join)(packDir, 'rules'))) {
        lines.push(stack.length === 0
            ? 'rules → none (no build manifest here, so no coding rules apply)'
            : `rules → rules/ for ${stack.join(' + ')}${refresh ? ' — skipped on refresh' : ''}`);
    }
    const policy = stack.length > 0 ? info.gitignore?.code : info.gitignore?.spec;
    if (policy) {
        lines.push(refresh
            ? '.gitignore → left alone (committed)'
            : `.gitignore → managed block with ${policy.length} entries`);
    }
    if ((0, fs_1.existsSync)((0, path_1.join)(packDir, 'config', 'bmm-config.template.yaml'))) {
        lines.push('');
        if (refresh) {
            lines.push('project skeleton → left alone (committed)');
        }
        else {
            for (const [label, path] of [
                ['CLAUDE.md', (0, path_1.join)(projectPath, 'CLAUDE.md')],
                ['README.md', (0, path_1.join)(projectPath, 'README.md')],
                ['.bmm-config.yaml', (0, path_1.join)(projectPath, '.bmm-config.yaml')],
                ['_bmad/', (0, path_1.join)(projectPath, '_bmad')],
                ['scripts/', (0, path_1.join)(projectPath, 'scripts')],
                ['docs/Process/', (0, path_1.join)(projectPath, 'docs', 'Process')],
            ]) {
                lines.push(`${label.padEnd(18)} ${verdict(path)}`);
            }
            const missing = spec_scaffold_js_1.ARTIFACT_DIRS.filter(dir => !(0, fs_1.existsSync)((0, path_1.join)(projectPath, workspace_js_1.SPEC_REPO_MARKER, dir)));
            lines.push(`${`${workspace_js_1.SPEC_REPO_MARKER}/`.padEnd(18)} ${missing.length === 0 ? 'keep as is' : `create ${missing.length} of ${spec_scaffold_js_1.ARTIFACT_DIRS.length} stage directories`}`);
        }
        // Resolved as the install will see it: the skeleton is created first, so the
        // marker this looks for is there by the time the layout is read.
        const workspace = (0, workspace_js_1.resolveWorkspace)(projectPath, options.codeRepos, { assumeSpecRepo: !refresh });
        lines.push('');
        if (workspace.codeRepos.length > 0) {
            lines.push('code repos to wire:');
            for (const repo of workspace.codeRepos) {
                const scope = (0, repo_scope_js_1.detectRepoScope)(repo);
                lines.push(`    ${(0, path_1.basename)(repo)} — ${scope.scope} (${scope.signal})`);
                lines.push(`        .bmm-config.yaml → spec_repo_root: ${(0, path_1.relative)(repo, projectPath)}`);
                lines.push('        .agent/skills → relative link to this project');
                lines.push(`        pre-commit hook${(0, fs_1.existsSync)((0, path_1.join)(repo, '.git')) ? '' : ' — skipped, not a git repo'}`);
                // Wired per repo because the gates fire in whichever repo the agent has open.
                lines.push('        .claude/hooks → link to this project\'s hooks, events merged into its settings.json');
                if (!refresh) {
                    lines.push('        repo_type block in its CLAUDE.md');
                    const stack = (0, rules_js_1.detectStack)(repo);
                    lines.push(stack.length > 0
                        ? `        coding rules for ${stack.join(' + ')} → rules/ + import in its CLAUDE.md`
                        : '        coding rules → none, no stack detected');
                    lines.push('        .gitignore block for the generated files');
                }
            }
            const designSystems = (0, ds_registry_js_1.planDesignSystems)(projectPath, workspace.codeRepos);
            if (designSystems)
                lines.push(`    ${designSystems}`);
            if (!refresh)
                lines.push(`    ${resolveProjectNameLabel(projectPath, options.projectName)}.code-workspace`);
        }
        else if (workspace.candidates.length > 0) {
            lines.push('code repos: none named — these were found nearby:');
            for (const candidate of workspace.candidates) {
                lines.push(`    ${(0, workspace_js_1.candidateName)(projectPath, candidate)}`);
            }
        }
    }
    lines.push('');
    const workflows = Object.keys(info.workflows).length;
    if (refresh) {
        lines.push('workflows and slash commands → left alone (committed)');
    }
    else if (!(0, fs_1.existsSync)((0, path_1.join)(projectPath, '.vsaf'))) {
        lines.push('workflows and slash commands → skipped, project not initialised (run vsaf init)');
    }
    else {
        const commands = info.skillNames.filter(name => name !== 'setup').length;
        lines.push(`.vsaf/workflows/${packName}/ → ${workflows} files`);
        lines.push(`.vsaf/commands/ → up to ${commands} slash commands (existing ones kept)`);
    }
    lines.push(options.syncGlobal && info.global
        ? `outside the project → ${info.global.skillTargets.join(', ')} under your home`
        : 'outside the project → nothing');
    return lines;
}
function resolveProjectNameLabel(projectPath, given) {
    return given ?? (0, path_1.basename)(projectPath).replace(/-(doc|spec)$/, '');
}
//# sourceMappingURL=plan.js.map