import type { Tracer } from '../telemetry/tracer.js';
/**
 * Read the drift-check node's persisted results (.vsaf/telemetry/drift.json,
 * written by the sdlc-drift-check skill) and attach them to the currently
 * open drift-check span. Must run before onNodeComplete ends that span.
 * Telemetry must never break a run: any read/parse failure (missing file,
 * malformed JSON, unexpected shape) is swallowed silently.
 */
export declare function maybeAttachDrift(tracer: Tracer, projectPath: string, nodeId: string, isDriftNode: boolean): void;
//# sourceMappingURL=drift-glue.d.ts.map