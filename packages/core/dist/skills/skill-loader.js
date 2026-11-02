"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadSkill = loadSkill;
// packages/core/src/skills/skill-loader.ts
const fs_1 = require("fs");
const path_1 = require("path");
const gray_matter_1 = __importDefault(require("gray-matter"));
function loadSkill(name, projectPath) {
    // Primary: .claude/skills/, Fallback: .vsaf/skills/ (backward compat)
    const primaryDir = (0, path_1.join)(projectPath, '.claude', 'skills', name);
    const fallbackDir = (0, path_1.join)(projectPath, '.vsaf', 'skills', name);
    const skillDir = (0, fs_1.existsSync)((0, path_1.join)(primaryDir, 'SKILL.md')) ? primaryDir
        : (0, fs_1.existsSync)((0, path_1.join)(fallbackDir, 'SKILL.md')) ? fallbackDir
            : null;
    if (!skillDir) {
        throw new Error(`Skill not found: "${name}" (expected at ${(0, path_1.join)(primaryDir, 'SKILL.md')})`);
    }
    const skillFile = (0, path_1.join)(skillDir, 'SKILL.md');
    const raw = (0, fs_1.readFileSync)(skillFile, 'utf-8');
    const { data, content } = (0, gray_matter_1.default)(raw);
    const resolvedBody = resolveIncludes(content.trim(), skillDir);
    return {
        name: data.name ?? name,
        description: data.description ?? '',
        version: data.version,
        author: data.author,
        body: resolvedBody,
    };
}
function resolveIncludes(content, skillDir) {
    return content.replace(/@include\(([^)]+)\)/g, (_match, relativePath) => {
        const filePath = (0, path_1.join)(skillDir, relativePath.trim());
        if (!(0, fs_1.existsSync)(filePath)) {
            throw new Error(`Skill include not found: ${relativePath} (expected at ${filePath})`);
        }
        return (0, fs_1.readFileSync)(filePath, 'utf-8').trimEnd();
    });
}
//# sourceMappingURL=skill-loader.js.map