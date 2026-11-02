"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.healthRoutes = healthRoutes;
async function healthRoutes(app) {
    app.get('/health', async () => {
        return {
            status: 'ok',
            version: '0.2.0',
            timestamp: new Date().toISOString(),
        };
    });
}
//# sourceMappingURL=health.js.map