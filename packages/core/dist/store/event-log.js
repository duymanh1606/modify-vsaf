"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.EventLog = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
class EventLog {
    filePath;
    constructor(runDir) {
        this.filePath = (0, path_1.join)(runDir, 'events.jsonl');
    }
    append(event) {
        const entry = {
            timestamp: new Date().toISOString(),
            ...event,
        };
        (0, fs_1.appendFileSync)(this.filePath, JSON.stringify(entry) + '\n', 'utf-8');
    }
    readAll() {
        if (!(0, fs_1.existsSync)(this.filePath))
            return [];
        const content = (0, fs_1.readFileSync)(this.filePath, 'utf-8').trim();
        if (!content)
            return [];
        return content
            .split('\n')
            .map(line => JSON.parse(line));
    }
}
exports.EventLog = EventLog;
//# sourceMappingURL=event-log.js.map