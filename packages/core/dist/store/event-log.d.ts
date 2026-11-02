import type { WorkflowEvent } from './types.js';
export declare class EventLog {
    private readonly filePath;
    constructor(runDir: string);
    append(event: Omit<WorkflowEvent, 'timestamp'>): void;
    readAll(): WorkflowEvent[];
}
//# sourceMappingURL=event-log.d.ts.map