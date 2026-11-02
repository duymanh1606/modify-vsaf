"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NodeRunner = void 0;
exports.resolveBashShell = resolveBashShell;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const path_1 = require("path");
const util_1 = require("util");
const variable_resolver_js_1 = require("./variable-resolver.js");
const command_loader_js_1 = require("../commands/command-loader.js");
const prompt_builder_js_1 = require("../commands/prompt-builder.js");
const exec = (0, util_1.promisify)(child_process_1.exec);
/**
 * The shell a `bash:` node runs in.
 *
 * `exec()` defaults to `/bin/sh`, which on Debian and Ubuntu is dash. Workflow gates are
 * written as bash — arrays, `shopt`, `[[ ]]` — so under dash they die on a syntax error
 * *before* checking anything, and the run fails for a reason that has nothing to do with
 * what the gate was guarding. The field is named `bash`; this makes that true.
 *
 * Falls back to the default shell when no bash is found, which keeps a machine without it
 * working exactly as before rather than failing to spawn.
 */
const BASH_CANDIDATES = process.platform === 'win32'
    ? [
        'C:\\Program Files\\Git\\bin\\bash.exe',
        'C:\\Program Files (x86)\\Git\\bin\\bash.exe',
    ]
    : ['/bin/bash', '/usr/bin/bash', '/usr/local/bin/bash'];
let cachedShell = null;
function resolveBashShell() {
    if (cachedShell !== null)
        return cachedShell;
    cachedShell = BASH_CANDIDATES.find(path => (0, fs_1.existsSync)(path));
    return cachedShell;
}
class NodeRunner {
    workspaceCwd;
    projectCwd;
    constructor(workspaceCwd, projectCwd) {
        this.workspaceCwd = workspaceCwd;
        this.projectCwd = projectCwd;
    }
    getCwd(node) {
        if (!node.workspace && this.projectCwd)
            return this.projectCwd;
        return this.workspaceCwd;
    }
    /**
     * Cross-iteration context: when a node declares `ledger: <path>`, read that file
     * and return a READ-ONLY preamble to prepend to the prompt — the lessons a previous
     * iteration left behind. Capped at the last 16 KB because the file is append-only,
     * so the tail is the recent part. A missing, unreadable or blank file yields '' and
     * is never an error. The engine only reads; other nodes in the workflow do the writing.
     */
    ledgerPreamble(node) {
        if (!node.ledger)
            return '';
        try {
            const path = (0, path_1.isAbsolute)(node.ledger) ? node.ledger : (0, path_1.join)(this.getCwd(node), node.ledger);
            if (!(0, fs_1.existsSync)(path))
                return '';
            let text = (0, fs_1.readFileSync)(path, 'utf-8');
            const CAP = 16 * 1024;
            if (text.length > CAP) {
                text = `...(truncated; latest tail)...\n${text.slice(text.length - CAP)}`;
            }
            if (!text.trim())
                return '';
            // Wording kept verbatim from the pack this feature came from: the line goes into
            // the model's prompt, so paraphrasing it changes the instruction the node reads.
            return `## Cross-iteration ledger (bài học từ vòng trước — READ-ONLY context, KHÔNG sửa file này ở node đọc)\n\n${text.trimEnd()}\n\n---\n\n`;
        }
        catch {
            return '';
        }
    }
    async runBash(node, ctx) {
        const startedAt = new Date().toISOString();
        const startTime = Date.now();
        const resolvedScript = (0, variable_resolver_js_1.resolveVariables)(node.content, ctx, 'bash');
        const unresolvedConfig = resolvedScript.match(/\$CONFIG\.([a-zA-Z0-9_-]+)/);
        if (unresolvedConfig) {
            throw new Error(`Node "${node.id}" references $CONFIG.${unresolvedConfig[1]} but "${unresolvedConfig[1]}" is not set in .vsaf/config.yaml. ` +
                `Add it (e.g. test_command: npm test) or run /sdlc-onboard-code to detect it.`);
        }
        const { stdout } = await exec(resolvedScript, {
            cwd: this.getCwd(node),
            env: { ...process.env, ARTIFACTS_DIR: ctx.ARTIFACTS_DIR },
            maxBuffer: 10 * 1024 * 1024,
            shell: resolveBashShell(),
        });
        return {
            status: 'completed',
            output: stdout,
            durationMs: Date.now() - startTime,
            startedAt,
            completedAt: new Date().toISOString(),
        };
    }
    resolveAIPrompt(node, ctx) {
        // Read once, reuse for whichever branch runs — reading the file twice buys nothing.
        const ledger = this.ledgerPreamble(node);
        let resolved;
        if (node.type === 'command') {
            if (!this.projectCwd)
                throw new Error(`Command node "${node.id}" requires projectPath`);
            const cmd = (0, command_loader_js_1.loadCommand)(node.content, this.projectCwd);
            resolved = {
                prompt: ledger + (0, prompt_builder_js_1.buildPrompt)(cmd.body, ctx),
                skill: cmd.skill,
            };
        }
        else {
            // type === 'prompt'
            resolved = { prompt: ledger + (0, variable_resolver_js_1.resolveVariables)(node.content, ctx) };
        }
        return this.withInjectedError(node, resolved);
    }
    /**
     * When a loop with inject_error reset this node, carry the downstream
     * failure (e.g. test-gate output) into its prompt so the model fixes the
     * real error instead of retrying blind. One-shot: cleared after use.
     */
    withInjectedError(node, resolved) {
        if (!node.error)
            return resolved;
        const MAX_ERROR_CHARS = 4000;
        const error = node.error.length > MAX_ERROR_CHARS
            ? `…(truncated)\n${node.error.slice(-MAX_ERROR_CHARS)}`
            : node.error;
        node.error = undefined;
        return {
            ...resolved,
            prompt: `${resolved.prompt}\n\n---\n` +
                `The previous attempt failed a downstream check (e.g. test-gate). ` +
                `Fix the code so the following error no longer occurs:\n\n${error}`,
        };
    }
}
exports.NodeRunner = NodeRunner;
//# sourceMappingURL=node-runner.js.map