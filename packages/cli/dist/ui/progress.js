"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.formatNodeStatus = formatNodeStatus;
exports.formatSummary = formatSummary;
function formatNodeStatus(nodeId, status, durationMs) {
    const pad = nodeId.padEnd(30, ' .');
    switch (status) {
        case 'running':
            return `  ● ${pad} ⏳`;
        case 'completed':
            return `  ● ${pad} ✓ ${durationMs ? (durationMs / 1000).toFixed(1) + 's' : ''}`;
        case 'skipped':
            return `  ○ ${pad} ⊘ skipped`;
        case 'failed':
            return `  ● ${pad} ✗ FAILED`;
        default:
            return `  ○ ${pad} pending`;
    }
}
function formatSummary(success, totalMs) {
    const time = (totalMs / 1000).toFixed(1);
    if (success) {
        return `\n[vsaf] ✓ Workflow completed in ${time}s`;
    }
    return `\n[vsaf] ✗ Workflow failed after ${time}s`;
}
//# sourceMappingURL=progress.js.map