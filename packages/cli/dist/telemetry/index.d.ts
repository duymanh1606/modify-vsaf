import type { VSAFConfig } from '@vsaf/core';
import { type Tracer } from './tracer.js';
import { OutputMetricsCollector } from './metrics/output-metrics.js';
export { resolveTelemetryConfig } from './config.js';
export type { ResolvedTelemetryConfig, TelemetryMode, OtlpSettings, } from './config.js';
export { NoopTracer } from './tracer.js';
export type { Tracer, RunInfo } from './tracer.js';
export { OtelRunTracer, type OtelTracerOptions } from './otel-tracer.js';
export { createOtelRuntime, assembleRuntime, type OtelRuntime, type SpanLike } from './otel-sdk.js';
export { withTelemetry, withOutputMetrics } from './callbacks.js';
export type { RunOutcome } from './tracer.js';
export { readClaudeSessionId, CLAUDE_SESSION_FILE } from './session/claude-session.js';
export { OutputMetricsCollector } from './metrics/output-metrics.js';
export type { NodeOutputMetrics, RepoRole, RoleMetrics } from './metrics/output-metrics.js';
export { resolveCodeRoots } from './metrics/code-roots.js';
export { resolveUserId } from './user.js';
export interface TelemetrySetup {
    tracer: Tracer;
    outputMetrics?: OutputMetricsCollector;
    claudeSessionId?: string;
    userId?: string;
}
/**
 * One-stop wiring helper for the three run paths (MCP, HTTP server, CLI run).
 * Returns a NoopTracer when telemetry is not configured, so call sites never
 * need to branch. claudeSessionId (MCP mode) becomes the session.id span
 * attribute so vsaf and gateway traces group into one session on the backend.
 */
export declare function createTelemetry(config: VSAFConfig, projectPath: string): TelemetrySetup;
//# sourceMappingURL=index.d.ts.map