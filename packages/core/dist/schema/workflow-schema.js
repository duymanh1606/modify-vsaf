"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.workflowSchema = void 0;
const nodeSchema = {
    type: 'object',
    required: ['id'],
    oneOf: [
        { required: ['prompt'], not: { anyOf: [{ required: ['bash'] }, { required: ['command'] }] } },
        { required: ['bash'], not: { anyOf: [{ required: ['prompt'] }, { required: ['command'] }] } },
        { required: ['command'], not: { anyOf: [{ required: ['prompt'] }, { required: ['bash'] }] } },
    ],
    additionalProperties: false,
    properties: {
        id: { type: 'string', minLength: 1 },
        // Human-readable note on what this node does. Every NTAPP workflow node carries one.
        description: { type: 'string' },
        prompt: { type: 'string' },
        bash: { type: 'string' },
        command: { type: 'string' },
        depends_on: { type: 'array', items: { type: 'string' } },
        when: { type: 'string' },
        trigger_rule: { type: 'string', enum: ['all_success', 'one_success'] },
        context: { type: 'string', enum: ['fresh', 'inherit'] },
        model: { type: 'string' },
        workspace: { type: 'boolean' },
        // Read-only cross-iteration context: engine reads this file and prepends its
        // tail to the AI prompt. The engine never writes it — other nodes do.
        ledger: { type: 'string', minLength: 1 },
        // Expand one node into N sub-tasks, one per file matched by the `over` glob.
        fanout: {
            type: 'object',
            required: ['over', 'as'],
            additionalProperties: false,
            properties: {
                over: { type: 'string', minLength: 1 },
                as: { type: 'string', minLength: 1 },
                max_concurrency: { type: 'integer', minimum: 1 },
            },
        },
        allowed_tools: { type: 'array', items: { type: 'string' } },
        on_error: { type: 'string', enum: ['skip_dependents', 'fail_workflow', 'continue'] },
        output_format: {
            type: 'object',
            required: ['type', 'properties'],
            properties: {
                type: { type: 'string', enum: ['object'] },
                properties: {
                    type: 'object',
                    additionalProperties: {
                        type: 'object',
                        properties: {
                            type: { type: 'string' },
                            enum: { type: 'array', items: { type: 'string' } },
                        },
                    },
                },
                required: { type: 'array', items: { type: 'string' } },
            },
        },
        loop: {
            type: 'object',
            required: ['on_fail', 'max_retries'],
            properties: {
                on_fail: { type: 'string' },
                max_retries: { type: 'integer', minimum: 1 },
                inject_error: { type: 'boolean' },
                backoff_ms: { type: 'integer', minimum: 0 },
            },
            additionalProperties: false,
        },
    },
};
exports.workflowSchema = {
    type: 'object',
    required: ['name', 'nodes'],
    additionalProperties: false,
    properties: {
        name: { type: 'string', minLength: 1 },
        description: { type: 'string' },
        provider: { type: 'string' },
        model: { type: 'string' },
        inputs: {
            type: 'object',
            additionalProperties: {
                type: 'object',
                properties: {
                    type: { type: 'string', enum: ['string', 'number', 'boolean'] },
                    required: { type: 'boolean' },
                    default: { type: 'string' },
                },
            },
        },
        nodes: {
            type: 'array',
            minItems: 1,
            items: nodeSchema,
        },
    },
};
//# sourceMappingURL=workflow-schema.js.map