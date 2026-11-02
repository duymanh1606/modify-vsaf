"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.runRoutes = runRoutes;
const path_1 = require("path");
const core_1 = require("@vsaf/core");
async function runRoutes(app, opts) {
    const storeDir = (0, path_1.join)(opts.projectPath, '.vsaf', 'storage');
    app.get('/runs', async () => {
        const store = new core_1.RunStore(storeDir);
        return store.listAll().map(r => ({
            runId: r.runId,
            workflow: r.workflow,
            status: r.status,
            startedAt: r.startedAt,
            completedAt: r.completedAt,
        }));
    });
    app.get('/runs/:runId', async (request, reply) => {
        const store = new core_1.RunStore(storeDir);
        const run = store.load(request.params.runId);
        if (!run) {
            return reply.status(404).send({ error: `Run not found: ${request.params.runId}` });
        }
        return run;
    });
    app.post('/runs', async (request, reply) => {
        const { workflow, args } = request.body;
        try {
            const { runId } = await opts.executionManager.startRun(workflow, args ?? '');
            return reply.status(202).send({ runId });
        }
        catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            if (message.includes('not found')) {
                return reply.status(404).send({ error: message });
            }
            return reply.status(500).send({ error: message });
        }
    });
    app.get('/runs/:runId/events', async (request, reply) => {
        reply.hijack();
        reply.raw.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        });
        reply.raw.write(':connected\n\n');
        opts.sseManager.addClient(request.params.runId, reply);
        // Send current state as initial event
        const store = new core_1.RunStore(storeDir);
        const run = store.load(request.params.runId);
        if (run) {
            reply.raw.write(`event: run:state\ndata: ${JSON.stringify(run)}\n\n`);
        }
    });
}
//# sourceMappingURL=runs.js.map