"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildNeverRejectFlush = buildNeverRejectFlush;
exports.assembleRuntime = assembleRuntime;
exports.createOtelRuntime = createOtelRuntime;
/**
 * One shared deadline for all targets (Δ8): flushing traces and metrics
 * sequentially would double the worst-case wait and break NFR-03 (≤5s).
 */
function buildNeverRejectFlush(targets) {
    return async (timeoutMs) => {
        let timer;
        const deadline = new Promise((resolve) => {
            timer = setTimeout(resolve, timeoutMs);
            timer.unref?.();
        });
        const all = Promise.allSettled(targets.map((t) => t.forceFlush())).then(() => undefined);
        await Promise.race([all, deadline]);
        clearTimeout(timer);
    };
}
/**
 * Assemble an OtelRuntime from already-constructed providers. Split from
 * createOtelRuntime so tests can inject an InMemorySpanExporter-backed
 * provider without duplicating the span-wrapping logic. Still lazy: the
 * @opentelemetry/api require happens at call time, not import time.
 */
function assembleRuntime(parts) {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const api = require('@opentelemetry/api');
    const tracer = parts.tracerProvider.getTracer('vsaf');
    const flushables = [parts.tracerProvider, ...(parts.extraFlushables ?? [])];
    const shutdownables = [parts.tracerProvider, ...(parts.extraShutdownables ?? [])];
    const wrap = (otelSpan) => ({
        _otelSpan: otelSpan,
        setAttribute: (k, v) => void otelSpan.setAttribute(k, v),
        setAttributes: (a) => void otelSpan.setAttributes(a),
        setStatus: ({ code, message }) => void otelSpan.setStatus({
            code: code === 'ERROR'
                ? api.SpanStatusCode.ERROR
                : code === 'OK'
                    ? api.SpanStatusCode.OK
                    : api.SpanStatusCode.UNSET,
            message,
        }),
        end: (t) => otelSpan.end(t),
        spanContext: () => otelSpan.spanContext(),
    });
    const flush = buildNeverRejectFlush(flushables);
    return {
        startSpan(name, spanOpts, parent) {
            const ctx = parent
                ? api.trace.setSpan(api.context.active(), parent._otelSpan)
                : api.context.active();
            return wrap(tracer.startSpan(name, { startTime: spanOpts.startTime, attributes: spanOpts.attributes }, ctx));
        },
        addMetric: parts.addMetric ?? (() => { }),
        flush,
        shutdown: async () => {
            let timer;
            const deadline = new Promise((resolve) => {
                timer = setTimeout(resolve, 2_000);
                timer.unref?.();
            });
            const all = Promise.allSettled(shutdownables.map((s) => s.shutdown())).then(() => undefined);
            await Promise.race([all, deadline]);
            clearTimeout(timer);
        },
    };
}
function createOtelRuntime(settings, opts) {
    /* eslint-disable @typescript-eslint/no-var-requires */
    const api = require('@opentelemetry/api');
    const { BasicTracerProvider, BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter } = require('@opentelemetry/sdk-trace-base');
    const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-proto');
    const { resourceFromAttributes } = require('@opentelemetry/resources');
    const { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } = require('@opentelemetry/semantic-conventions');
    /* eslint-enable @typescript-eslint/no-var-requires */
    if (opts.debug) {
        api.diag.setLogger(new api.DiagConsoleLogger(), api.DiagLogLevel.DEBUG);
    }
    let serviceVersion = '0.0.0';
    try {
        // src/telemetry/ and dist/telemetry/ both sit two levels under packages/cli.
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        serviceVersion = require('../../package.json').version ?? serviceVersion;
    }
    catch {
        /* keep fallback */
    }
    const resource = resourceFromAttributes({
        [ATTR_SERVICE_NAME]: 'vsaf',
        [ATTR_SERVICE_VERSION]: serviceVersion,
    });
    const spanProcessors = [
        new BatchSpanProcessor(new OTLPTraceExporter({ url: settings.tracesUrl, headers: settings.headers, timeoutMillis: 10_000 }), {
            // Δ7: endRun releases every deferred span at once — the queue must fit a large DAG.
            maxQueueSize: Math.max(512, opts.nodeCount * 2),
            scheduledDelayMillis: 5_000,
            exportTimeoutMillis: 10_000,
        }),
    ];
    if (opts.debug) {
        spanProcessors.push(new SimpleSpanProcessor(new ConsoleSpanExporter()));
    }
    const tracerProvider = new BasicTracerProvider({
        resource,
        spanProcessors,
        forceFlushTimeoutMillis: 5_000,
    });
    let addMetric;
    const extraFlushables = [];
    const extraShutdownables = [];
    if (settings.metricsUrl) {
        /* eslint-disable @typescript-eslint/no-var-requires */
        const { MeterProvider, PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
        const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-proto');
        /* eslint-enable @typescript-eslint/no-var-requires */
        const meterProvider = new MeterProvider({
            resource,
            readers: [
                new PeriodicExportingMetricReader({
                    exporter: new OTLPMetricExporter({
                        url: settings.metricsUrl,
                        headers: settings.headers,
                        timeoutMillis: 10_000,
                    }),
                    exportIntervalMillis: 60_000,
                    exportTimeoutMillis: 10_000,
                }),
            ],
        });
        const meter = meterProvider.getMeter('vsaf');
        const counters = new Map();
        addMetric = (name, value, attributes) => {
            let counter = counters.get(name);
            if (!counter) {
                counter = meter.createCounter(name);
                counters.set(name, counter);
            }
            counter.add(value, attributes);
        };
        extraFlushables.push(meterProvider);
        extraShutdownables.push(meterProvider);
    }
    return assembleRuntime({ tracerProvider, addMetric, extraFlushables, extraShutdownables });
}
//# sourceMappingURL=otel-sdk.js.map