"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SESSION_HOOK_COMMAND = void 0;
exports.ensureSessionHook = ensureSessionHook;
const fs_1 = require("fs");
const path_1 = require("path");
/**
 * Hook `SessionStart` của vsaf: ghi session id của Claude Code ra `.vsaf/.claude-session`.
 *
 * That id is the join key for telemetry — the vsaf trace carries it as the `session.id`
 * span attribute, which is what groups a vsaf run and the gateway's own traces into one
 * session. Without the hook the file is never written, every run reports no session, and
 * nothing anywhere errors.
 */
exports.SESSION_HOOK_COMMAND = `node -e "let d='';process.stdin.on('data',c=>d+=c).on('end',()=>{try{const j=JSON.parse(d);require('fs').mkdirSync('.vsaf',{recursive:true});require('fs').writeFileSync('.vsaf/.claude-session',j.session_id||'')}catch{}})"`;
/**
 * Đảm bảo `.claude/settings.json` còn hook `SessionStart` của vsaf.
 *
 * Separate from `init` and callable again, because something else keeps removing it. The
 * NTAPP pack's wiring script merges its own event hooks with one assignment —
 * `data["hooks"] = manifest["hooks"]` — which replaces the whole object rather than the
 * three keys it owns, so every key it does not know about goes with it. That is the pack's
 * script, and this does not touch it.
 *
 * Measured: `--new` ends up with the hook because `init` runs after the wiring and puts it
 * back, while `--refresh`, `--clone` and `--upgrade` skip `init` — so from the second run
 * onward, and on every teammate's machine, the hook was simply gone. Nothing reported it:
 * telemetry just stopped carrying a session.
 *
 * Only ever adds. An existing `SessionStart` — the user's own, or a newer form of this one
 * — is left exactly as it is, and a settings file that does not parse is left alone rather
 * than rewritten from scratch.
 */
function ensureSessionHook(projectPath) {
    const claudeDir = (0, path_1.join)(projectPath, '.claude');
    const settingsPath = (0, path_1.join)(claudeDir, 'settings.json');
    let settings = {};
    if ((0, fs_1.existsSync)(settingsPath)) {
        try {
            const parsed = JSON.parse((0, fs_1.readFileSync)(settingsPath, 'utf-8'));
            // `null` is valid JSON and not a settings object; rewriting it would throw away
            // whatever the person meant by it.
            if (!parsed || typeof parsed !== 'object')
                return 'unreadable';
            settings = parsed;
        }
        catch {
            return 'unreadable';
        }
    }
    const hooks = (settings.hooks ??= {});
    if (hooks.SessionStart)
        return 'kept';
    hooks.SessionStart = [{ hooks: [{ type: 'command', command: exports.SESSION_HOOK_COMMAND }] }];
    (0, fs_1.mkdirSync)(claudeDir, { recursive: true });
    (0, fs_1.writeFileSync)(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');
    return 'added';
}
//# sourceMappingURL=session-hook.js.map