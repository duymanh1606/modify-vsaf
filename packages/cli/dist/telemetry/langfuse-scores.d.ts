export interface LangfuseScoreInput {
    traceId?: string;
    observationId?: string;
    name: string;
    value: number;
    comment?: string;
}
export interface LangfuseScoreClient {
    /** POST một score. Nuốt mọi lỗi — telemetry không bao giờ phá run. */
    postScore(input: LangfuseScoreInput): Promise<void>;
    /**
     * POST một batch score trong 1 request (ingestion API). Score id là hash
     * xác định của (traceId, observationId, name) nên re-emit là upsert,
     * không nhân đôi. Nuốt mọi lỗi.
     */
    postScores(inputs: LangfuseScoreInput[]): Promise<void>;
}
export declare function createLangfuseScoreClient(cfg: {
    host: string;
    publicKey: string;
    secretKey: string;
}): LangfuseScoreClient;
//# sourceMappingURL=langfuse-scores.d.ts.map