"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SseManager = void 0;
class SseManager {
    clients = new Map();
    addClient(runId, reply) {
        if (!this.clients.has(runId)) {
            this.clients.set(runId, new Set());
        }
        this.clients.get(runId).add(reply);
        // Remove client on disconnect
        reply.raw.on('close', () => {
            this.removeClient(runId, reply);
        });
    }
    removeClient(runId, reply) {
        const clients = this.clients.get(runId);
        if (clients) {
            clients.delete(reply);
            if (clients.size === 0) {
                this.clients.delete(runId);
            }
        }
    }
    pushEvent(runId, event, data) {
        const clients = this.clients.get(runId);
        if (!clients)
            return;
        const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
        for (const reply of clients) {
            if (!reply.raw.writableEnded) {
                reply.raw.write(message);
            }
        }
    }
    getClientCount(runId) {
        return this.clients.get(runId)?.size ?? 0;
    }
}
exports.SseManager = SseManager;
//# sourceMappingURL=sse-manager.js.map