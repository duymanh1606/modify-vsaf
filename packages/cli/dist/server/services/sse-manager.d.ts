import type { FastifyReply } from 'fastify';
export declare class SseManager {
    private clients;
    addClient(runId: string, reply: FastifyReply): void;
    removeClient(runId: string, reply: FastifyReply): void;
    pushEvent(runId: string, event: string, data: Record<string, unknown>): void;
    getClientCount(runId: string): number;
}
//# sourceMappingURL=sse-manager.d.ts.map