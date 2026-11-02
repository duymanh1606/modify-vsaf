import type { VSAFConfig } from '@vsaf/core';
export type TelemetryMode = 'disabled' | 'otlp' | 'legacy-langfuse';
export interface OtlpSettings {
    tracesUrl: string;
    /** Absent in legacy-langfuse mode — Langfuse's OTLP endpoint rejects metrics. */
    metricsUrl?: string;
    headers: Record<string, string>;
}
/** @deprecated Transitional — removed with the Langfuse tracer cutover. */
export interface LangfuseSettings {
    host: string;
    publicKey: string;
    secretKey: string;
}
export interface ResolvedTelemetryConfig {
    mode: TelemetryMode;
    otlp?: OtlpSettings;
    /** @deprecated Use `mode !== 'disabled'`. Kept while doctor/index migrate. */
    enabled: boolean;
    /** @deprecated Raw legacy credentials, used by doctor's key-prefix check. */
    langfuse?: LangfuseSettings;
}
/**
 * Resolve telemetry settings into one of three modes (SRS §6.3):
 *   1. VSAF_TELEMETRY=off              → disabled
 *   2. env OTEL_EXPORTER_OTLP_*        → otlp (traces + metrics)
 *   3. config telemetry.otlp.endpoint  → otlp (traces + metrics)
 *   4. legacy telemetry.langfuse (full)→ legacy-langfuse (traces only, Basic auth)
 *   5. otherwise                       → disabled
 */
export declare function resolveTelemetryConfig(config: VSAFConfig, env?: NodeJS.ProcessEnv): ResolvedTelemetryConfig;
//# sourceMappingURL=config.d.ts.map