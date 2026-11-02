import type { OtlpSettings } from './config.js';
export interface SpanLike {
    setAttribute(key: string, value: unknown): void;
    setAttributes(attributes: Record<string, unknown>): void;
    setStatus(status: {
        code: 'ERROR' | 'OK' | 'UNSET';
        message?: string;
    }): void;
    end(endTime?: Date): void;
    spanContext(): {
        spanId: string;
        traceId: string;
    };
}
export interface OtelRuntime {
    startSpan(name: string, opts: {
        startTime: Date;
        attributes?: Record<string, unknown>;
    }, parent?: SpanLike): SpanLike;
    /** No-op when the metrics pipeline is absent (legacy-langfuse mode). */
    addMetric(name: string, value: number, attributes: Record<string, string>): void;
    /** Flushes traces + metrics in parallel under one deadline. Never rejects. */
    flush(timeoutMs: number): Promise<void>;
    /** Never rejects. */
    shutdown(): Promise<void>;
}
interface Flushable {
    forceFlush(): Promise<unknown>;
}
/**
 * One shared deadline for all targets (Δ8): flushing traces and metrics
 * sequentially would double the worst-case wait and break NFR-03 (≤5s).
 */
export declare function buildNeverRejectFlush(targets: Flushable[]): (timeoutMs: number) => Promise<void>;
/**
 * Assemble an OtelRuntime from already-constructed providers. Split from
 * createOtelRuntime so tests can inject an InMemorySpanExporter-backed
 * provider without duplicating the span-wrapping logic. Still lazy: the
 * @opentelemetry/api require happens at call time, not import time.
 */
export declare function assembleRuntime(parts: {
    tracerProvider: {
        getTracer(name: string): unknown;
        forceFlush(): Promise<unknown>;
        shutdown(): Promise<unknown>;
    };
    addMetric?: OtelRuntime['addMetric'];
    extraFlushables?: Flushable[];
    extraShutdownables?: Array<{
        shutdown(): Promise<unknown>;
    }>;
}): OtelRuntime;
export declare function createOtelRuntime(settings: OtlpSettings, opts: {
    nodeCount: number;
    debug: boolean;
}): OtelRuntime;
export {};
//# sourceMappingURL=otel-sdk.d.ts.map