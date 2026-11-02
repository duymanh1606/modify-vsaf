"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildPrompt = buildPrompt;
// packages/core/src/commands/prompt-builder.ts
const variable_resolver_js_1 = require("../engine/variable-resolver.js");
function buildPrompt(body, ctx) {
    return (0, variable_resolver_js_1.resolveVariables)(body, ctx);
}
//# sourceMappingURL=prompt-builder.js.map