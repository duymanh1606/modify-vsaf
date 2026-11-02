"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.writeWorkspaceFile = writeWorkspaceFile;
const path_1 = require("path");
const fs_1 = require("fs");
const backup_js_1 = require("./backup.js");
/** Editor settings that travel with the multi-root workspace. */
const SETTINGS = {
    'files.exclude': {
        '**/node_modules': true,
        '**/NTAPP-output/archive': true,
        '**/.git': false,
        '**/.DS_Store': true,
    },
    'search.exclude': {
        '**/node_modules': true,
        '**/NTAPP-output/archive': true,
        '**/dist': true,
        '**/build': true,
    },
};
/**
 * Write the multi-root workspace file beside the spec repo.
 *
 * Paths are relative so the file survives the workspace being moved or cloned
 * somewhere else. Built and serialised as data rather than by filling a text
 * template, so the result cannot come out as invalid JSON.
 *
 * Written even when no code repo is named yet. That case used to be skipped as "one
 * repo needs no multi-root file", but it is the case that needs the file most: a
 * project is set up before its code repos arrive, and the person who installed it
 * then had nothing to open — and no obvious way to get one, short of installing
 * again with the right flag.
 *
 * Returns the file written.
 */
function writeWorkspaceFile(specRepo, projectName, codeRepos) {
    const folders = [
        { name: 'spec-repo', path: '.' },
        ...codeRepos.map(repo => ({
            name: (0, path_1.basename)(repo),
            // Forward slashes in the output regardless of host platform: the editor reads
            // this file on whatever machine opens the workspace.
            path: (0, path_1.relative)(specRepo, repo).split('\\').join('/'),
        })),
    ];
    const path = (0, path_1.join)(specRepo, `${projectName}.code-workspace`);
    const content = `${JSON.stringify({ folders, settings: SETTINGS }, null, 2)}\n`;
    (0, backup_js_1.backupIfModified)(path, content);
    (0, fs_1.writeFileSync)(path, content, 'utf-8');
    return path;
}
//# sourceMappingURL=workspace-file.js.map