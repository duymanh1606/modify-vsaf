"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerStatic = registerStatic;
const fs_1 = require("fs");
const path_1 = require("path");
const static_1 = __importDefault(require("@fastify/static"));
async function registerStatic(app) {
    // Resolve web package dist relative to CLI package
    const webDist = (0, path_1.resolve)(__dirname, '..', '..', '..', 'web', 'dist', 'web', 'browser');
    if (!(0, fs_1.existsSync)(webDist)) {
        return false;
    }
    app.register(static_1.default, {
        root: webDist,
        prefix: '/',
        wildcard: false,
    });
    // SPA fallback: serve index.html for non-API, non-file routes
    app.setNotFoundHandler((request, reply) => {
        if (request.url.startsWith('/api')) {
            return reply.status(404).send({ error: 'Not found' });
        }
        return reply.sendFile('index.html');
    });
    return true;
}
//# sourceMappingURL=static.js.map