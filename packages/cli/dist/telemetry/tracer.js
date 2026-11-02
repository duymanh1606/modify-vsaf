"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.NoopTracer = void 0;
class NoopTracer {
    startRun() { }
    nodeStart() { }
    nodeComplete() { }
    nodeFail() { }
    nodeSkip() { }
    attachOutputMetrics() { }
    attachDriftScores() { }
    async endRun() { }
}
exports.NoopTracer = NoopTracer;
//# sourceMappingURL=tracer.js.map