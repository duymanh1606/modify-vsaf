"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.maybeAttachDrift = maybeAttachDrift;
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
/**
 * Read the drift-check node's persisted results (.vsaf/telemetry/drift.json,
 * written by the sdlc-drift-check skill) and attach them to the currently
 * open drift-check span. Must run before onNodeComplete ends that span.
 * Telemetry must never break a run: any read/parse failure (missing file,
 * malformed JSON, unexpected shape) is swallowed silently.
 */
function maybeAttachDrift(tracer, projectPath, nodeId, isDriftNode) {
    if (!isDriftNode)
        return;
    try {
        const raw = (0, node_fs_1.readFileSync)((0, node_path_1.join)(projectPath, '.vsaf/telemetry/drift.json'), 'utf8');
        const parsed = JSON.parse(raw);
        const edges = parsed.edges ?? [];
        if (edges.length)
            tracer.attachDriftScores(nodeId, edges);
    }
    catch {
        /* missing file / bad JSON: no-op, never break the run */
    }
}
//# sourceMappingURL=drift-glue.js.map