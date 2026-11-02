import type { FastifyInstance } from 'fastify';
import { ExecutionManager } from '../services/execution-manager.js';
import { SseManager } from '../services/sse-manager.js';
export declare function runRoutes(app: FastifyInstance, opts: {
    projectPath: string;
    executionManager: ExecutionManager;
    sseManager: SseManager;
}): Promise<void>;
//# sourceMappingURL=runs.d.ts.map