"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execMCP = execMCP;
const server_js_1 = require("../mcp/server.js");
async function execMCP() {
    await (0, server_js_1.startMCPServer)();
}
//# sourceMappingURL=mcp.js.map