"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.listWorkflows = listWorkflows;
const fs_1 = require("fs");
const path_1 = require("path");
const js_yaml_1 = __importDefault(require("js-yaml"));
function listWorkflows(projectPath) {
    const workflowsDir = (0, path_1.join)(projectPath, '.vsaf', 'workflows');
    if (!(0, fs_1.existsSync)(workflowsDir))
        return [];
    return scanWorkflowDir(workflowsDir, '');
}
function scanWorkflowDir(dir, prefix) {
    const results = [];
    const entries = (0, fs_1.readdirSync)(dir);
    for (const entry of entries) {
        const fullPath = (0, path_1.join)(dir, entry);
        const stat = (0, fs_1.statSync)(fullPath);
        if (stat.isDirectory()) {
            const subPrefix = prefix ? `${prefix}/${entry}` : entry;
            results.push(...scanWorkflowDir(fullPath, subPrefix));
        }
        else if (entry.endsWith('.yaml') || entry.endsWith('.yml')) {
            const content = (0, fs_1.readFileSync)(fullPath, 'utf-8');
            const parsed = js_yaml_1.default.load(content);
            const baseName = entry.replace(/\.ya?ml$/, '');
            const name = prefix ? `${prefix}/${baseName}` : (parsed?.name ?? baseName);
            results.push({
                name,
                description: (parsed?.description ?? '').split('\n')[0].trim(),
                file: prefix ? `${prefix}/${entry}` : entry,
            });
        }
    }
    return results;
}
//# sourceMappingURL=list.js.map