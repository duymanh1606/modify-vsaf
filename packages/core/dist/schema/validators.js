"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.validateWorkflowSchema = validateWorkflowSchema;
exports.validateOutputFormat = validateOutputFormat;
exports.validateInputs = validateInputs;
const ajv_instance_js_1 = require("./ajv-instance.js");
const workflow_schema_js_1 = require("./workflow-schema.js");
function formatErrors(errors) {
    if (!errors)
        return [];
    return errors.map(e => {
        const path = e.instancePath || 'root';
        // Post-process oneOf errors on node items for readability
        if (e.keyword === 'oneOf' && path.match(/\/nodes\/\d+$/)) {
            return `${path}: must have exactly one of: prompt, bash, command`;
        }
        return `${path}: ${e.message}`;
    });
}
const validateWorkflow = ajv_instance_js_1.ajv.compile(workflow_schema_js_1.workflowSchema);
function validateWorkflowSchema(raw) {
    const valid = validateWorkflow(raw);
    return { valid: !!valid, errors: valid ? [] : formatErrors(validateWorkflow.errors) };
}
function validateOutputFormat(output, format) {
    const properties = {};
    for (const [key, prop] of Object.entries(format.properties)) {
        const schemaProp = { type: prop.type };
        if (prop.enum)
            schemaProp.enum = prop.enum;
        properties[key] = schemaProp;
    }
    const schema = {
        type: 'object',
        properties,
        required: format.required ?? [],
    };
    const validate = ajv_instance_js_1.ajv.compile(schema);
    const valid = validate(output ?? {});
    return { valid: !!valid, errors: valid ? [] : formatErrors(validate.errors) };
}
function validateInputs(args, inputs) {
    let parsed;
    try {
        parsed = JSON.parse(args || '{}');
    }
    catch {
        return ['Args must be valid JSON when input schema is defined'];
    }
    const required = Object.entries(inputs)
        .filter(([, def]) => def.required && def.default === undefined)
        .map(([name]) => name);
    const properties = {};
    for (const [name, def] of Object.entries(inputs)) {
        properties[name] = { type: def.type };
    }
    const schema = {
        type: 'object',
        required,
        properties,
    };
    const validate = ajv_instance_js_1.ajv.compile(schema);
    const valid = validate(parsed);
    if (valid)
        return [];
    return formatErrors(validate.errors);
}
//# sourceMappingURL=validators.js.map