"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.detectStack = detectStack;
exports.removeRulesImport = removeRulesImport;
exports.deployRules = deployRules;
const fs_1 = require("fs");
const path_1 = require("path");
const backup_js_1 = require("./backup.js");
/** Which rule file a pack wants applied to which kind of repo. */
const MAPPING_FILE = 'rules.json';
const BLOCK_BEGIN = '<!-- >>> vsaf coding rules import (auto-managed, do not edit) >>>';
const BLOCK_END = '<!-- <<< vsaf coding rules import <<< -->';
const FE_DEPS = /"(react|next|vue|svelte|@angular\/core|nuxt|remix|astro|solid-js|preact|qwik)"/;
const BE_DEPS = /"(express|fastify|@nestjs\/core|koa|hapi|hono|@hapi\/hapi|restify)"/;
const BE_MANIFESTS = [
    'pom.xml', 'build.gradle', 'build.gradle.kts',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'requirements.txt',
];
/**
 * Work out what kind of code a repo holds, from its dependency manifests.
 *
 * An empty result is a normal answer, not a failure: a docs-only repo gets no
 * coding rules, which keeps its sessions free of irrelevant context.
 */
function detectStack(projectPath) {
    const stack = [];
    const packageJson = (0, path_1.join)(projectPath, 'package.json');
    if ((0, fs_1.existsSync)(packageJson)) {
        let manifest = '';
        try {
            manifest = (0, fs_1.readFileSync)(packageJson, 'utf-8');
        }
        catch {
            manifest = ''; // unreadable manifest tells us nothing; fall through to the file probes
        }
        if (FE_DEPS.test(manifest))
            stack.push('fe');
        if (BE_DEPS.test(manifest))
            stack.push('be');
    }
    if (!stack.includes('be') && BE_MANIFESTS.some(m => (0, fs_1.existsSync)((0, path_1.join)(projectPath, m)))) {
        stack.push('be');
    }
    return stack;
}
function readMapping(rulesDir) {
    const path = (0, path_1.join)(rulesDir, MAPPING_FILE);
    if (!(0, fs_1.existsSync)(path))
        return {};
    try {
        return JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch (error) {
        throw new Error(`Invalid rule mapping in ${path}: ${error.message}`);
    }
}
/** The managed block is rewritten wholesale, so a stack change cannot leave stale imports. */
function renderBlock(files) {
    const imports = files.map(f => `@rules/${f}`).join('\n');
    return [
        BLOCK_BEGIN,
        '## Coding rules',
        '',
        'Rule chi tiết theo stack của repo, do pack cài vào `rules/`.',
        '',
        imports,
        BLOCK_END,
    ].join('\n');
}
/** Replace an existing managed block, or append one, leaving the user's prose alone. */
function upsertBlock(current, block) {
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    if (start !== -1 && end > start) {
        return current.slice(0, start) + block + current.slice(end + BLOCK_END.length);
    }
    const base = current.length === 0 || current.endsWith('\n') ? current : `${current}\n`;
    return `${base}${base.length > 0 ? '\n' : ''}${block}\n`;
}
/**
 * Pull the managed import block back out of `CLAUDE.md`, leaving the prose the
 * user wrote around it. Returns the file path, or null when there was no block.
 */
function removeRulesImport(projectPath) {
    const claudeMd = (0, path_1.join)(projectPath, 'CLAUDE.md');
    if (!(0, fs_1.existsSync)(claudeMd))
        return null;
    const current = (0, fs_1.readFileSync)(claudeMd, 'utf-8');
    const start = current.indexOf(BLOCK_BEGIN);
    const end = current.indexOf(BLOCK_END);
    if (start === -1 || end <= start)
        return null;
    const next = (current.slice(0, start) + current.slice(end + BLOCK_END.length)).replace(/\n{3,}$/, '\n');
    (0, fs_1.writeFileSync)(claudeMd, next, 'utf-8');
    return claudeMd;
}
/**
 * Install the pack's rule files for the stacks a repo actually uses, and point
 * `CLAUDE.md` at them through a marker block that a reinstall rewrites in place.
 *
 * Returns every path written, all of them inside the project.
 */
function deployRules(packDir, projectPath, stack) {
    const source = (0, path_1.join)(packDir, 'rules');
    if (!(0, fs_1.existsSync)(source) || stack.length === 0)
        return [];
    const mapping = readMapping(source);
    const files = stack
        .map(kind => mapping[kind])
        .filter((f) => !!f && (0, fs_1.existsSync)((0, path_1.join)(source, f)));
    if (files.length === 0)
        return [];
    const written = [];
    // At the repo root, not under `.claude/`: these are the team's coding rules, meant
    // to be read and committed like any other document in the repo.
    const targetDir = (0, path_1.join)(projectPath, 'rules');
    (0, fs_1.mkdirSync)(targetDir, { recursive: true });
    for (const file of files) {
        const target = (0, path_1.join)(targetDir, file);
        (0, fs_1.copyFileSync)((0, path_1.join)(source, file), target);
        written.push(target);
    }
    const claudeMd = (0, path_1.join)(projectPath, 'CLAUDE.md');
    const current = (0, fs_1.existsSync)(claudeMd) ? (0, fs_1.readFileSync)(claudeMd, 'utf-8') : '';
    const next = upsertBlock(current, renderBlock(files));
    (0, backup_js_1.backupIfModified)(claudeMd, next);
    (0, fs_1.writeFileSync)(claudeMd, next, 'utf-8');
    written.push(claudeMd);
    return written;
}
//# sourceMappingURL=rules.js.map