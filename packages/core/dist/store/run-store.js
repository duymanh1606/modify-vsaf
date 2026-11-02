"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RunStore = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const crypto_1 = require("crypto");
const event_log_js_1 = require("./event-log.js");
class RunStore {
    baseDir;
    runs = new Map();
    logs = new Map();
    constructor(baseDir) {
        this.baseDir = baseDir;
        (0, fs_1.mkdirSync)(baseDir, { recursive: true });
    }
    create(workflow, args, workspacePath, artifactsPath, projectPath) {
        const runId = `run-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
        const run = {
            runId, workflow, status: 'running', args,
            workspacePath, artifactsPath, projectPath,
            startedAt: new Date().toISOString(), nodes: {},
        };
        this.runs.set(runId, run);
        this.persist(run);
        this.getLog(runId).append({ type: 'run:create', data: { workflow, args } });
        return run;
    }
    updateNode(runId, nodeId, result) {
        const run = this.getRun(runId);
        run.nodes[nodeId] = { ...run.nodes[nodeId], ...result };
        if (result.status) {
            const eventType = this.statusToEventType(result.status);
            if (eventType) {
                this.getLog(runId).append({
                    type: eventType,
                    nodeId,
                    data: result.error ? { error: result.error } : undefined,
                });
            }
        }
    }
    save(runId) { this.persist(this.getRun(runId)); }
    complete(runId) {
        const run = this.getRun(runId);
        run.status = 'completed';
        run.completedAt = new Date().toISOString();
        this.persist(run);
        this.getLog(runId).append({ type: 'run:complete' });
    }
    fail(runId) {
        const run = this.getRun(runId);
        run.status = 'failed';
        run.completedAt = new Date().toISOString();
        this.persist(run);
        this.getLog(runId).append({ type: 'run:fail' });
    }
    /**
     * The run stopped at a gate a person clears — not a failure. Kept separate from `fail`
     * so a workflow waiting for a signature is not filed next to one that broke.
     */
    pause(runId) {
        const run = this.getRun(runId);
        run.status = 'paused';
        run.completedAt = new Date().toISOString();
        this.persist(run);
        this.getLog(runId).append({ type: 'run:pause' });
    }
    /**
     * Put a terminated run back in flight — used when a run that stopped at a HITL gate is
     * resumed after the human signed. The node results stay; only the run's own verdict is
     * cleared, so whatever happens next decides it afresh.
     */
    resume(runId) {
        const run = this.getRun(runId);
        run.status = 'running';
        delete run.completedAt;
        this.persist(run);
        this.getLog(runId).append({ type: 'run:resume' });
    }
    load(runId) {
        if (this.runs.has(runId))
            return this.runs.get(runId);
        const filePath = (0, path_1.join)(this.baseDir, runId, 'state.json');
        if (!(0, fs_1.existsSync)(filePath))
            return undefined;
        const run = JSON.parse((0, fs_1.readFileSync)(filePath, 'utf-8'));
        this.runs.set(runId, run);
        return run;
    }
    listAll() {
        const runs = [];
        if (!(0, fs_1.existsSync)(this.baseDir))
            return runs;
        for (const dir of (0, fs_1.readdirSync)(this.baseDir)) {
            const run = this.load(dir);
            if (run)
                runs.push(run);
        }
        return runs;
    }
    getEvents(runId) {
        return this.getLog(runId).readAll();
    }
    getLog(runId) {
        let log = this.logs.get(runId);
        if (!log) {
            const runDir = (0, path_1.join)(this.baseDir, runId);
            (0, fs_1.mkdirSync)(runDir, { recursive: true });
            log = new event_log_js_1.EventLog(runDir);
            this.logs.set(runId, log);
        }
        return log;
    }
    getRun(runId) {
        const run = this.runs.get(runId);
        if (!run)
            throw new Error(`Run not found: ${runId}`);
        return run;
    }
    persist(run) {
        const runDir = (0, path_1.join)(this.baseDir, run.runId);
        (0, fs_1.mkdirSync)(runDir, { recursive: true });
        (0, fs_1.writeFileSync)((0, path_1.join)(runDir, 'state.json'), JSON.stringify(run, null, 2), 'utf-8');
    }
    statusToEventType(status) {
        switch (status) {
            case 'running': return 'node:start';
            case 'completed': return 'node:complete';
            case 'failed': return 'node:fail';
            case 'skipped': return 'node:skip';
            default: return null;
        }
    }
}
exports.RunStore = RunStore;
//# sourceMappingURL=run-store.js.map