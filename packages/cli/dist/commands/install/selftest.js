"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.selfTest = selfTest;
const js_yaml_1 = require("js-yaml");
const fs_1 = require("fs");
const path_1 = require("path");
/**
 * Check that what the install claims to have written is really usable.
 *
 * Every check is against the install record, so it verifies the promise actually
 * made rather than a fixed expectation. Catching this here matters because the
 * failures are all silent ones: a hook missing its execute bit never runs, a link
 * resolving nowhere fails only when a skill reads through it, and a missing
 * workflow directory shows up as "no workflows" long after installing.
 *
 * Returns one line per problem found; empty means the install is sound.
 */
function selfTest(projectPath, record) {
    const problems = [];
    for (const skill of record.skills) {
        const dir = (0, path_1.join)(projectPath, record.canonicalDir, skill);
        if (!(0, fs_1.existsSync)((0, path_1.join)(dir, 'SKILL.md'))) {
            problems.push(`skill ${skill}: no SKILL.md at ${record.canonicalDir}/${skill}`);
        }
    }
    for (const hook of record.hooks) {
        const path = (0, path_1.join)(projectPath, '.claude', 'hooks', hook);
        if (!(0, fs_1.existsSync)(path)) {
            problems.push(`hook ${hook}: not installed`);
            continue;
        }
        // Only scripts need the bit; a README in the same directory does not.
        if (!/\.(sh|py)$/.test(hook))
            continue;
        if (((0, fs_1.statSync)(path).mode & 0o111) === 0) {
            problems.push(`hook ${hook}: not executable, so it will never run`);
        }
    }
    if (record.hooks.length > 0) {
        const settings = (0, path_1.join)(projectPath, '.claude', 'settings.json');
        if (!(0, fs_1.existsSync)(settings)) {
            problems.push('settings.json: missing, so no hook is wired to any event');
        }
        else {
            try {
                JSON.parse((0, fs_1.readFileSync)(settings, 'utf-8'));
            }
            catch (error) {
                problems.push(`settings.json: cannot be parsed — ${error.message}`);
            }
        }
    }
    // `hasWorkflows` records what the pack ships, not what this run wrote — uninstall
    // needs it that way. Scaffolding is skipped outright on a project with no `.vsaf/`,
    // and the install says so on screen, so checking for the directory there flags a
    // promise that was never made and fails an install that went exactly to plan.
    if (record.hasWorkflows && (0, fs_1.existsSync)((0, path_1.join)(projectPath, '.vsaf'))) {
        const dir = (0, path_1.join)(projectPath, '.vsaf', 'workflows', record.pack);
        const count = (0, fs_1.existsSync)(dir) ? (0, fs_1.readdirSync)(dir).filter(f => f.endsWith('.yaml')).length : 0;
        if (count === 0) {
            problems.push(`workflow directory .vsaf/workflows/${record.pack}: empty or missing`);
        }
    }
    for (const command of record.commands) {
        if (!(0, fs_1.existsSync)((0, path_1.join)(projectPath, '.vsaf', 'commands', command))) {
            problems.push(`slash command ${command}: missing`);
        }
    }
    // The check that matters most for a spec repo: the config 28 of the pack's skills
    // read. A missing or unparsable one leaves every skill resolving paths to nowhere,
    // and nothing else in this list would have noticed.
    if (record.specConfig) {
        const path = (0, path_1.join)(projectPath, record.specConfig);
        if (!(0, fs_1.existsSync)(path)) {
            problems.push(`${record.specConfig}: missing, so skills cannot resolve their paths`);
        }
        else {
            try {
                const config = (0, js_yaml_1.load)((0, fs_1.readFileSync)(path, 'utf-8'));
                const bmad = (config?.bmad ?? {});
                for (const key of ['spec_repo_root', 'code_repo_root', 'design_system_root']) {
                    if (!bmad[key])
                        problems.push(`${record.specConfig}: missing bmad.${key}`);
                }
                if (!config?.project_name)
                    problems.push(`${record.specConfig}: missing project_name`);
            }
            catch (error) {
                problems.push(`${record.specConfig}: not valid YAML — ${error.message}`);
            }
        }
    }
    for (const entry of record.wired ?? []) {
        const path = (0, path_1.resolve)(projectPath, entry);
        const stat = (0, fs_1.lstatSync)(path, { throwIfNoEntry: false });
        if (!stat) {
            problems.push(`wired path ${entry}: missing`);
        }
        else if (stat.isSymbolicLink() && !(0, fs_1.existsSync)(path)) {
            problems.push(`wired path ${entry}: link resolves to nothing`);
        }
    }
    return problems;
}
//# sourceMappingURL=selftest.js.map