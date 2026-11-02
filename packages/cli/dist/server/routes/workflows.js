"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.workflowRoutes = workflowRoutes;
const fs_1 = require("fs");
const path_1 = require("path");
const core_1 = require("@vsaf/core");
const js_yaml_1 = __importDefault(require("js-yaml"));
async function workflowRoutes(app, opts) {
    const workflowsDir = (0, path_1.join)(opts.projectPath, '.vsaf', 'workflows');
    app.get('/workflows', async () => {
        if (!(0, fs_1.existsSync)(workflowsDir))
            return [];
        const files = (0, fs_1.readdirSync)(workflowsDir).filter(f => f.endsWith('.yaml') || f.endsWith('.yml'));
        return files.map(file => {
            const content = (0, fs_1.readFileSync)((0, path_1.join)(workflowsDir, file), 'utf-8');
            const parsed = js_yaml_1.default.load(content);
            return {
                name: parsed?.name ?? file.replace(/\.ya?ml$/, ''),
                description: (parsed?.description ?? '').split('\n')[0].trim(),
                nodeCount: Array.isArray(parsed?.nodes) ? parsed.nodes.length : 0,
                file,
            };
        });
    });
    app.get('/workflows/:name', async (request, reply) => {
        const { name } = request.params;
        const filePath = (0, path_1.join)(workflowsDir, `${name}.yaml`);
        if (!(0, fs_1.existsSync)(filePath)) {
            return reply.status(404).send({ error: `Workflow not found: ${name}` });
        }
        const content = (0, fs_1.readFileSync)(filePath, 'utf-8');
        const graph = (0, core_1.parseWorkflow)(content);
        const nodes = [...graph.nodes.values()].map(n => ({
            id: n.id,
            type: n.type,
            content: n.content.substring(0, 200),
            dependsOn: n.dependsOn,
            when: n.when,
            triggerRule: n.triggerRule,
            context: n.context,
            model: n.model,
        }));
        return {
            name: graph.name,
            description: graph.description,
            defaultProvider: graph.defaultProvider,
            defaultModel: graph.defaultModel,
            nodeCount: nodes.length,
            nodes,
        };
    });
}
//# sourceMappingURL=workflows.js.map