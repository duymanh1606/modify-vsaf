"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildApp = buildApp;
const fastify_1 = __importDefault(require("fastify"));
const cors_1 = __importDefault(require("@fastify/cors"));
const health_js_1 = require("./routes/health.js");
const workflows_js_1 = require("./routes/workflows.js");
const runs_js_1 = require("./routes/runs.js");
const sse_manager_js_1 = require("./services/sse-manager.js");
const execution_manager_js_1 = require("./services/execution-manager.js");
function buildApp(options) {
    const app = (0, fastify_1.default)({ logger: false });
    const sseManager = new sse_manager_js_1.SseManager();
    const executionManager = new execution_manager_js_1.ExecutionManager(options.projectPath, sseManager);
    app.register(cors_1.default, { origin: true });
    app.register(health_js_1.healthRoutes, { prefix: '/api' });
    app.register(workflows_js_1.workflowRoutes, { prefix: '/api', projectPath: options.projectPath });
    app.register(runs_js_1.runRoutes, {
        prefix: '/api',
        projectPath: options.projectPath,
        executionManager,
        sseManager,
    });
    return app;
}
//# sourceMappingURL=app.js.map