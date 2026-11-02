"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveVariables = resolveVariables;
// packages/core/src/engine/variable-resolver.ts
const IS_WIN = process.platform === 'win32';
/**
 * Quote a value so a shell treats it as ONE word, whatever it contains.
 * Only ever applied to DATA (see `ResolveMode`), never to something meant to run.
 */
function shellEscape(value) {
    if (IS_WIN) {
        // cmd.exe / PowerShell: wrap in double quotes, escape inner ones
        return `"${value.replace(/"/g, '\\"')}"`;
    }
    return `'${value.replace(/'/g, "'\\''")}'`;
}
function resolveVariables(template, ctx, mode = 'prompt') {
    let result = template;
    const data = (value) => (mode === 'bash' ? shellEscape(value) : value);
    // Per-item fanout variables — resolved FIRST because the names are plain identifiers
    // (${ITEM}, ${UNIT}) and must not be mistaken for the $node.output syntax below.
    if (ctx.fanout) {
        for (const [name, raw] of Object.entries(ctx.fanout)) {
            const value = data(String(raw));
            result = result.replaceAll(`\${${name}}`, value);
            result = result.replace(new RegExp(`\\$${name}\\b`, 'g'), value);
        }
    }
    // Replace $CONFIG.<key> from project config. Resolved before the script
    // reaches any shell, so it works identically on cmd.exe and sh.
    // NOT escaped — see ResolveMode: this is a command to run, not data.
    result = result.replace(/\$CONFIG\.([a-zA-Z0-9_-]+)/g, (_match, key) => {
        const value = ctx.config?.[key];
        return value !== undefined ? value : _match;
    });
    result = result.replaceAll('$ARGUMENTS', data(ctx.ARGUMENTS));
    result = result.replaceAll('$ARTIFACTS_DIR', data(ctx.ARTIFACTS_DIR));
    // Replace $node-id.output.field (must come before $node-id.output)
    result = result.replace(/\$([a-zA-Z0-9_-]+)\.output\.([a-zA-Z0-9_]+)/g, (_match, nodeId, field) => {
        const node = ctx.nodes[nodeId];
        if (!node?.structuredOutput)
            return _match;
        const value = node.structuredOutput[field];
        return value !== undefined ? data(String(value)) : _match;
    });
    // Replace $node-id.output
    result = result.replace(/\$([a-zA-Z0-9_-]+)\.output(?!\.)/g, (_match, nodeId) => {
        const node = ctx.nodes[nodeId];
        if (!node)
            return _match;
        return data(node.output ?? '');
    });
    return result;
}
//# sourceMappingURL=variable-resolver.js.map