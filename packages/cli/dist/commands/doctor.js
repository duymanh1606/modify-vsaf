"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.MissingOtelModules = MissingOtelModules;
exports.countWorkflows = countWorkflows;
exports.runChecks = runChecks;
exports.formatChecks = formatChecks;
const child_process_1 = require("child_process");
const util_1 = require("util");
const fs_1 = require("fs");
const path_1 = require("path");
const core_1 = require("@vsaf/core");
const config_js_1 = require("../telemetry/config.js");
const python_js_1 = require("./install/python.js");
const exec = (0, util_1.promisify)(child_process_1.execFile);
/** The OTel packages otel-sdk.ts requires lazily; all are needed to emit traces. */
const OTEL_MODULES = [
    '@opentelemetry/api',
    '@opentelemetry/sdk-trace-base',
    '@opentelemetry/exporter-trace-otlp-proto',
    '@opentelemetry/resources',
    '@opentelemetry/semantic-conventions',
];
/** Which of those cannot be resolved from here. Empty means telemetry can load. */
function MissingOtelModules(modules = OTEL_MODULES) {
    return modules.filter((name) => {
        try {
            // eslint-disable-next-line @typescript-eslint/no-var-requires
            require.resolve(name);
            return false;
        }
        catch {
            return true;
        }
    });
}
/**
 * POST an empty batch to an OTLP endpoint. An empty protobuf body is a valid
 * (empty) Export*ServiceRequest, so any non-auth HTTP response proves the
 * endpoint is reachable; 401/403 isolates bad credentials (FR-08).
 */
async function defaultProbe(url, headers) {
    try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3_000);
        const response = await fetch(url, {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/x-protobuf' },
            body: new Uint8Array(0),
            signal: controller.signal,
        });
        clearTimeout(timer);
        return response.status === 401 || response.status === 403 ? 'auth' : 'ok';
    }
    catch {
        return 'unreachable';
    }
}
/**
 * Count workflows one level deep as well: installing a pack puts its workflows in
 * `.vsaf/workflows/<pack>/`, so counting only the top level reports zero for a
 * project that in fact has plenty.
 */
function countWorkflows(dir) {
    if (!(0, fs_1.existsSync)(dir))
        return 0;
    return (0, fs_1.readdirSync)(dir, { withFileTypes: true }).reduce((total, entry) => {
        if (entry.isDirectory()) {
            return total + (0, fs_1.readdirSync)((0, path_1.join)(dir, entry.name)).filter(f => f.endsWith('.yaml')).length;
        }
        return total + (entry.name.endsWith('.yaml') ? 1 : 0);
    }, 0);
}
async function checkBinary(name, args) {
    try {
        const { stdout } = await run(name, args);
        const version = stdout.trim().match(/[\d.]+/)?.[0] ?? 'unknown';
        return { name, ok: true, version };
    }
    catch {
        return { name, ok: false, message: 'not found' };
    }
}
/**
 * Run a tool by name, including the ones Windows only has under another extension.
 *
 * `execFile` hands the name to CreateProcess, which appends `.exe` and nothing else — so
 * a tool installed by npm, which puts a `claude.cmd` and a `claude.ps1` on PATH and no
 * `claude`, comes back ENOENT and `doctor` reports "not found" for something the user can
 * run in the same shell. cmd.exe does read PATHEXT, so a second attempt through it finds
 * what the first could not. Only on Windows, and only for names written here — the args
 * are literals in this file, so there is nothing for a shell to interpret.
 */
async function run(name, args) {
    try {
        return await exec(name, args);
    }
    catch (error) {
        if (process.platform !== 'win32')
            throw error;
        return await exec(name, args, { shell: true });
    }
}
async function runChecks(projectPath, options = {}) {
    const results = [];
    results.push({ name: 'Node.js', ok: true, version: process.version.replace('v', '') });
    results.push(await checkBinary('claude', ['--version']));
    results.push(await checkBinary('gh', ['--version']));
    results.push(await checkBinary('git', ['--version']));
    // Not a plain binary check: the interpreter answers to three different names
    // depending on the platform, and only version 3 can run pack hooks.
    results.push((0, python_js_1.checkPython)());
    const vsafDir = (0, path_1.join)(projectPath, '.vsaf');
    if ((0, fs_1.existsSync)(vsafDir)) {
        const workflows = countWorkflows((0, path_1.join)(vsafDir, 'workflows'));
        const commands = (0, fs_1.existsSync)((0, path_1.join)(vsafDir, 'commands'))
            ? (0, fs_1.readdirSync)((0, path_1.join)(vsafDir, 'commands')).filter(f => f.endsWith('.md')).length
            : 0;
        results.push({ name: '.vsaf/', ok: true, message: `${workflows} workflows, ${commands} commands` });
    }
    else {
        results.push({ name: '.vsaf/', ok: false, message: 'not found — run "vsaf init"' });
    }
    results.push(await checkTelemetry(projectPath, options.probe ?? defaultProbe));
    return results;
}
async function checkTelemetry(projectPath, probe) {
    const config = (0, core_1.loadConfig)(projectPath);
    const telemetry = (0, config_js_1.resolveTelemetryConfig)(config);
    // A project that records nothing used to get a green tick, which is the one answer
    // this check must not give: the whole point of asking is to find the runs nobody can
    // trace afterwards, and `install` now turns recording on by itself — so an off project
    // is a project something went wrong in, not a project someone chose.
    if (telemetry.mode === 'disabled' || !telemetry.otlp) {
        const forcedOff = (process.env.VSAF_TELEMETRY ?? '').toLowerCase() === 'off';
        return {
            name: 'telemetry',
            ok: false,
            message: forcedOff
                ? 'tắt bằng VSAF_TELEMETRY=off — mọi run của project này không để lại dấu nào'
                : 'chưa bật — mọi run chạy im lặng. Chạy: vsaf init',
        };
    }
    // The OTel SDK is required lazily at first span, so a packaging mistake that
    // leaves it out of the published tarball surfaces nowhere: every span throws,
    // the tracer swallows it, and this check still probed the endpoint happily and
    // reported green for a telemetry pipe that could not emit a single byte.
    const missing = MissingOtelModules();
    if (missing.length > 0) {
        return {
            name: 'telemetry',
            ok: false,
            message: `OTel SDK not installed (${missing.join(', ')}) — telemetry is configured but cannot emit. `
                + 'Reinstall vsaf; if it persists the published package is missing these dependencies.',
        };
    }
    if (telemetry.mode === 'legacy-langfuse') {
        // Langfuse rejects swapped credentials with a silent 401, so catch the
        // classic pk/sk mix-up here where the user can actually see it.
        const { publicKey, secretKey } = telemetry.langfuse;
        if (publicKey.startsWith('sk-') || secretKey.startsWith('pk-')) {
            return {
                name: 'telemetry',
                ok: false,
                message: 'Langfuse keys look swapped — public_key must start with pk-lf-, secret_key with sk-lf-',
            };
        }
    }
    const { tracesUrl, metricsUrl, headers } = telemetry.otlp;
    const tracesResult = await probe(tracesUrl, headers);
    if (tracesResult === 'unreachable') {
        return { name: 'telemetry', ok: false, message: `OTLP traces endpoint unreachable (${tracesUrl})` };
    }
    if (tracesResult === 'auth') {
        return { name: 'telemetry', ok: false, message: `OTLP auth rejected (${tracesUrl}) — check credentials` };
    }
    // Δ11: in full otlp mode the metrics endpoint can be broken independently.
    if (metricsUrl) {
        const metricsResult = await probe(metricsUrl, headers);
        if (metricsResult !== 'ok')
            return { name: 'telemetry', ok: false, message: `OTLP metrics endpoint ${metricsResult === 'auth' ? 'auth rejected' : 'unreachable'} (${metricsUrl})` };
    }
    // Nothing but the verdict on success: the endpoint url, which probe answered, and the
    // fact that a legacy `telemetry.langfuse` block was auto-mapped are all things that
    // need no action when the answer is "healthy". Failures above keep their detail —
    // there the detail is the fix.
    return { name: 'telemetry', ok: true, message: 'OTLP configured' };
}
function formatChecks(results) {
    const lines = results.map(r => {
        const icon = r.ok ? '✓' : '✗';
        const detail = r.version ?? r.message ?? '';
        return `${icon} ${r.name.padEnd(12)} ${detail}`;
    });
    return `VSAF Doctor v0.1.0\n${'─'.repeat(30)}\n${lines.join('\n')}`;
}
//# sourceMappingURL=doctor.js.map