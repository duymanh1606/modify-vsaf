import type { ExecutorCallbacks } from '@vsaf/core';
import type { Tracer } from './tracer.js';
import type { OutputMetricsCollector } from './metrics/output-metrics.js';
/**
 * Decorate executor callbacks with telemetry emission. The base callbacks
 * (RunStore persistence, console output, SSE) always run first and are
 * never affected by tracer failures.
 */
export declare function withTelemetry(base: ExecutorCallbacks, tracer: Tracer): ExecutorCallbacks;
/**
 * Measure what each node produced and attach it to that node's span.
 *
 * A snapshot is taken as the node starts and diffed when it completes, so this has to
 * wrap the decoration that ends the span — the attach happens while the span is still
 * open. `isMeasured` excludes bash nodes: their output is the engine's own doing, not
 * a node's work product.
 *
 * Extracted from the MCP engine to be reachable by a test. Left inline, breaking the
 * wiring kept the whole suite green while every span reported zero — the collector and
 * the tracer were each covered, and the line joining them was not.
 */
export declare function withOutputMetrics(base: ExecutorCallbacks, tracer: Tracer, outputMetrics: OutputMetricsCollector | undefined, isMeasured: (nodeId: string) => boolean): ExecutorCallbacks;
//# sourceMappingURL=callbacks.d.ts.map