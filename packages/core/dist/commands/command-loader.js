"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadCommand = loadCommand;
// packages/core/src/commands/command-loader.ts
const fs_1 = require("fs");
const path_1 = require("path");
const gray_matter_1 = __importDefault(require("gray-matter"));
const skill_loader_js_1 = require("../skills/skill-loader.js");
function loadCommand(name, projectPath) {
    const filePath = (0, path_1.join)(projectPath, '.vsaf', 'commands', `${name}.md`);
    if (!(0, fs_1.existsSync)(filePath)) {
        throw new Error(`Command not found: "${name}" (expected at ${filePath})`);
    }
    const raw = (0, fs_1.readFileSync)(filePath, 'utf-8');
    const { data, content } = (0, gray_matter_1.default)(raw);
    let body = content.trim();
    if (data.skill) {
        const skill = (0, skill_loader_js_1.loadSkill)(data.skill, projectPath);
        body = body ? `${skill.body}\n\n${body}` : skill.body;
    }
    return {
        name,
        description: data.description ?? '',
        argumentHint: data['argument-hint'],
        skill: data.skill,
        body,
    };
}
//# sourceMappingURL=command-loader.js.map