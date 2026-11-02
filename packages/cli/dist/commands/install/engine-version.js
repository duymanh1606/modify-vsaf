"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveEngineVersion = resolveEngineVersion;
const fs_1 = require("fs");
const path_1 = require("path");
/**
 * Real package version, read from the root package.json at runtime.
 *
 * Walks up from this file (dist/commands/install → … → package root) and picks the
 * first package.json whose name is the published root (`…/vsaf`), skipping the
 * workspace's own `@vsaf/cli`. Reading it at runtime keeps `vsaf --version` truthful
 * after a release bump — the previous hardcoded '0.1.0' reported the (never-bumped)
 * workspace version instead.
 *
 * Lives here rather than in `index.ts` because the install path needs it too: the
 * `requiresEngine` gate compares a flow's demand against this number, and a version it
 * cannot read means the gate never refuses anything. Left unexported in `index.ts` it
 * was unreachable from there, so the gate would have passed every flow in silence.
 */
function resolveEngineVersion() {
    let dir = __dirname;
    // Eight rather than the six this walk needs from its deepest known home
    // (`dist/commands/install`). Six was exactly enough, which means one more directory
    // between this file and the package root would return 'unknown' — and 'unknown'
    // does not fail loudly, it turns the engine gate off without a word.
    for (let i = 0; i < 8; i++) {
        try {
            const pkg = JSON.parse((0, fs_1.readFileSync)((0, path_1.join)(dir, 'package.json'), 'utf8'));
            if (typeof pkg.name === 'string' && pkg.name.endsWith('/vsaf') && pkg.version) {
                return pkg.version;
            }
        }
        catch {
            // no package.json here (or unreadable) — keep walking up
        }
        const parent = (0, path_1.dirname)(dir);
        if (parent === dir)
            break;
        dir = parent;
    }
    return 'unknown';
}
//# sourceMappingURL=engine-version.js.map