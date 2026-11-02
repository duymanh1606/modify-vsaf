"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.builtInPacks = builtInPacks;
exports.resolvePackName = resolvePackName;
exports.resolvePackInfo = resolvePackInfo;
exports.readPackInfoFrom = readPackInfoFrom;
exports.skillList = skillList;
exports.skillInfo = skillInfo;
exports.skillRemove = skillRemove;
exports.skillAdd = skillAdd;
exports.renderCommandFile = renderCommandFile;
exports.scaffoldWorkflowCommands = scaffoldWorkflowCommands;
exports.skillInit = skillInit;
exports.findPackageRoot = findPackageRoot;
exports.resolveSource = resolveSource;
// packages/cli/src/commands/skill.ts
const fs_1 = require("fs");
const path_1 = require("path");
const child_process_1 = require("child_process");
const os_1 = require("os");
const gray_matter_1 = __importDefault(require("gray-matter"));
const js_yaml_1 = __importDefault(require("js-yaml"));
// `flow-home.ts` chứ không phải `flow-source.ts`: cái sau import file này, nên import
// ngược lại là một vòng import. `flow-home` chỉ đọc đĩa và không import gì của cli.
const flow_home_js_1 = require("./install/flow-home.js");
// ── Pack Resolution ──
/** Pack directories shipped with this package. */
function builtInPacks() {
    try {
        return (0, fs_1.readdirSync)((0, path_1.join)(findPackageRoot(), 'skills'), { withFileTypes: true })
            .filter(entry => entry.isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(findPackageRoot(), 'skills', entry.name, 'pack.yaml')))
            .map(entry => entry.name)
            .sort();
    }
    catch {
        return [];
    }
}
/**
 * The pack's real name, from a name typed in any casing.
 *
 * A pack directory is `NTAPP` but nobody types it that way, and on a case-sensitive
 * filesystem `ntapp` simply does not exist. Resolving here means the rest of the code
 * — the `NTAPP-` prefix on every skill, the install record, the workflow directory —
 * still works from the one canonical spelling.
 *
 * Reads the flow cache as well as the packs shipped in the npm package. The npm list on
 * its own answers for four names and no more, so a flow that lives only on the flows repo
 * kept whatever casing was typed — and after step 7.0, when `skills/` leaves the npm
 * package, that list is empty and this function corrects nothing at all. Cache first: it
 * is the fresher of the two, and it is the one that grows.
 *
 * Neither side is read over the network. A name that matches nothing is handed back
 * unchanged, and the fetch a moment later reports it with the list of flows the repo has —
 * the more useful list of the two.
 */
function resolvePackName(input) {
    const wanted = input.toLowerCase();
    const known = [...(0, flow_home_js_1.cachedFlowNames)(), ...builtInPacks()];
    return known.find(name => name.toLowerCase() === wanted) ?? input;
}
function resolvePackInfo(input, projectPath) {
    const packName = resolvePackName(input);
    // 1. Try built-in pack at {packageRoot}/skills/{packName}/
    const builtInDir = (0, path_1.join)(findPackageRoot(), 'skills', packName);
    const builtInPackYaml = (0, path_1.join)(builtInDir, 'pack.yaml');
    if ((0, fs_1.existsSync)(builtInPackYaml)) {
        return readPackInfo(builtInDir, builtInPackYaml);
    }
    // 2. Try installed pack.yaml at .claude/skills/{packName}/pack.yaml
    const installedPackYaml = (0, path_1.join)(projectPath, '.claude', 'skills', packName, 'pack.yaml');
    if ((0, fs_1.existsSync)(installedPackYaml)) {
        return readPackInfo((0, path_1.join)(projectPath, '.claude', 'skills', packName), installedPackYaml);
    }
    const available = builtInPacks();
    throw new Error(`Pack "${packName}" not found.`
        + `${available.length > 0 ? ` Available: ${available.join(', ')}` : ''}`);
}
/**
 * Read a pack straight from a directory.
 *
 * For tests that need a pack shape no shipped pack has: every pack in `skills/` now
 * hands its wiring to its own script, which leaves the installer's own wiring — hooks,
 * rules, the gitignore policy, the per-repo config — with nothing exercising it.
 */
function readPackInfoFrom(packDir) {
    return readPackInfo(packDir, (0, path_1.join)(packDir, 'pack.yaml'));
}
function readPackInfo(packDir, packYamlPath) {
    const packData = js_yaml_1.default.load((0, fs_1.readFileSync)(packYamlPath, 'utf-8'));
    const skillNames = packData.skills ?? [];
    const bundledNames = packData.bundled ?? [];
    // Two layouts, because a pack that mirrors an upstream template keeps the upstream's
    // own paths. The flat one is checked first so a pack declaring nothing behaves as it
    // always did.
    const workflows = {};
    const workflowsDir = [
        (0, path_1.join)(packDir, 'workflows'),
        (0, path_1.join)(packDir, '.vsaf', 'workflows', (0, path_1.basename)(packDir)),
    ].find(dir => (0, fs_1.existsSync)(dir));
    if (workflowsDir) {
        for (const file of (0, fs_1.readdirSync)(workflowsDir).filter(f => f.endsWith('.yaml'))) {
            workflows[file] = (0, fs_1.readFileSync)((0, path_1.join)(workflowsDir, file), 'utf-8');
        }
    }
    return {
        name: packData.name,
        skillNames, bundledNames, workflows,
        canonicalSkillsDir: packData.canonicalSkillsDir,
        skillsRoot: packData.skillsRoot,
        skillsPrefixed: packData.skillsPrefixed,
        skillsKeepInProject: packData.skillsKeepInProject,
        packOnly: packData.packOnly,
        gitignore: packData.gitignore,
        global: packData.global,
        wiring: packData.wiring,
        globalSync: packData.globalSync,
        telemetry: packData.telemetry,
        requiresEngine: packData.requiresEngine,
    };
}
// ── List ──
function skillList(projectPath) {
    const skillsDir = (0, path_1.join)(projectPath, '.claude', 'skills');
    if (!(0, fs_1.existsSync)(skillsDir))
        return [];
    const linkedMap = scanLinkedCommands(projectPath);
    const entries = (0, fs_1.readdirSync)(skillsDir);
    const results = [];
    for (const entry of entries) {
        const skillDir = (0, path_1.join)(skillsDir, entry);
        const skillFile = (0, path_1.join)(skillDir, 'SKILL.md');
        if (!(0, fs_1.statSync)(skillDir).isDirectory() || !(0, fs_1.existsSync)(skillFile))
            continue;
        const { data } = (0, gray_matter_1.default)((0, fs_1.readFileSync)(skillFile, 'utf-8'));
        const fileCount = countFiles(skillDir);
        results.push({
            name: data.name ?? entry,
            description: data.description ?? '',
            fileCount,
            linkedCommand: linkedMap.get(entry),
        });
    }
    return results;
}
// ── Info ──
function skillInfo(name, projectPath) {
    const skillDir = (0, path_1.join)(projectPath, '.claude', 'skills', name);
    const skillFile = (0, path_1.join)(skillDir, 'SKILL.md');
    if (!(0, fs_1.existsSync)(skillFile)) {
        throw new Error(`Skill not found: "${name}"`);
    }
    const { data } = (0, gray_matter_1.default)((0, fs_1.readFileSync)(skillFile, 'utf-8'));
    const files = listFilesRecursive(skillDir, '');
    const linkedCommands = findLinkedCommands(name, projectPath);
    return {
        name: data.name ?? name,
        description: data.description ?? '',
        version: data.version,
        author: data.author,
        files,
        linkedCommands,
    };
}
// ── Remove ──
function skillRemove(name, projectPath) {
    const skillDir = (0, path_1.join)(projectPath, '.claude', 'skills', name);
    if (!(0, fs_1.existsSync)(skillDir)) {
        throw new Error(`Skill not found: "${name}"`);
    }
    const warnings = findLinkedCommands(name, projectPath);
    (0, fs_1.rmSync)(skillDir, { recursive: true, force: true });
    return { removed: name, warnings };
}
// ── Add ──
function skillAdd(source, projectPath, options) {
    const skillsDir = (0, path_1.join)(projectPath, '.claude', 'skills');
    (0, fs_1.mkdirSync)(skillsDir, { recursive: true });
    const resolvedSource = resolveSource(source);
    const detected = detectSkillType(resolvedSource);
    const result = { added: [], skipped: [] };
    if (detected.type === 'single') {
        const name = getSkillName(resolvedSource);
        installSkill(resolvedSource, name, skillsDir, options, result);
    }
    else {
        for (const subdir of detected.skills) {
            if (options.only && !options.only.includes(subdir))
                continue;
            const subPath = (0, path_1.join)(resolvedSource, subdir);
            installSkill(subPath, subdir, skillsDir, options, result);
        }
    }
    // Clean up temp dir if we cloned from git
    if (resolvedSource !== (0, path_1.resolve)(source) && resolvedSource.startsWith((0, os_1.tmpdir)())) {
        (0, fs_1.rmSync)(resolvedSource, { recursive: true, force: true });
    }
    return result;
}
// ── Init (scaffold) ──
/**
 * Nội dung một file `.vsaf/commands/<name>.md`.
 *
 * Tồn tại để chỉ có MỘT nơi biết định dạng file command: trước đây `skillInit` và
 * bước scaffold của `execInstall` mỗi nơi tự dựng một kiểu, nên bản nối chuỗi ở
 * install âm thầm ghi đè bản đúng của skillInit.
 *
 * Front matter được yaml.dump chứ không nội suy vào template string: description
 * là văn xuôi, mang theo dấu hai chấm, nháy và backtick. Dán thô đã từng đẻ ra
 * file command mà chính front matter của nó không parse được, và engine sau đó từ
 * chối chạy mọi workflow tham chiếu tới skill đó. `lineWidth: -1` giữ description
 * dài nằm trên một dòng, để file vừa hợp lệ vừa còn đọc được.
 */
function renderCommandFile(name, skillFile) {
    let description = name;
    if ((0, fs_1.existsSync)(skillFile)) {
        try {
            const { data } = (0, gray_matter_1.default)((0, fs_1.readFileSync)(skillFile, 'utf-8'));
            description = data.description ?? name;
        }
        catch {
            // Front matter hỏng là lỗi của tác giả pack. Lùi về tên skill để một file
            // xấu không giết cả lượt install.
            console.log(`[vsaf] ⚠ ${name}: cannot read front matter — using the name as description`);
        }
    }
    const frontMatter = js_yaml_1.default.dump({ description, skill: name }, { lineWidth: -1, noRefs: true });
    return `---\n${frontMatter}---\n\n## Project context\n<!-- Add your project-specific context here -->\n`;
}
/**
 * Sinh file command cho mọi node `command:` trong workflow của một pack.
 *
 * Node `command:` gọi loadCommand(name, projectPath), hàm này đọc thẳng
 * `.vsaf/commands/<name>.md` và throw nếu thiếu. `user-invocable: true` trong
 * front matter của skill chỉ nối slash command người dùng gõ, không giúp gì cho
 * node workflow. `skillInit` lại chỉ sinh file cho skill có tiền tố pack, nên một
 * pack khai toàn bộ skill ở `bundled:` (autotest-skill) không có file command nào
 * và workflow chết ngay ở node đầu tiên.
 *
 * Chỉ nhận những tên thực sự được `command:` tham chiếu trong workflow của CHÍNH
 * pack đó — không phải mọi skill `bundled` — nên ~23 skill phụ trợ của sdlc không
 * bị đẻ thêm file command.
 */
function scaffoldWorkflowCommands(workflows, projectPath, skillsDir, options) {
    const result = { created: [], owned: [] };
    const names = new Set();
    for (const source of Object.values(workflows)) {
        const workflow = js_yaml_1.default.load(source);
        for (const node of workflow?.nodes ?? []) {
            if (node.command)
                names.add(node.command);
        }
    }
    if (names.size === 0)
        return result;
    const commandsDir = (0, path_1.join)(projectPath, '.vsaf', 'commands');
    (0, fs_1.mkdirSync)(commandsDir, { recursive: true });
    for (const name of names) {
        // Chỉ scaffold khi skill được tham chiếu đã thực sự nằm trên đĩa (do pack này
        // hoặc một lượt install trước) — tên `command:` trỏ vào hư không thì để yên
        // chứ không đoán.
        const skillFile = (0, path_1.join)(skillsDir, name, 'SKILL.md');
        if (!(0, fs_1.existsSync)(skillFile))
            continue;
        result.owned.push(name);
        const cmdFile = (0, path_1.join)(commandsDir, `${name}.md`);
        if ((0, fs_1.existsSync)(cmdFile) && !options?.overwrite)
            continue;
        (0, fs_1.writeFileSync)(cmdFile, renderCommandFile(name, skillFile), 'utf-8');
        result.created.push(name);
    }
    return result;
}
function skillInit(packName, projectPath, skillNames, options) {
    const commandsDir = (0, path_1.join)(projectPath, '.vsaf', 'commands');
    const workflowsDir = (0, path_1.join)(projectPath, '.vsaf', 'workflows', packName);
    (0, fs_1.mkdirSync)(commandsDir, { recursive: true });
    const result = { commandsCreated: [], commandsSkipped: [], workflowsCreated: [] };
    // Scaffold commands
    for (const name of skillNames) {
        const cmdFile = (0, path_1.join)(commandsDir, `${name}.md`);
        if ((0, fs_1.existsSync)(cmdFile)) {
            result.commandsSkipped.push(name);
            continue;
        }
        const skillFile = (0, path_1.join)(projectPath, '.claude', 'skills', name, 'SKILL.md');
        (0, fs_1.writeFileSync)(cmdFile, renderCommandFile(name, skillFile), 'utf-8');
        result.commandsCreated.push(name);
    }
    // Scaffold workflows
    if (options?.workflows && Object.keys(options.workflows).length > 0) {
        (0, fs_1.mkdirSync)(workflowsDir, { recursive: true });
        for (const [filename, yamlContent] of Object.entries(options.workflows)) {
            const wfFile = (0, path_1.join)(workflowsDir, filename);
            if (!(0, fs_1.existsSync)(wfFile) || options.overwriteWorkflows) {
                (0, fs_1.writeFileSync)(wfFile, yamlContent, 'utf-8');
                result.workflowsCreated.push(`${packName}/${filename}`);
            }
        }
    }
    return result;
}
// ── Internal helpers ──
function findPackageRoot() {
    // Navigate up from packages/cli/src/commands/ to monorepo root
    return (0, path_1.resolve)(__dirname, '..', '..', '..', '..');
}
function resolveSource(source) {
    if (source.startsWith('http://') || source.startsWith('https://') || source.startsWith('git@')) {
        const tempDir = (0, path_1.join)((0, os_1.tmpdir)(), `vsaf-clone-${Date.now()}`);
        (0, child_process_1.execSync)(`git clone --depth 1 ${source} ${tempDir}`, { stdio: 'pipe' });
        return tempDir;
    }
    // Check if source is a built-in pack name (no path separators, not a relative/absolute path)
    if (!source.includes('/') && !source.includes('\\') && !source.startsWith('.')) {
        const builtInPath = (0, path_1.join)(findPackageRoot(), 'skills', resolvePackName(source));
        if ((0, fs_1.existsSync)(builtInPath)) {
            return builtInPath;
        }
    }
    return (0, path_1.resolve)(source);
}
function detectSkillType(dir) {
    if ((0, fs_1.existsSync)((0, path_1.join)(dir, 'SKILL.md'))) {
        return { type: 'single' };
    }
    const skills = [];
    for (const entry of (0, fs_1.readdirSync)(dir)) {
        const full = (0, path_1.join)(dir, entry);
        if ((0, fs_1.statSync)(full).isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(full, 'SKILL.md'))) {
            skills.push(entry);
        }
    }
    if (skills.length === 0) {
        throw new Error(`No valid skill found at ${dir}. Expected SKILL.md or subdirectories with SKILL.md.`);
    }
    return { type: 'pack', skills };
}
function getSkillName(skillDir) {
    const skillFile = (0, path_1.join)(skillDir, 'SKILL.md');
    const { data } = (0, gray_matter_1.default)((0, fs_1.readFileSync)(skillFile, 'utf-8'));
    return data.name ?? skillDir.split('/').pop();
}
function installSkill(sourceDir, name, skillsDir, options, result) {
    const targetDir = (0, path_1.join)(skillsDir, name);
    if ((0, fs_1.existsSync)(targetDir)) {
        if (options.force) {
            (0, fs_1.rmSync)(targetDir, { recursive: true, force: true });
        }
        else {
            result.skipped.push(name);
            return;
        }
    }
    (0, fs_1.cpSync)(sourceDir, targetDir, { recursive: true });
    result.added.push(name);
}
function scanLinkedCommands(projectPath) {
    const commandsDir = (0, path_1.join)(projectPath, '.vsaf', 'commands');
    const map = new Map();
    if (!(0, fs_1.existsSync)(commandsDir))
        return map;
    for (const file of (0, fs_1.readdirSync)(commandsDir).filter(f => f.endsWith('.md'))) {
        const raw = (0, fs_1.readFileSync)((0, path_1.join)(commandsDir, file), 'utf-8');
        const { data } = (0, gray_matter_1.default)(raw);
        if (data.skill) {
            map.set(data.skill, `commands/${file}`);
        }
    }
    return map;
}
function findLinkedCommands(skillName, projectPath) {
    const commandsDir = (0, path_1.join)(projectPath, '.vsaf', 'commands');
    if (!(0, fs_1.existsSync)(commandsDir))
        return [];
    const linked = [];
    for (const file of (0, fs_1.readdirSync)(commandsDir).filter(f => f.endsWith('.md'))) {
        const raw = (0, fs_1.readFileSync)((0, path_1.join)(commandsDir, file), 'utf-8');
        const { data } = (0, gray_matter_1.default)(raw);
        if (data.skill === skillName) {
            linked.push(`commands/${file}`);
        }
    }
    return linked;
}
function countFiles(dir) {
    let count = 0;
    for (const entry of (0, fs_1.readdirSync)(dir)) {
        const full = (0, path_1.join)(dir, entry);
        if ((0, fs_1.statSync)(full).isDirectory()) {
            count += countFiles(full);
        }
        else {
            count++;
        }
    }
    return count;
}
function listFilesRecursive(dir, prefix) {
    const files = [];
    for (const entry of (0, fs_1.readdirSync)(dir)) {
        const full = (0, path_1.join)(dir, entry);
        const relative = prefix ? `${prefix}/${entry}` : entry;
        if ((0, fs_1.statSync)(full).isDirectory()) {
            files.push(...listFilesRecursive(full, relative));
        }
        else {
            files.push(relative);
        }
    }
    return files;
}
//# sourceMappingURL=skill.js.map