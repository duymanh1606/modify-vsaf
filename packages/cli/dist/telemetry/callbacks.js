"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.withTelemetry = withTelemetry;
exports.withOutputMetrics = withOutputMetrics;
function safe(fn) {
    try {
        fn();
    }
    catch {
        // Telemetry must never break a run.
    }
}
/**
 * Decorate executor callbacks with telemetry emission. The base callbacks
 * (RunStore persistence, console output, SSE) always run first and are
 * never affected by tracer failures.
 */
function withTelemetry(base, tracer) {
    return {
        onNodeStart: (nodeId) => {
            base.onNodeStart(nodeId);
            safe(() => tracer.nodeStart(nodeId));
        },
        onNodeComplete: (nodeId, result) => {
            base.onNodeComplete(nodeId, result);
            safe(() => tracer.nodeComplete(nodeId, result));
        },
        onNodeSkip: (nodeId, reason) => {
            base.onNodeSkip(nodeId, reason);
            safe(() => tracer.nodeSkip(nodeId, reason));
        },
        onNodeFail: (nodeId, error) => {
            base.onNodeFail(nodeId, error);
            safe(() => tracer.nodeFail(nodeId, error));
        },
    };
}
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
function withOutputMetrics(base, tracer, outputMetrics, isMeasured) {
    if (!outputMetrics)
        return base;
    return {
        ...base,
        onNodeStart: (nodeId) => {
            base.onNodeStart(nodeId);
            if (isMeasured(nodeId))
                safe(() => outputMetrics.snapshot(nodeId));
        },
        onNodeComplete: (nodeId, result) => {
            if (isMeasured(nodeId)) {
                safe(() => {
                    const metrics = outputMetrics.delta(nodeId);
                    if (metrics)
                        tracer.attachOutputMetrics(nodeId, metrics);
                });
            }
            base.onNodeComplete(nodeId, result);
        },
    };
}
//# sourceMappingURL=callbacks.js.map