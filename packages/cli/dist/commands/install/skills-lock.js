"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LOCK_FILE = void 0;
exports.computeSkillHash = computeSkillHash;
exports.verifySkillsLock = verifySkillsLock;
exports.assertSkillsLock = assertSkillsLock;
const fs_1 = require("fs");
const crypto_1 = require("crypto");
const path_1 = require("path");
/** Pins the exact content of skills that come from outside this repo. */
exports.LOCK_FILE = 'skills-lock.json';
function computeSkillHash(filePath) {
    return (0, crypto_1.createHash)('sha256').update((0, fs_1.readFileSync)(filePath)).digest('hex');
}
/**
 * Check every third-party skill against the hash the project pinned.
 *
 * A project with no lock file pins nothing and passes. A lock file that cannot be
 * parsed throws instead of passing: treating it as "no lock" would silently turn a
 * damaged pin into an unpinned install, which is the exact thing pinning prevents.
 *
 * Verification is purely local — nothing is fetched, so no network means no hang.
 */
function verifySkillsLock(projectPath) {
    const lockPath = (0, path_1.join)(projectPath, exports.LOCK_FILE);
    if (!(0, fs_1.existsSync)(lockPath))
        return [];
    let lock;
    try {
        lock = JSON.parse((0, fs_1.readFileSync)(lockPath, 'utf-8'));
    }
    catch (error) {
        throw new Error(`Cannot read ${exports.LOCK_FILE}: ${error.message}`);
    }
    const violations = [];
    for (const [skill, entry] of Object.entries(lock.skills ?? {})) {
        const target = (0, path_1.resolve)(projectPath, entry.skillPath);
        const inside = (0, path_1.relative)(projectPath, target);
        if (inside.startsWith('..') || (0, path_1.isAbsolute)(inside)) {
            throw new Error(`Locked skill "${skill}" points outside the project: ${entry.skillPath}`);
        }
        if (!(0, fs_1.existsSync)(target)) {
            violations.push({ skill, reason: 'missing', path: entry.skillPath });
            continue;
        }
        const actual = computeSkillHash(target);
        if (actual !== entry.computedHash) {
            violations.push({
                skill, reason: 'hash-mismatch', path: entry.skillPath,
                expected: entry.computedHash, actual,
            });
        }
    }
    return violations;
}
function describe(violation) {
    if (violation.reason === 'missing') {
        return `  ${violation.skill}: not on disk at ${violation.path} — fetch it, then re-run`;
    }
    return `  ${violation.skill}: content changed at ${violation.path}\n`
        + `    pinned:  ${violation.expected}\n`
        + `    on disk: ${violation.actual}`;
}
/** Stop the install rather than deploy a third-party skill nobody vouched for. */
function assertSkillsLock(projectPath) {
    const violations = verifySkillsLock(projectPath);
    if (violations.length === 0)
        return;
    throw new Error(`${exports.LOCK_FILE} verification failed:\n${violations.map(describe).join('\n')}\n`
        + 'Review the change, then update the pinned hash on purpose.');
}
//# sourceMappingURL=skills-lock.js.map