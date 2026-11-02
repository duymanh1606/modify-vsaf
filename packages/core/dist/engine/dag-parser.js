"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseWorkflow = parseWorkflow;
// packages/core/src/engine/dag-parser.ts
const js_yaml_1 = __importDefault(require("js-yaml"));
const cycle_detector_js_1 = require("./cycle-detector.js");
const validators_js_1 = require("../schema/validators.js");
function detectNodeType(node) {
    if (node.prompt)
        return 'prompt';
    if (node.bash)
        return 'bash';
    return 'command';
}
function getNodeContent(node) {
    return node.prompt ?? node.bash ?? node.command ?? '';
}
function parseWorkflow(yamlContent) {
    const raw = js_yaml_1.default.load(yamlContent);
    // AJV schema validation
    const { valid, errors } = (0, validators_js_1.validateWorkflowSchema)(raw);
    if (!valid) {
        throw new Error(`Invalid workflow:\n${errors.join('\n')}`);
    }
    const def = raw;
    const nodes = new Map();
    // Duplicate ID check (AJV cannot validate uniqueness by property)
    for (const nodeDef of def.nodes) {
        if (nodes.has(nodeDef.id)) {
            throw new Error(`Duplicate node ID: "${nodeDef.id}"`);
        }
        nodes.set(nodeDef.id, {
            id: nodeDef.id,
            type: detectNodeType(nodeDef),
            content: getNodeContent(nodeDef),
            dependsOn: nodeDef.depends_on ?? [],
            when: nodeDef.when,
            triggerRule: nodeDef.trigger_rule ?? 'all_success',
            context: nodeDef.context ?? 'inherit',
            workspace: nodeDef.workspace ?? true,
            model: nodeDef.model,
            allowedTools: nodeDef.allowed_tools,
            outputFormat: nodeDef.output_format,
            status: 'pending',
            errorStrategy: nodeDef.on_error ?? 'skip_dependents',
            ledger: nodeDef.ledger,
            fanout: nodeDef.fanout
                ? {
                    over: nodeDef.fanout.over,
                    as: nodeDef.fanout.as,
                    maxConcurrency: nodeDef.fanout.max_concurrency ?? Infinity,
                }
                : undefined,
            loop: nodeDef.loop ? {
                onFail: nodeDef.loop.on_fail,
                maxRetries: nodeDef.loop.max_retries,
                injectError: nodeDef.loop.inject_error ?? false,
                backoffMs: nodeDef.loop.backoff_ms,
            } : undefined,
        });
    }
    // Graph-semantic checks (not expressible in JSON Schema)
    for (const [id, node] of nodes) {
        for (const dep of node.dependsOn) {
            if (!nodes.has(dep)) {
                throw new Error(`Node "${id}" depends on unknown node "${dep}"`);
            }
        }
    }
    const cycleNodes = (0, cycle_detector_js_1.detectCycle)(nodes);
    if (cycleNodes) {
        throw new Error(`Circular dependency detected among nodes: ${cycleNodes.join(', ')}`);
    }
    for (const [id, node] of nodes) {
        if (node.loop && !nodes.has(node.loop.onFail)) {
            throw new Error(`Node "${id}" loop.on_fail references unknown node "${node.loop.onFail}"`);
        }
    }
    return {
        name: def.name,
        description: def.description ?? '',
        defaultProvider: def.provider ?? 'claude',
        defaultModel: def.model ?? 'sonnet',
        inputs: def.inputs,
        nodes,
    };
}
//# sourceMappingURL=dag-parser.js.map