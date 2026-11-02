"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveTelemetryConfig = resolveTelemetryConfig;
function stripTrailingSlashes(url) {
    return url.replace(/\/+$/, '');
}
function nonEmpty(value) {
    return value && value.trim() !== '' ? value : undefined;
}
function parseUrl(value) {
    if (!value)
        return undefined;
    try {
        // eslint-disable-next-line no-new
        new URL(value);
        return value;
    }
    catch {
        return undefined;
    }
}
/** Parse W3C correlation-context style header list: "k=v,k2=v2". */
function parseHeaderList(value) {
    const headers = {};
    if (!value)
        return headers;
    for (const pair of value.split(',')) {
        const idx = pair.indexOf('=');
        if (idx <= 0)
            continue;
        const key = pair.slice(0, idx).trim();
        const val = pair.slice(idx + 1).trim();
        if (key)
            headers[key] = val;
    }
    return headers;
}
/**
 * Resolve telemetry settings into one of three modes (SRS §6.3):
 *   1. VSAF_TELEMETRY=off              → disabled
 *   2. env OTEL_EXPORTER_OTLP_*        → otlp (traces + metrics)
 *   3. config telemetry.otlp.endpoint  → otlp (traces + metrics)
 *   4. legacy telemetry.langfuse (full)→ legacy-langfuse (traces only, Basic auth)
 *   5. otherwise                       → disabled
 */
function resolveTelemetryConfig(config, env = process.env) {
    const file = config.telemetry;
    if ((env.VSAF_TELEMETRY ?? '').toLowerCase() === 'off') {
        return { mode: 'disabled', enabled: false };
    }
    // Tier 1: OTLP — signal-specific env endpoints verbatim; generic endpoint gets /v1/{signal}.
    const envTraces = parseUrl(nonEmpty(env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT));
    const envMetrics = parseUrl(nonEmpty(env.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT));
    const genericEndpoint = parseUrl(nonEmpty(env.OTEL_EXPORTER_OTLP_ENDPOINT) ?? nonEmpty(file?.otlp?.endpoint));
    const base = genericEndpoint ? stripTrailingSlashes(genericEndpoint) : undefined;
    const tracesUrl = envTraces ?? (base ? `${base}/v1/traces` : undefined);
    if (tracesUrl) {
        const headers = {
            ...(file?.otlp?.headers ?? {}),
            ...parseHeaderList(env.OTEL_EXPORTER_OTLP_HEADERS),
        };
        return {
            mode: 'otlp',
            otlp: {
                tracesUrl,
                metricsUrl: envMetrics ?? (base ? `${base}/v1/metrics` : undefined),
                headers,
            },
            enabled: true,
        };
    }
    // Tier 2: legacy Langfuse credentials auto-map to its OTLP traces endpoint (no metrics).
    const host = parseUrl(nonEmpty(env.LANGFUSE_HOST) ?? nonEmpty(file?.langfuse?.host));
    const publicKey = nonEmpty(env.LANGFUSE_PUBLIC_KEY) ?? nonEmpty(file?.langfuse?.public_key);
    const secretKey = nonEmpty(env.LANGFUSE_SECRET_KEY) ?? nonEmpty(file?.langfuse?.secret_key);
    if (host && publicKey && secretKey) {
        const auth = Buffer.from(`${publicKey}:${secretKey}`).toString('base64');
        return {
            mode: 'legacy-langfuse',
            otlp: {
                tracesUrl: `${stripTrailingSlashes(host)}/api/public/otel/v1/traces`,
                headers: { Authorization: `Basic ${auth}` },
            },
            enabled: true,
            langfuse: { host, publicKey, secretKey },
        };
    }
    return { mode: 'disabled', enabled: false };
}
//# sourceMappingURL=config.js.map