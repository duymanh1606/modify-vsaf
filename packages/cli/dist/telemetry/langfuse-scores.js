"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createLangfuseScoreClient = createLangfuseScoreClient;
const crypto_1 = require("crypto");
/** Deterministic score id: re-emitted metrics overwrite instead of duplicating. */
function scoreId(input) {
    return (0, crypto_1.createHash)('sha1')
        .update(`${input.traceId ?? ''}:${input.observationId ?? 'run'}:${input.name}`)
        .digest('hex');
}
function createLangfuseScoreClient(cfg) {
    const base = cfg.host.replace(/\/+$/, '');
    const auth = 'Basic ' + Buffer.from(`${cfg.publicKey}:${cfg.secretKey}`).toString('base64');
    const headers = { Authorization: auth, 'Content-Type': 'application/json' };
    return {
        async postScore(input) {
            try {
                await fetch(`${base}/api/public/scores`, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify(input),
                    signal: AbortSignal.timeout(5_000),
                });
            }
            catch {
                /* Telemetry must never break a run. */
            }
        },
        async postScores(inputs) {
            if (inputs.length === 0)
                return;
            try {
                const timestamp = new Date().toISOString();
                await fetch(`${base}/api/public/ingestion`, {
                    method: 'POST',
                    headers,
                    body: JSON.stringify({
                        batch: inputs.map((input) => ({
                            id: (0, crypto_1.randomUUID)(), // event id: unique per attempt (ingestion dedup)
                            type: 'score-create',
                            timestamp,
                            body: { id: scoreId(input), ...input },
                        })),
                    }),
                    signal: AbortSignal.timeout(5_000),
                });
            }
            catch {
                /* Telemetry must never break a run. */
            }
        },
    };
}
//# sourceMappingURL=langfuse-scores.js.map