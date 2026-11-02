"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.scaffoldSdlcDocs = scaffoldSdlcDocs;
const fs_1 = require("fs");
const path_1 = require("path");
/**
 * The artifact tree every `sdlc-*` phase reads and writes. Creating it here means
 * a fresh project can run a phase straight away instead of failing on a missing
 * tracker and asking the user to scaffold it by hand first.
 */
const DOC_DIRS = ['features', 'hotfixes', 'onboarding'];
const STATUS_MD = `# SDLC Status Tracker

## Active Features

| Feature | Phase | Status | Last Updated |
|---------|-------|--------|-------------|

## Active Hotfixes

| Bug ID | Phase | Status | Last Updated |
|--------|-------|--------|-------------|

## Completed Features

## Completed Hotfixes
`;
const KNOWLEDGE_MD = `# Domain Knowledge

Accumulated knowledge from all phases.
`;
const CONTEXT_MD = `# Project Context

## Project Overview
{Brief project description — fill after onboarding}

## Tech Stack
{Will be updated by onboard-code}

## Shared Language

| Term | Definition | Example |
|------|-----------|---------|
| {term} | {1-line definition} | {concrete example} |

## Architecture Decisions
{Will be updated by sdlc-architecture}
`;
/** Index directories, rebuilt from source and never worth committing. */
const IGNORED = ['graphify-out/', '.gitnexus/'];
/** Write a template only where there is nothing yet — a filled-in doc always wins. */
function writeIfAbsent(path, content, created) {
    if ((0, fs_1.existsSync)(path))
        return;
    (0, fs_1.writeFileSync)(path, content, 'utf-8');
    created.push(path);
}
/**
 * Add entries the index tools generate, leaving every existing line in place:
 * a `.gitignore` is the user's file, and dropping a rule from it could publish
 * something they meant to keep out of the repo.
 */
function addIgnoreEntries(projectPath, created) {
    const path = (0, path_1.join)(projectPath, '.gitignore');
    const current = (0, fs_1.existsSync)(path) ? (0, fs_1.readFileSync)(path, 'utf-8') : '';
    const lines = new Set(current.split('\n').map(line => line.trim()));
    const missing = IGNORED.filter(entry => !lines.has(entry));
    if (missing.length === 0)
        return;
    const prefix = current.length === 0 || current.endsWith('\n') ? '' : '\n';
    (0, fs_1.appendFileSync)(path, `${prefix}${missing.join('\n')}\n`, 'utf-8');
    created.push(path);
}
/**
 * Scaffold the SDLC artifact tree: `.vsaf/docs/` with its trackers, a root
 * `CONTEXT.md`, and the index entries in `.gitignore`.
 *
 * Idempotent by design — re-running only fills gaps, so it is safe on a project
 * that has been carrying these documents for months.
 *
 * Returns the paths created or extended.
 */
function scaffoldSdlcDocs(projectPath) {
    const created = [];
    const docs = (0, path_1.join)(projectPath, '.vsaf', 'docs');
    for (const dir of DOC_DIRS) {
        (0, fs_1.mkdirSync)((0, path_1.join)(docs, dir), { recursive: true });
    }
    writeIfAbsent((0, path_1.join)(docs, 'STATUS.md'), STATUS_MD, created);
    writeIfAbsent((0, path_1.join)(docs, 'KNOWLEDGE.md'), KNOWLEDGE_MD, created);
    writeIfAbsent((0, path_1.join)(projectPath, 'CONTEXT.md'), CONTEXT_MD, created);
    addIgnoreEntries(projectPath, created);
    return created;
}
//# sourceMappingURL=sdlc-docs.js.map