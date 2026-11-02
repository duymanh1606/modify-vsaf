"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.loadConfig = loadConfig;
// packages/core/src/config/config-loader.ts
const fs_1 = require("fs");
const path_1 = require("path");
const js_yaml_1 = __importDefault(require("js-yaml"));
const DEFAULT_CONFIG = {
    provider: 'claude',
    model: 'sonnet',
    isolation: {
        type: 'ephemeral',
        cleanup: 'after_success',
        exclude: ['node_modules', '.git', 'dist', 'build', '.vsaf/storage'],
        max_workspaces: 5,
    },
};
function loadConfig(projectPath) {
    const configPath = (0, path_1.join)(projectPath, '.vsaf', 'config.yaml');
    if (!(0, fs_1.existsSync)(configPath)) {
        return { ...DEFAULT_CONFIG };
    }
    const raw = (0, fs_1.readFileSync)(configPath, 'utf-8');
    // A hand-edited config with one bad indent used to throw a raw YAMLException all
    // the way out of whatever called this — `vsaf doctor`, the diagnostic command,
    // died on a Node stack trace instead of reporting the problem. Defaults keep the
    // caller alive; the warning names the file so the user can go fix it.
    let parsed = null;
    try {
        parsed = js_yaml_1.default.load(raw);
    }
    catch (error) {
        const reason = error instanceof Error ? error.message.split('\n')[0] : String(error);
        console.warn(`[vsaf] ${configPath} is not valid YAML (${reason}) — falling back to defaults.`);
        return { ...DEFAULT_CONFIG };
    }
    if (!parsed) {
        return { ...DEFAULT_CONFIG };
    }
    return {
        provider: parsed.provider ?? DEFAULT_CONFIG.provider,
        model: parsed.model ?? DEFAULT_CONFIG.model,
        isolation: {
            ...DEFAULT_CONFIG.isolation,
            ...(parsed.isolation ?? {}),
        },
        telemetry: parsed.telemetry,
        test_command: parsed.test_command,
    };
}
//# sourceMappingURL=config-loader.js.map