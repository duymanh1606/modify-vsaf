"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.GATEWAY_ENV_ENABLED = void 0;
exports.writeProjectConfig = writeProjectConfig;
exports.hasGatewayToken = hasGatewayToken;
exports.execInit = execInit;
const fs_1 = require("fs");
const path_1 = require("path");
const js_yaml_1 = __importDefault(require("js-yaml"));
const sdlc_docs_js_1 = require("./init/sdlc-docs.js");
const session_hook_js_1 = require("./install/session-hook.js");
const DEFAULT_CONFIG = `provider: claude
model: sonnet

# Test command for this project — used by test-gate nodes as $CONFIG.test_command.
# Detected and written by /sdlc-onboard-code, or set manually:
# test_command: npm test

isolation:
  type: ephemeral
  cleanup: after_success
  exclude:
    - node_modules
    - .git
    - dist
    - build
    - .vsaf/storage
  max_workspaces: 5
`;
/**
 * Telemetry defaults packed with the CLI at the package root. When present,
 * `vsaf init` writes them into the new project's config.yaml so runs emit
 * telemetry out of the box: OTLP endpoint/headers, or legacy Langfuse
 * credentials (VSAF_TELEMETRY_DEFAULTS overrides path).
 *
 * These are the engine's own defaults, and they are all `init` writes. Which paths a
 * flow counts as deliverables is the flow's own declaration, so `vsaf install` tops the
 * section up once it knows which flow is being installed.
 */
const TELEMETRY_DEFAULTS_FILE = 'telemetry.defaults.json';
/** The AI gateway every initialized project routes Claude Code through. */
const GATEWAY_BASE_URL = 'https://ai-gateway.viettel.digital';
function readJsonIfExists(path) {
    if (!(0, fs_1.existsSync)(path))
        return undefined;
    try {
        return JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        return undefined;
    }
}
function loadPackedDefaults(env = process.env) {
    // Package root is 4 levels up from packages/cli/{src,dist}/commands — the
    // same convention as skill.ts findPackageRoot().
    const root = (0, path_1.resolve)(__dirname, '..', '..', '..', '..');
    const telemetry = readJsonIfExists(env.VSAF_TELEMETRY_DEFAULTS ?? (0, path_1.join)(root, TELEMETRY_DEFAULTS_FILE));
    return { otlp: telemetry?.otlp, langfuse: telemetry?.langfuse };
}
/**
 * Write `.vsaf/config.yaml`, or top up one that is already there.
 *
 * The old behaviour was all-or-nothing: an existing file was left completely
 * alone, so any project whose config predates telemetry — or was written by
 * hand, or scaffolded by something other than `vsaf init` — could never acquire
 * the section, not even with `--force`. Telemetry stayed off forever with no
 * hint as to why.
 *
 * Appending is the whole change. The file belongs to the user (they keep notes
 * in it), so existing bytes are never rewritten or reordered, and a file that
 * does not parse is left untouched rather than guessed at.
 */
function writeProjectConfig(configPath, artifacts) {
    if (!(0, fs_1.existsSync)(configPath)) {
        (0, fs_1.writeFileSync)(configPath, DEFAULT_CONFIG + renderTelemetrySection(loadPackedDefaults(), artifacts), 'utf-8');
        return;
    }
    const current = (0, fs_1.readFileSync)(configPath, 'utf-8');
    let parsed;
    try {
        parsed = js_yaml_1.default.load(current);
    }
    catch (error) {
        const reason = error instanceof Error ? error.message.split('\n')[0] : String(error);
        console.warn(`[vsaf] ${configPath} is not valid YAML (${reason}) — left untouched, telemetry section not added.`);
        return;
    }
    // Parsing rather than grepping for `telemetry:` on purpose: hand-written configs
    // carry long comment blocks, and a commented-out mention would fool a text scan
    // into skipping a project that genuinely has no telemetry configured.
    if (parsed && Object.prototype.hasOwnProperty.call(parsed, 'telemetry')) {
        addArtifactsToExisting(configPath, current, parsed, artifacts);
        return;
    }
    const separator = current.endsWith('\n') ? '' : '\n';
    (0, fs_1.writeFileSync)(configPath, current + separator + renderTelemetrySection(loadPackedDefaults(), artifacts), 'utf-8');
}
/**
 * Give a config that already has `telemetry:` the artifact paths its pack declares.
 *
 * Every project installed before the pack declared them has the section already, so
 * skipping here would leave the fix reaching new projects only — and the symptom
 * (`artifacts_created: 0` on every span, while the generic file count looks right)
 * gives no hint that a sub-key is missing.
 *
 * The insertion point is the line right after `telemetry:`, because `artifacts` is a
 * direct child of it and any existing children are siblings that follow. Existing
 * bytes are never rewritten — the user keeps notes in this file.
 */
function addArtifactsToExisting(configPath, current, parsed, artifacts) {
    if (!hasAnyArtifactPath(artifacts))
        return;
    const telemetry = parsed.telemetry;
    if (telemetry && typeof telemetry === 'object' && 'artifacts' in telemetry)
        return;
    const lines = current.split('\n');
    const anchor = lines.findIndex(line => line.trimEnd() === 'telemetry:');
    if (anchor === -1) {
        // `telemetry: {…}` on one line, or a value where a mapping was expected. Editing
        // that safely means rewriting the user's line, so say what is missing instead.
        console.warn(`[vsaf] ${configPath}: telemetry is not a block mapping — add ` +
            `telemetry.artifacts.include: ${JSON.stringify(artifacts?.include ?? [])} by hand, ` +
            `otherwise output metrics report 0 artifacts.`);
        return;
    }
    lines.splice(anchor + 1, 0, renderArtifacts(artifacts).replace(/\n$/, ''));
    (0, fs_1.writeFileSync)(configPath, lines.join('\n'), 'utf-8');
}
const SECRET_HEADER_KEY = /^authorization$|-api-key$/i;
const SECRET_HEADER_VALUE = /^(Basic|Bearer)\s|^(sk|pk)-/;
/**
 * Commented-out artifact prefixes, written when the pack declares none. The default
 * (`.vsaf/docs/`) is right for the sdlc layout, and leaving the block visible is also
 * how the option gets discovered at all.
 */
const ARTIFACTS_HINT = `  # Which paths the output metrics count. Defaults shown.
  # artifacts:
  #   include: [".vsaf/docs/"]     # created files here count as artifacts
  #   exclude: []                  # never counted; added to the engine's own list
  #   code_roots: []               # extra repos to measure, for a project whose code
  #                                # lives outside this repo. Empty reads the repos
  #                                # listed in the workspace file.
`;
function hasAnyArtifactPath(artifacts) {
    return Boolean(artifacts &&
        (artifacts.include?.length || artifacts.exclude?.length || artifacts.code_roots?.length));
}
/**
 * The `artifacts` block for a pack that declares where it writes — real YAML, not the
 * commented hint. A pack knows its own output tree; leaving the project to uncomment
 * the default meant nobody ever did, and NTAPP (which writes to `NTAPP-output/`) scored
 * zero artifacts on every run.
 */
function renderArtifacts(artifacts) {
    if (!hasAnyArtifactPath(artifacts))
        return ARTIFACTS_HINT;
    const lines = ['  # Which paths the output metrics count — declared by this project\'s pack.', '  artifacts:'];
    const entry = (key, values) => {
        if (!values?.length)
            return;
        lines.push(`    ${key}: [${values.map(value => JSON.stringify(value)).join(', ')}]`);
    };
    entry('include', artifacts.include);
    entry('exclude', artifacts.exclude);
    entry('code_roots', artifacts.code_roots);
    return lines.join('\n') + '\n';
}
function renderTelemetrySection(defaults, artifacts) {
    // Always write the full telemetry structure so users can fill it in later.
    // Empty values are written as "" — the run paths fall back to NoopTracer,
    // so vsaf behaves as if the section were absent (UC-OTL-09).
    const val = (raw) => raw?.trim() || '""';
    // ALT1: legacy-only defaults keep producing a langfuse section — it is
    // auto-mapped to the Langfuse OTLP endpoint at runtime (deprecated).
    if (!defaults.otlp?.endpoint?.trim() && defaults.langfuse) {
        return `
# Telemetry — every run emits an OpenTelemetry trace (one span per node).
# DEPRECATED: langfuse credentials are auto-mapped to Langfuse's OTLP
# endpoint (traces only). Prefer telemetry.otlp — see README "Telemetry".
# VSAF_TELEMETRY=off force-disables.
telemetry:
  langfuse:
    host: ${val(defaults.langfuse.host)}
    public_key: ${val(defaults.langfuse.public_key)}
    secret_key: ${val(defaults.langfuse.secret_key)}
${renderArtifacts(artifacts)}`;
    }
    // Secret-looking headers stay out of the committable config.yaml — pass
    // them via OTEL_EXPORTER_OTLP_HEADERS or the gitignored defaults file.
    const safeHeaders = Object.entries(defaults.otlp?.headers ?? {}).filter(([key, value]) => !SECRET_HEADER_KEY.test(key) && !SECRET_HEADER_VALUE.test(value));
    const headersBlock = safeHeaders.length > 0
        ? `    headers:\n${safeHeaders.map(([k, v]) => `      ${k}: ${v}`).join('\n')}\n`
        : '';
    return `
# Telemetry — every run emits an OpenTelemetry trace (one span per node) and
# run-total metrics over OTLP http/protobuf. Set endpoint to enable, e.g.
# http://otel-collector:4318. Env OTEL_EXPORTER_OTLP_* overrides these;
# VSAF_TELEMETRY=off force-disables. Auth headers: prefer the env var
# OTEL_EXPORTER_OTLP_HEADERS over committing secrets here.
telemetry:
  otlp:
    endpoint: ${val(defaults.otlp?.endpoint)}
${headersBlock}${renderArtifacts(artifacts)}`;
}
/**
 * TEMPORARILY DISABLED (2026-07-23): during scaffold, `vsaf init` does NOT
 * write the gateway env block (ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN /
 * ANTHROPIC_MODEL) into .claude/settings.json, and no virtual key is required
 * or prompted for. Flip to true to restore key validation, the CLI prompt,
 * and env writes. The SessionStart hook is unaffected either way.
 */
exports.GATEWAY_ENV_ENABLED = false;
/**
 * Reports whether the project's .claude/settings.json already carries a
 * gateway virtual key — in that case `vsaf init` doesn't require a new one.
 */
function hasGatewayToken(projectPath) {
    const settings = readJsonIfExists((0, path_1.join)(projectPath, '.claude', 'settings.json'));
    return Boolean(settings?.env?.ANTHROPIC_AUTH_TOKEN?.trim());
}
/**
 * Wire the project's Claude Code to vsaf via .claude/settings.json: gateway env
 * vars (so a machine with only Claude Code installed — no Anthropic account —
 * works out of the box) and the SessionStart hook above. The base URL is
 * merge-only (never overwrites a value the user already set); the virtual key
 * overwrites, because the user explicitly provided it in this very run. Leaves
 * an unparseable settings.json untouched.
 */
function writeClaudeSettings(projectPath, gatewayKey) {
    const claudeDir = (0, path_1.join)(projectPath, '.claude');
    const settingsPath = (0, path_1.join)(claudeDir, 'settings.json');
    let settings = {};
    if ((0, fs_1.existsSync)(settingsPath)) {
        const parsed = readJsonIfExists(settingsPath);
        if (!parsed)
            return;
        settings = parsed;
    }
    if (exports.GATEWAY_ENV_ENABLED) {
        const env = (settings.env ??= {});
        if (!env.ANTHROPIC_BASE_URL)
            env.ANTHROPIC_BASE_URL = GATEWAY_BASE_URL;
        if (gatewayKey)
            env.ANTHROPIC_AUTH_TOKEN = gatewayKey;
        if (!env.ANTHROPIC_MODEL)
            env.ANTHROPIC_MODEL = '';
    }
    (0, fs_1.mkdirSync)(claudeDir, { recursive: true });
    (0, fs_1.writeFileSync)(settingsPath, JSON.stringify(settings, null, 2) + '\n', 'utf-8');
    // The hook lives in its own module and is put back after every wiring run too — the
    // pack's script drops it. One definition, applied from both places.
    (0, session_hook_js_1.ensureSessionHook)(projectPath);
}
/** Whether `init` has run here before — see the guard in `execInit`. */
function isInitialised(vsafDir) {
    try {
        const parsed = js_yaml_1.default.load((0, fs_1.readFileSync)((0, path_1.join)(vsafDir, 'config.yaml'), 'utf-8'));
        return Boolean(parsed && Object.prototype.hasOwnProperty.call(parsed, 'telemetry'));
    }
    catch {
        // No config, or one that does not parse: not something `init` left behind.
        return false;
    }
}
async function execInit(projectPath, options) {
    const vsafDir = (0, path_1.join)(projectPath, '.vsaf');
    // "Already initialised" is not the same as "`.vsaf/` exists". A pack that ships its
    // own project skeleton (NTAPP) brings `.vsaf/workflows` and a `.vsaf/config.yaml` of
    // its own, so the directory is there before `init` ever runs — and the guard then
    // demanded `--force` for the very first init, on a project nothing had initialised.
    // The documented two-step stopped at an error, which is a good part of why the second
    // step got skipped and telemetry stayed off.
    //
    // The telemetry section is the marker: nothing a user writes by hand starts with it,
    // so its presence means a vsaf command has already configured this project. `install`
    // tops the same section up with the flow's artifact paths, so a caller that knows for
    // certain init has not run here — it read the project before installing — passes
    // `force` rather than reading the marker afterwards.
    if (isInitialised(vsafDir) && !options?.force) {
        throw new Error(`.vsaf/ already initialised at ${projectPath}. Pass --force to reinitialize ` +
            `(keeps docs/, storage/, and config.yaml).`);
    }
    // Validate the key before creating anything — a failed init must leave no
    // partial .vsaf/ behind (reinit requires removing it first).
    const gatewayKey = options?.gatewayKey?.trim();
    if (exports.GATEWAY_ENV_ENABLED && !gatewayKey && !hasGatewayToken(projectPath)) {
        throw new Error('AI Gateway virtual key is required — run "vsaf init --key <key>" or enter it at the prompt.');
    }
    (0, fs_1.mkdirSync)((0, path_1.join)(vsafDir, 'workflows'), { recursive: true });
    (0, fs_1.mkdirSync)((0, path_1.join)(vsafDir, 'commands'), { recursive: true });
    (0, fs_1.mkdirSync)((0, path_1.join)(vsafDir, 'storage'), { recursive: true });
    // The phase skills expect their artifact tree to exist; scaffolding it here keeps
    // a first phase from stopping to ask for a structure the project could not have known about.
    (0, sdlc_docs_js_1.scaffoldSdlcDocs)(projectPath);
    // Mặc định của engine, không của flow nào. Thư mục nào chứa sản phẩm của một lượt
    // chạy là thứ chỉ flow biết, và `init` không còn biết flow nào sắp được cài — nên
    // `vsaf install <flow>` bù phần đó vào đúng lúc nó đọc `pack.yaml`.
    writeProjectConfig((0, path_1.join)(vsafDir, 'config.yaml'));
    writeClaudeSettings(projectPath, gatewayKey);
    // Create .mcp.json for MCP server registration
    const mcpPath = (0, path_1.join)(projectPath, '.mcp.json');
    const vsafServer = { type: 'stdio', command: 'vsaf', args: ['mcp'] };
    const gitnexusServer = { type: 'stdio', command: 'npx', args: ['-y', 'gitnexus@latest', 'mcp'] };
    if (!(0, fs_1.existsSync)(mcpPath)) {
        const mcpConfig = {
            mcpServers: {
                vsaf: vsafServer,
                gitnexus: gitnexusServer,
            },
        };
        (0, fs_1.writeFileSync)(mcpPath, JSON.stringify(mcpConfig, null, 2) + '\n', 'utf-8');
    }
    else {
        // Merge vsaf + gitnexus servers into existing .mcp.json
        const existing = JSON.parse((0, fs_1.readFileSync)(mcpPath, 'utf-8'));
        if (!existing.mcpServers)
            existing.mcpServers = {};
        let changed = false;
        if (!existing.mcpServers.vsaf) {
            existing.mcpServers.vsaf = vsafServer;
            changed = true;
        }
        if (!existing.mcpServers.gitnexus) {
            existing.mcpServers.gitnexus = gitnexusServer;
            changed = true;
        }
        if (changed) {
            (0, fs_1.writeFileSync)(mcpPath, JSON.stringify(existing, null, 2) + '\n', 'utf-8');
        }
    }
}
//# sourceMappingURL=init.js.map