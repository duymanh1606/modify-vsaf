"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.REGISTRY_FILE = exports.DS_FAMILY = void 0;
exports.designSystemId = designSystemId;
exports.planDesignSystems = planDesignSystems;
exports.resolveDesignSystems = resolveDesignSystems;
const fs_1 = require("fs");
const path_1 = require("path");
const js_yaml_1 = require("js-yaml");
const repos_config_js_1 = require("./repos-config.js");
const rules_js_1 = require("./rules.js");
/** Where every design system of a project lives, relative to the spec repo. */
exports.DS_FAMILY = (0, path_1.join)('NTAPP-output', 'design-system');
/** The file listing each design system and which repo owns it. */
exports.REGISTRY_FILE = 'registry.yaml';
/** A flat design system predates the registry, so this file marks the legacy layout. */
const LEGACY_MARKER = 'master_token.json';
/** Directory-safe id derived from the repo name, matching what the skills expect. */
function designSystemId(repoName) {
    return repoName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
}
/** A repo that ships a front end owns a design system; a service repo consumes none. */
function isFrontend(repoPath) {
    return (0, rules_js_1.detectStack)(repoPath).includes('fe');
}
/** Honour an existing registry: a person may have renamed roots or merged two repos. */
function readRegistry(path) {
    const byRepo = new Map();
    let parsed;
    try {
        parsed = (0, js_yaml_1.load)((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        return byRepo; // an unreadable registry is the user's to fix; fall back to defaults
    }
    const systems = parsed?.systems ?? {};
    for (const entry of Object.values(systems)) {
        const owners = Array.isArray(entry?.code_repo) ? entry.code_repo : [entry?.code_repo];
        for (const owner of owners) {
            if (typeof owner === 'string' && owner.length > 0 && entry?.root) {
                byRepo.set(owner, entry.root.replace(/\/$/, ''));
            }
        }
    }
    return byRepo;
}
function renderRegistry(repos) {
    const lines = [
        '# DS Registry — written by vsaf install (project has more than one front-end repo).',
        '# Schema + semantics: _shared/ds-registry-schema.md. Resolve: _shared/ds-resolution.md.',
        '# Add id_prefixes/modules so skills can resolve a unit to its design system without asking.',
        'version: 1',
        '',
        'systems:',
    ];
    for (const repoPath of repos) {
        const name = (0, path_1.basename)(repoPath);
        const id = designSystemId(name);
        lines.push(`  ${id}:`);
        lines.push(`    root: "${id}/"`);
        lines.push(`    code_repo: ${name}`);
        lines.push(`    framework: ${(0, repos_config_js_1.detectRepoStack)(repoPath).framework}`);
    }
    return `${lines.join('\n')}\n`;
}
/**
 * Describe what `resolveDesignSystems` would do, without writing anything.
 *
 * Returns null when there is nothing to say — one front end needs no registry.
 */
function planDesignSystems(specRepo, codeRepos) {
    const frontends = codeRepos.filter(isFrontend).map(path => (0, path_1.basename)(path));
    if (frontends.length < 2)
        return null;
    const registry = `${exports.DS_FAMILY}/${exports.REGISTRY_FILE}`;
    if ((0, fs_1.existsSync)((0, path_1.join)(specRepo, exports.DS_FAMILY, exports.REGISTRY_FILE))) {
        return `${registry} → already there, design system roots read from it`;
    }
    if ((0, fs_1.existsSync)((0, path_1.join)(specRepo, exports.DS_FAMILY, LEGACY_MARKER))) {
        return `${registry} → not written: a flat design system is already there and its owner is unrecorded`;
    }
    return `${registry} → one design system per front end: ${frontends.map(designSystemId).join(', ')}`;
}
/**
 * Decide which design system each code repo uses, and write the registry when a
 * project needs more than one.
 *
 * One front end needs no registry: its design system is the family root, and a
 * registry would only add a file to keep in sync. Two or more each get their own
 * namespaced root, because a single shared root would let one repo's tokens
 * silently overwrite another's.
 *
 * The one case left to a person is a project that already has a flat design system
 * and has since grown a second front end: nothing in the files says which repo the
 * existing tokens belong to, so guessing could attach them to the wrong repo.
 */
function resolveDesignSystems(specRepo, codeRepos) {
    const frontends = codeRepos.filter(isFrontend);
    const roots = new Map();
    if (frontends.length < 2)
        return { roots };
    const familyRoot = (0, path_1.join)(specRepo, exports.DS_FAMILY);
    const registryPath = (0, path_1.join)(familyRoot, exports.REGISTRY_FILE);
    if ((0, fs_1.existsSync)(registryPath)) {
        const declared = readRegistry(registryPath);
        for (const repoPath of frontends) {
            const root = declared.get((0, path_1.basename)(repoPath)) ?? designSystemId((0, path_1.basename)(repoPath));
            if (root !== '.')
                roots.set(repoPath, root);
        }
        return { registry: registryPath, roots };
    }
    if ((0, fs_1.existsSync)((0, path_1.join)(familyRoot, LEGACY_MARKER))) {
        return {
            roots,
            warning: `${frontends.length} front-end repos share one flat design system at ${exports.DS_FAMILY}. ` +
                'Which repo owns it is not recorded, so every repo keeps pointing at that root. ' +
                'Run the design-system bootstrap skill from the newer front-end repo to split them.',
        };
    }
    (0, fs_1.mkdirSync)(familyRoot, { recursive: true });
    (0, fs_1.writeFileSync)(registryPath, renderRegistry(frontends), 'utf-8');
    for (const repoPath of frontends) {
        roots.set(repoPath, designSystemId((0, path_1.basename)(repoPath)));
    }
    return { registry: registryPath, roots };
}
//# sourceMappingURL=ds-registry.js.map