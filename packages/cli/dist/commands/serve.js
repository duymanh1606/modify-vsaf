"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execServe = execServe;
const app_js_1 = require("../server/app.js");
const static_js_1 = require("../server/static.js");
async function execServe(projectPath, options) {
    const app = (0, app_js_1.buildApp)({ projectPath });
    const hasUI = await (0, static_js_1.registerStatic)(app);
    await app.listen({ port: options.port, host: '0.0.0.0' });
    console.log(`[vsaf] Server running on http://localhost:${options.port}`);
    console.log(`[vsaf] API: http://localhost:${options.port}/api`);
    if (hasUI) {
        console.log(`[vsaf] Dashboard: http://localhost:${options.port}`);
    }
    else {
        console.log(`[vsaf] Warning: Web UI not built. Run "npm run build -w packages/web" first.`);
        console.log(`[vsaf] API available at http://localhost:${options.port}/api`);
    }
    console.log(`[vsaf] Press Ctrl+C to stop`);
    if (options.open && hasUI) {
        const { exec } = await import('child_process');
        const url = `http://localhost:${options.port}`;
        const cmd = process.platform === 'darwin' ? `open ${url}` :
            process.platform === 'win32' ? `start ${url}` : `xdg-open ${url}`;
        exec(cmd);
    }
}
//# sourceMappingURL=serve.js.map