"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.evaluateCondition = evaluateCondition;
function evaluateCondition(condition, nodeOutputs) {
    if (!condition)
        return true;
    // Split by || (lower precedence)
    const orParts = condition.split('||').map(s => s.trim());
    return orParts.some(orPart => {
        // Split by && (higher precedence)
        const andParts = orPart.split('&&').map(s => s.trim());
        return andParts.every(expr => evaluateSingle(expr, nodeOutputs));
    });
}
function evaluateSingle(expr, nodeOutputs) {
    const match = expr.match(/^\$([a-zA-Z0-9_-]+)\.output(?:\.([a-zA-Z0-9_]+))?\s*(==|!=)\s*'([^']*)'\s*$/);
    if (!match)
        return false;
    const [, nodeId, field, operator, expected] = match;
    const node = nodeOutputs[nodeId];
    if (!node)
        return false;
    let actual;
    if (field && node.structuredOutput) {
        const value = node.structuredOutput[field];
        actual = value !== undefined ? String(value) : '';
    }
    else {
        actual = node.output ?? '';
    }
    if (operator === '==')
        return actual === expected;
    if (operator === '!=')
        return actual !== expected;
    return false;
}
//# sourceMappingURL=condition-evaluator.js.map