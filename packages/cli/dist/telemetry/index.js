"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveUserId = exports.resolveCodeRoots = exports.OutputMetricsCollector = exports.CLAUDE_SESSION_FILE = exports.readClaudeSessionId = exports.withOutputMetrics = exports.withTelemetry = exports.assembleRuntime = exports.createOtelRuntime = exports.OtelRunTracer = exports.NoopTracer = exports.resolveTelemetryConfig = void 0;
exports.createTelemetry = createTelemetry;
const config_js_1 = require("./config.js");
const tracer_js_1 = require("./tracer.js");
const otel_tracer_js_1 = require("./otel-tracer.js");
const otel_sdk_js_1 = require("./otel-sdk.js");
const claude_session_js_1 = require("./session/claude-session.js");
const output_metrics_js_1 = require("./metrics/output-metrics.js");
const code_roots_js_1 = require("./metrics/code-roots.js");
const user_js_1 = require("./user.js");
const langfuse_scores_js_1 = require("./langfuse-scores.js");
var config_js_2 = require("./config.js");
Object.defineProperty(exports, "resolveTelemetryConfig", { enumerable: true, get: function () { return config_js_2.resolveTelemetryConfig; } });
var tracer_js_2 = require("./tracer.js");
Object.defineProperty(exports, "NoopTracer", { enumerable: true, get: function () { return tracer_js_2.NoopTracer; } });
var otel_tracer_js_2 = require("./otel-tracer.js");
Object.defineProperty(exports, "OtelRunTracer", { enumerable: true, get: function () { return otel_tracer_js_2.OtelRunTracer; } });
var otel_sdk_js_2 = require("./otel-sdk.js");
Object.defineProperty(exports, "createOtelRuntime", { enumerable: true, get: function () { return otel_sdk_js_2.createOtelRuntime; } });
Object.defineProperty(exports, "assembleRuntime", { enumerable: true, get: function () { return otel_sdk_js_2.assembleRuntime; } });
var callbacks_js_1 = require("./callbacks.js");
Object.defineProperty(exports, "withTelemetry", { enumerable: true, get: function () { return callbacks_js_1.withTelemetry; } });
Object.defineProperty(exports, "withOutputMetrics", { enumerable: true, get: function () { return callbacks_js_1.withOutputMetrics; } });
var claude_session_js_2 = require("./session/claude-session.js");
Object.defineProperty(exports, "readClaudeSessionId", { enumerable: true, get: function () { return claude_session_js_2.readClaudeSessionId; } });
Object.defineProperty(exports, "CLAUDE_SESSION_FILE", { enumerable: true, get: function () { return claude_session_js_2.CLAUDE_SESSION_FILE; } });
var output_metrics_js_2 = require("./metrics/output-metrics.js");
Object.defineProperty(exports, "OutputMetricsCollector", { enumerable: true, get: function () { return output_metrics_js_2.OutputMetricsCollector; } });
var code_roots_js_2 = require("./metrics/code-roots.js");
Object.defineProperty(exports, "resolveCodeRoots", { enumerable: true, get: function () { return code_roots_js_2.resolveCodeRoots; } });
var user_js_2 = require("./user.js");
Object.defineProperty(exports, "resolveUserId", { enumerable: true, get: function () { return user_js_2.resolveUserId; } });
/**
 * One-stop wiring helper for the three run paths (MCP, HTTP server, CLI run).
 * Returns a NoopTracer when telemetry is not configured, so call sites never
 * need to branch. claudeSessionId (MCP mode) becomes the session.id span
 * attribute so vsaf and gateway traces group into one session on the backend.
 */
function createTelemetry(config, projectPath) {
    try {
        const resolved = (0, config_js_1.resolveTelemetryConfig)(config);
        const otlp = resolved.otlp;
        if (resolved.mode === 'disabled' || !otlp) {
            return { tracer: new tracer_js_1.NoopTracer() };
        }
        const claudeSessionId = (0, claude_session_js_1.readClaudeSessionId)(projectPath);
        const scoreClient = resolved.mode === 'legacy-langfuse' && resolved.langfuse
            ? (0, langfuse_scores_js_1.createLangfuseScoreClient)({
                host: resolved.langfuse.host,
                publicKey: resolved.langfuse.publicKey,
                secretKey: resolved.langfuse.secretKey,
            })
            : undefined;
        const tracer = new otel_tracer_js_1.OtelRunTracer((nodeCount) => (0, otel_sdk_js_1.createOtelRuntime)(otlp, {
            nodeCount,
            debug: Boolean(process.env.VSAF_TELEMETRY_DEBUG),
        }), 
        // gen_ai.provider.name uses the semconv well-known value: vsaf's
        // "claude" provider runs Anthropic models.
        {
            provider: config.provider === 'claude' ? 'anthropic' : config.provider,
            scoreClient,
        });
        // `include` replaces the default — a project that names its artifact folder
        // knows where its artifacts live. `exclude` only ever adds: the defaults are
        // the engine's own churn (worktrees, run storage), which no project has a
        // reason to start counting.
        const artifacts = config.telemetry?.artifacts;
        const outputMetrics = new output_metrics_js_1.OutputMetricsCollector(projectPath, {
            artifactPrefixes: artifacts?.include?.length ? artifacts.include : undefined,
            excludePrefixes: [...output_metrics_js_1.DEFAULT_EXCLUDE_PREFIXES, ...(artifacts?.exclude ?? [])],
            codeRoots: (0, code_roots_js_1.resolveCodeRoots)(projectPath, artifacts?.code_roots),
        });
        const userId = (0, user_js_1.resolveUserId)(projectPath);
        return { tracer, outputMetrics, claudeSessionId, userId };
    }
    catch {
        return { tracer: new tracer_js_1.NoopTracer() };
    }
}
//# sourceMappingURL=index.js.map