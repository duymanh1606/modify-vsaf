"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.findBash = findBash;
exports.pythonStubOnPath = pythonStubOnPath;
exports.findPython = findPython;
exports.canSymlink = canSymlink;
exports.checkEnvironment = checkEnvironment;
exports.warnUnwirableRepos = warnUnwirableRepos;
exports.assertScopeIsKnown = assertScopeIsKnown;
exports.assertWiringScriptPresent = assertWiringScriptPresent;
exports.copyPackIntoProject = copyPackIntoProject;
exports.repairCommandFrontMatter = repairCommandFrontMatter;
exports.pythonShimDir = pythonShimDir;
exports.runWiring = runWiring;
exports.runGlobalSync = runGlobalSync;
exports.refuseHomeDirectory = refuseHomeDirectory;
exports.skillsLibraryMissing = skillsLibraryMissing;
exports.warnIfSkillsNotSynced = warnIfSkillsNotSynced;
exports.isProjectInitialised = isProjectInitialised;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
const js_yaml_1 = __importDefault(require("js-yaml"));
/**
 * Handing the wiring back to the pack's own script.
 *
 * A pack can ship the script that sets a project up, and be the source of truth for
 * what those steps are. When it says so, the installer runs that script instead of
 * repeating the work: the alternative is two passes over the same files, where the
 * result is whatever ran last rather than anything anyone decided.
 *
 * The cost is that a shell is now required. That is why the environment is checked
 * before a single file is written — a missing shell halfway through leaves a project
 * with files in it and no wiring, which reads as a finished install.
 */
/** Where Git for Windows puts its shell when it is not on PATH. */
function windowsBashCandidates() {
    const local = process.env.LOCALAPPDATA;
    return [
        'C:\\Program Files\\Git\\bin\\bash.exe',
        'C:\\Program Files (x86)\\Git\\bin\\bash.exe',
        ...(local ? [(0, path_1.join)(local, 'Programs', 'Git', 'bin', 'bash.exe')] : []),
    ];
}
/** Whether a command answers at all. Cheaper and more honest than parsing `which`. */
function answers(command, args) {
    try {
        (0, child_process_1.execFileSync)(command, args, { stdio: 'ignore' });
        return true;
    }
    catch {
        return false;
    }
}
/**
 * What a command prints, or null. Never throws — a caller on the path where an
 * exception would take down an entire install cannot be handed one.
 */
function asks(command, args) {
    try {
        const out = (0, child_process_1.execFileSync)(command, args, {
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe'],
        }).trim();
        return out.length > 0 ? out : null;
    }
    catch {
        return null;
    }
}
/**
 * The shell that will run the pack's scripts, or null.
 *
 * PATH first, so a machine that has arranged its own shell keeps it. The Windows
 * locations are only tried after that, and `wsl` last: it works, but it puts the
 * script in a different filesystem view than the paths it was handed.
 */
function findBash() {
    if (answers('bash', ['-c', 'exit 0'])) {
        // Trả đường dẫn thật, không trả chữ "bash". Khối `Môi trường` tồn tại để trả lời
        // "máy này đang dùng bash nào" — trên Windows câu trả lời có thể là Git Bash, WSL,
        // hay một bản khác trên PATH, và chữ "bash" không phân biệt được ba thứ đó.
        // Hỏi chính bash để tránh phụ thuộc `which`/`where` (không có trên mọi máy).
        //
        // Nhưng giá trị trả về không chỉ để hiển thị — nó còn là lệnh được spawn thẳng
        // (flow-script.ts, delegate.ts, sync.ts). Đường dẫn bash tự báo là góc nhìn hệ
        // thống tệp CỦA BASH, không chắc là đường dẫn Node spawn được: Git Bash trên
        // Windows trả về dạng POSIX như `/usr/bin/bash`, Node trên Windows không thấy
        // đường dẫn đó tồn tại. Vì vậy chỉ nhận kết quả khi `existsSync` xác nhận đó thật
        // sự là một đường dẫn tệp từ góc nhìn của Node — nếu không, quay lại chữ "bash" để
        // PATH tự phân giải như trước, thay vì đưa một lệnh không spawn được.
        const resolved = asks('bash', ['-c', 'command -v bash']);
        return resolved && (0, fs_1.existsSync)(resolved) ? resolved : 'bash';
    }
    if (process.platform === 'win32') {
        for (const path of windowsBashCandidates()) {
            if ((0, fs_1.existsSync)(path))
                return path;
        }
        if (answers('wsl.exe', ['bash', '-c', 'exit 0']))
            return 'wsl.exe';
    }
    return null;
}
/** The Python the pack's scripts look for, in the order they look for it. */
/**
 * A `python3` that is on PATH but cannot run.
 *
 * Windows ships Microsoft Store aliases for `python.exe` and `python3.exe`: the file
 * exists, and running it prints an advert for the Store and exits non-zero. That fools
 * anything testing for presence instead of for an answer — the pack's own script picks
 * its interpreter with `command -v`, so it chooses the stub over a working `python`
 * sitting right beside it, and dies forty lines later inside a step named
 * "Workspace file". Naming the trap here turns that into one sentence with the fix.
 */
function pythonStubOnPath() {
    if (process.platform !== 'win32')
        return null;
    for (const candidate of ['python3', 'python']) {
        const onPath = answers('where', [candidate]);
        if (onPath && !answers(candidate, ['-c', 'pass']))
            return candidate;
    }
    return null;
}
function findPython() {
    for (const candidate of ['python3', 'python']) {
        if (answers(candidate, ['-c', 'pass']))
            return candidate;
    }
    // Windows ships the launcher rather than a `python3` on PATH.
    if (answers('py', ['-3', '-c', 'pass']))
        return 'py -3';
    return null;
}
/**
 * Whether this machine lets a symlink be created at all.
 *
 * Asked by trying, because there is no way to ask. Windows needs Developer Mode or
 * an elevated shell, and without it the wiring silently ends up as copies: the
 * install reports success, the gates never fire, and nothing says so. Knowing the
 * answer up front turns that into a sentence the user can act on.
 */
function canSymlink() {
    const dir = (0, fs_1.mkdtempSync)((0, path_1.join)((0, os_1.tmpdir)(), 'vsaf-symlink-'));
    try {
        (0, fs_1.writeFileSync)((0, path_1.join)(dir, 'target'), '');
        (0, fs_1.symlinkSync)('target', (0, path_1.join)(dir, 'link'));
        return true;
    }
    catch {
        return false;
    }
    finally {
        (0, fs_1.rmSync)(dir, { recursive: true, force: true });
    }
}
/**
 * Check what the pack's scripts need, and report it as one block before anything is
 * written. Throws when the shell is missing, since nothing below it can run.
 */
function checkEnvironment() {
    const bash = findBash();
    const python = findPython();
    const symlink = canSymlink();
    // In theo tài liệu §2 Bước 1, và in ĐÚNG MỘT LẦN cho cả cây tiến trình — không có
    // ngoại lệ cho `--verbose`.
    //
    // Một lượt cài đường flow-script có hai tiến trình engine — tiến trình người dùng gõ,
    // và tiến trình `apply-pack` mà script của flow gọi — và cả hai đều đi qua đây. Dấu
    // trong biến môi trường được tiến trình con thừa hưởng, nên nó là chỗ duy nhất biết
    // được "đã có ai in chưa" mà không cần hai bên biết về nhau. Điều kiện này TỪNG có
    // thêm `verbose ||` phía trước: sai, vì `--verbose` bật ở tiến trình cha khiến điều
    // kiện đó luôn đúng bất kể dấu đã đặt hay chưa, nên `vsaf install ... --verbose` in
    // khối này hai lần — phá đúng hợp đồng "đúng một lần" mà khối này tồn tại để giữ. Bỏ
    // hẳn `verbose` khỏi vế quyết định có in hay không: khối này giờ in trên MỌI lượt
    // cài, `--verbose` không còn vai trò gì ở đây.
    if (!process.env.VSAF_ENV_REPORTED) {
        console.log('[vsaf] Môi trường');
        console.log(`[vsaf]   bash     ${bash ?? '✗ không tìm thấy'}`);
        console.log(`[vsaf]   python   ${python ?? '✗ không tìm thấy'}`);
        console.log(`[vsaf]   symlink  ${symlink ? 'tạo được' : '✗ máy không cho tạo'}`);
        process.env.VSAF_ENV_REPORTED = '1';
    }
    if (!bash) {
        const tried = ['bash trên PATH', ...(process.platform === 'win32' ? windowsBashCandidates() : [])];
        throw new Error('Pack này chạy script bash để nối dây project, nhưng không tìm thấy bash.\n'
            + `  Đã thử: ${tried.join(', ')}\n`
            + '  Windows: cài Git for Windows (git-scm.com/download/win), hoặc dùng WSL2.\n'
            + '  Chưa ghi file nào — cài lại sau khi có bash.');
    }
    if (!python) {
        console.log('[vsaf] ⚠ Không có Python. Script sẽ không ghép được block hooks vào');
        console.log('[vsaf]   .claude/settings.json → event hook KHÔNG fire. Cài Python rồi chạy lại --refresh.');
    }
    else {
        // Even with a working interpreter found, a stub ahead of it on PATH is fatal: the
        // pack's script picks by name, not by answer, and picks the stub.
        const stub = pythonStubOnPath();
        if (stub) {
            console.log(`[vsaf] ⚠ '${stub}' trên PATH là alias Microsoft Store, chạy không được.`);
            console.log(`[vsaf]   Script của pack chọn theo tên nên sẽ chọn nó và dừng ở bước Workspace file,`);
            console.log(`[vsaf]   dù máy có '${python}' dùng được. Tắt: Settings → Apps → Advanced app settings`);
            console.log('[vsaf]   → App execution aliases → tắt python.exe và python3.exe.');
        }
    }
    if (!symlink) {
        // One line: the consequence is "heavier project, edits need --refresh", not a
        // failure, and a two-line warning for that competes with the lines that matter.
        console.log('[vsaf] ⚠ Máy chưa cho tạo symlink → skill/hook là bản copy (bật Developer Mode để dùng link thật).');
    }
    return { bash, python, symlink };
}
/**
 * Build manifests, the same set the pack's script looks for. A sibling without one is
 * something it classifies as "not code" and leaves alone, so it is none of our business
 * either.
 */
const CODE_MANIFESTS = [
    'package.json', 'pom.xml', 'build.gradle', 'build.gradle.kts',
    'go.mod', 'Cargo.toml', 'pyproject.toml', 'requirements.txt',
];
/**
 * Code repos beside the project that this install did not bring in itself.
 *
 * The pack's script finds a project's code repos by scanning the parent directory, and
 * asks a person to confirm the list. Running it unattended answers that question with
 * "yes" — so whatever else sits beside the project is wired up as part of it: a config
 * file written into it, a commit hook installed, a block added to its `CLAUDE.md`.
 * Those are other people's repos.
 *
 * Only repos it would actually act on are counted. A directory with a `.git` and no
 * build manifest is classified as neither spec nor code and skipped, so listing it here
 * would refuse installs over neighbours nothing was ever going to touch.
 */
function unexpectedSiblings(projectPath, broughtIn) {
    const parent = (0, path_1.dirname)(projectPath);
    const ours = new Set([(0, path_1.basename)(projectPath), ...broughtIn.map(path => (0, path_1.basename)(path))]);
    let entries;
    try {
        entries = (0, fs_1.readdirSync)(parent);
    }
    catch {
        return [];
    }
    return entries.filter(name => {
        if (ours.has(name))
            return false;
        const path = (0, path_1.join)(parent, name);
        try {
            if (!(0, fs_1.statSync)(path).isDirectory())
                return false;
            if (!(0, fs_1.existsSync)((0, path_1.join)(path, '.git')))
                return false;
            return CODE_MANIFESTS.some(manifest => (0, fs_1.existsSync)((0, path_1.join)(path, manifest)));
        }
        catch {
            return false;
        }
    });
}
/**
 * Say so when a repo was named that the wiring script will not act on.
 *
 * It only wires siblings that are git repos — reasonably, since there is nowhere to
 * install a commit hook in a directory that is not one. Naming such a directory used to
 * look like it worked: the install finished, and the repo simply had nothing in it.
 * Better to say it out loud than leave it to be noticed later.
 */
function warnUnwirableRepos(projectPath, named) {
    const parent = (0, path_1.dirname)(projectPath);
    for (const given of named) {
        const path = (0, path_1.join)(parent, (0, path_1.basename)(given));
        if (!(0, fs_1.existsSync)(path))
            continue;
        if ((0, fs_1.existsSync)((0, path_1.join)(path, '.git')))
            continue;
        console.log(`[vsaf] ⚠ ${(0, path_1.basename)(given)} chưa là git repo — script nối dây sẽ bỏ qua nó.`);
        console.log(`[vsaf]   Chạy \`git init\` trong đó rồi cài lại với --upgrade.`);
    }
}
/**
 * Decide whether the pack's script may run without a person watching.
 *
 * Unattended is right when the install knows what is beside the project: it either
 * laid the directory out itself, or was told which repos to wire. Otherwise the parent
 * directory is somebody else's business, and answering the script's question on their
 * behalf is not this installer's call.
 *
 * Throws with the list, because the fix is one of two flags and naming them is more
 * use than a warning.
 */
function assertScopeIsKnown(projectPath, broughtIn, named, pack = 'NTAPP') {
    if (named)
        return;
    const strangers = unexpectedSiblings(projectPath, broughtIn);
    if (strangers.length === 0)
        return;
    const project = (0, path_1.basename)(projectPath);
    const folder = (0, path_1.basename)((0, path_1.dirname)(projectPath));
    // Two ways out, both real. `--code-repos` used to be one of them and should not have
    // been: it is a consent gate, not a filter — the wiring script takes no repo list and
    // wires every sibling regardless, so naming three of eight changes nothing about what
    // gets written. And `<pack>` was a placeholder in a message people copy from.
    throw new Error(`Thư mục ${folder} đã có ${strangers.length} repo git mà lệnh này không mang vào:\n`
        + strangers.map(name => `    ${name}`).join('\n') + '\n'
        + `  Script nối dây sẽ coi hết chúng là code repo của ${project} — ghi config, cài hook,\n`
        + '  sửa CLAUDE.md của chúng.\n'
        + '  Nếu chúng KHÔNG thuộc dự án: chạy lại và đặt tên thư mục chứa khác (thư mục rỗng).\n'
        + `  Nếu chúng thuộc dự án:  cd ${folder}/${project} && vsaf install ${pack} --upgrade`);
}
/**
 * Refuse a re-wire of a project the pack was never installed into.
 *
 * `--refresh` and `--upgrade` both mean "the project is laid out, wire it again", so
 * neither copies anything — which leaves nothing to call when the project has no copy
 * yet. Without this the shell reports the missing file, and `bash: ./scripts/bootstrap.sh:
 * No such file or directory` says nothing about which flag to drop.
 */
function assertWiringScriptPresent(projectPath, info, rewiring) {
    if (!rewiring)
        return;
    const script = info.wiring?.script;
    if (!script || (0, fs_1.existsSync)((0, path_1.join)(projectPath, script)))
        return;
    throw new Error(`Project này chưa cài pack — không có ${script} để nối dây lại.\n`
        + '  Bỏ --refresh/--upgrade để cài lần đầu, rồi dùng chúng cho các lượt sau.');
}
/**
 * Copy the pack into the project, the way the pack's own documentation says to.
 *
 * Two things are held back. `pack.yaml` describes the pack to the installer and means
 * nothing inside a project. The skill library is held back because it belongs on the
 * machine — every project sharing one copy is the whole point — except the one skill
 * that puts it there, which has to travel so a machine with an empty library still has
 * a way to fill it.
 *
 * Nothing already in the project is overwritten unless asked: on a re-run the files
 * there may have been edited, and the pack has no way to tell an edit from a stale
 * copy.
 *
 * Returns the project path, or null when the pack does not ship a project layout.
 */
function copyPackIntoProject(packDir, projectPath, info, options = {}) {
    const written = [];
    const skillsRoot = info.skillsRoot ? (0, path_1.join)(packDir, info.skillsRoot) : null;
    const keep = new Set(info.skillsKeepInProject ?? []);
    const packOnly = ['pack.yaml', ...(info.packOnly ?? [])].map(path => (0, path_1.join)(packDir, path));
    (0, fs_1.cpSync)(packDir, projectPath, {
        recursive: true,
        force: options.force ?? false,
        errorOnExist: false,
        filter: (source, destination) => {
            if (packOnly.some(path => source === path || source.startsWith(path + path_1.sep)))
                return false;
            if (skillsRoot && source.startsWith(skillsRoot + path_1.sep)) {
                // The library root itself travels; what is inside it does not, bar the keepers.
                const name = (0, path_1.relative)(skillsRoot, source).split(path_1.sep)[0];
                return keep.has(name);
            }
            // Directories are always descended into. Refusing one because it already exists
            // stops the walk there, and the very first call is the pack root itself — which
            // exists by definition, so the whole copy was being skipped before it started.
            if ((0, fs_1.statSync)(source).isDirectory())
                return true;
            if (!options.force && (0, fs_1.existsSync)(destination))
                return false;
            written.push((0, path_1.relative)(packDir, source));
            return true;
        },
    });
    // The pack carries two readmes: its own, and the one meant for a project made from
    // it. The project keeps the second under the name anyone opening it will look for.
    const specReadme = (0, path_1.join)(projectPath, 'README.spec-template.md');
    if ((0, fs_1.existsSync)(specReadme)) {
        (0, fs_1.renameSync)(specReadme, (0, path_1.join)(projectPath, 'README.md'));
    }
    return written;
}
/**
 * Re-serialise slash-command front matter the pack shipped unparsable.
 *
 * A description holding `": "` — "Stage 2 — 6 sub-agent: HLD + Module 0 + WBS" — reads
 * as a nested mapping when it is written unquoted, and the file stops parsing. Four of
 * the pack's command files carry it. The generator on this side has serialised front
 * matter properly for a while; copying the files verbatim brought the bug back in
 * through the other door, so they are repaired on the way in.
 *
 * Only files that fail to parse are touched, and only their front matter: the body is
 * where a project keeps its own notes.
 *
 * Returns the files rewritten.
 */
function repairCommandFrontMatter(projectPath) {
    const dir = (0, path_1.join)(projectPath, '.vsaf', 'commands');
    if (!(0, fs_1.existsSync)(dir))
        return [];
    const repaired = [];
    for (const name of (0, fs_1.readdirSync)(dir).filter(file => file.endsWith('.md'))) {
        const path = (0, path_1.join)(dir, name);
        const text = (0, fs_1.readFileSync)(path, 'utf-8');
        if (!text.startsWith('---'))
            continue;
        const end = text.indexOf('\n---', 3);
        if (end === -1)
            continue;
        const front = text.slice(3, end);
        const body = text.slice(end + 4);
        try {
            js_yaml_1.default.load(front);
            continue; // parses already
        }
        catch {
            // The reason this function exists.
        }
        // Rebuilt from the lines rather than parsed, because parsing is what just failed.
        // Every `key: value` keeps its key and gets its value quoted by the serialiser.
        const fields = {};
        for (const line of front.split('\n')) {
            const match = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line);
            if (match)
                fields[match[1]] = match[2].replace(/^["']|["']$/g, '');
        }
        if (Object.keys(fields).length === 0)
            continue;
        (0, fs_1.writeFileSync)(path, `---\n${js_yaml_1.default.dump(fields, { lineWidth: -1 })}---${body}`, 'utf-8');
        repaired.push(name);
    }
    return repaired;
}
/** Run one of the pack's scripts, with its output going straight to the user. */
/** Colour codes sit between the marker and the line start, so they come off first. */
const ANSI = /\u001b\[[0-9;]*m/g;
/** A script's own failures — printed. */
const FAILED = /(✗|✘|FAIL|Error:|error:)/;
/**
 * Only failures reach the screen. The pack separates the two itself — `error()` prints
 * `✗`, `warn()` prints `⚠` — and its warnings are standing reminders it emits on every
 * run. They stay in the log, which the summary line points at.
 */
/**
 * Run a pack's script, quietly.
 *
 * The wiring script narrates about seventy lines of its own — pre-flight, eight setup
 * sections, three self-test blocks, a closing banner. All of it useful once, none of it
 * useful every time, and it buries the two things a reader actually needs: whether
 * something failed, and what to run next. So the output goes to a log file, only its
 * warnings and failures are echoed, and a non-zero exit prints the whole thing.
 * `--verbose` restores the running commentary.
 */
function runScript(bash, cwd, script, args, env, label, options = {}) {
    if (options.verbose) {
        console.log(`[vsaf] → ${label} (${script})`);
        console.log('─'.repeat(60));
        try {
            // A relative path, and `cwd` rather than an absolute argument: a Windows path
            // handed to bash has its separators read as escapes. `execFileSync` rather than a
            // shell string, because the shell's own path holds a space on Windows and passing
            // it as `shell:` fails to spawn at all.
            (0, child_process_1.execFileSync)(bash, [script, ...args], {
                cwd,
                stdio: 'inherit',
                env: { ...process.env, ...env },
            });
        }
        finally {
            console.log('─'.repeat(60));
        }
        return '';
    }
    // Nothing printed around this step, either side of it. It runs the pack's whole script
    // with the output captured, so on a slow machine there is a silent gap here — measured
    // in minutes inside a OneDrive-synced folder, where it read as a hang. The line that
    // used to say so was removed on request; the log named by the failure path is where a
    // gap that turns out to matter gets explained.
    let output = '';
    try {
        output = (0, child_process_1.execFileSync)(bash, [script, ...args], {
            cwd,
            stdio: ['inherit', 'pipe', 'pipe'],
            encoding: 'utf-8',
            env: { ...process.env, ...env },
        });
    }
    catch (error) {
        const failure = error;
        output = `${failure.stdout ?? ''}${failure.stderr ?? ''}`;
        writeLog(options.logPath, output);
        console.log('');
        console.log(output.trimEnd());
        console.log('');
        throw new Error(`${label} thất bại — toàn bộ output ở trên${options.logPath ? ` và trong ${options.logPath}` : ''}`);
    }
    writeLog(options.logPath, output);
    const lines = output.split('\n').map(line => line.replace(ANSI, '').trimEnd());
    // Failures are printed; warnings are counted. A routine install warns half a dozen
    // times about files it backed up, and printing those is how the two lines that matter
    // got lost in the first place.
    for (const line of lines.filter(line => FAILED.test(line)))
        console.log(`[vsaf] ${line.trim()}`);
    // Nothing printed on success. The step that follows says what to do next, and a failure
    // prints the script's whole output — so a line whose only content is "the thing that was
    // going to happen happened" is one more line to read past. The log stays on disk for
    // when something needs looking at.
    return output;
}
/** Best-effort: a log we could not write is not a reason to fail the install. */
function writeLog(logPath, output) {
    if (!logPath)
        return;
    try {
        (0, fs_1.writeFileSync)(logPath, output, 'utf-8');
    }
    catch { /* nothing to do about it */ }
}
/** Hand the project over to the pack's wiring script. */
/**
 * A throwaway `python3` on PATH that actually runs, for the pack's script to find.
 *
 * The script picks its interpreter with `command -v python3`, which answers "yes" to the
 * Microsoft Store alias — a file that exists and prints an advert. It cannot be told
 * otherwise: it sets `PYTHON_BIN=""` before looking, so an inherited value is discarded.
 * What the caller does control is the child's PATH. Putting a working interpreter there
 * under the name the script looks for makes the right thing happen with nothing asked of
 * the user, and leaves the machine untouched — the directory is temporary.
 *
 * Returns null when there is nothing to fix, so a healthy machine behaves exactly as before.
 */
function pythonShimDir() {
    if (process.platform !== 'win32')
        return null;
    if (!pythonStubOnPath())
        return null;
    const python = findPython();
    // Nothing to redirect to, or the name the script prefers already works.
    if (!python || python === 'python3')
        return null;
    // An absolute path, never the name: a shim called `python3` that execs `python` would
    // find this very shim when the same directory also shadows `python`, and a shim that
    // execs `python3` finds itself. Both spin forever — measured, before this line existed.
    const real = interpreterPath(python);
    if (!real)
        return null;
    const dir = (0, fs_1.mkdtempSync)((0, path_1.join)((0, os_1.tmpdir)(), 'vsaf-python-shim-'));
    try {
        // Only `python3`: that is the name the script tries first, and shadowing `python`
        // as well is what opens the loop above. A shebang is what marks a file executable
        // under MSYS; `exec "$@"` keeps the real interpreter's streams and exit status.
        // Forward slashes because a /bin/sh script cannot read a backslash path.
        const target = real.replace(/\\/g, '/');
        (0, fs_1.writeFileSync)((0, path_1.join)(dir, 'python3'), `#!/bin/sh\nexec "${target}" "$@"\n`, { mode: 0o755 });
        return { dir, cleanup: () => (0, fs_1.rmSync)(dir, { recursive: true, force: true }) };
    }
    catch {
        (0, fs_1.rmSync)(dir, { recursive: true, force: true });
        return null;
    }
}
/** Where a working interpreter actually lives, asked of the interpreter itself. */
function interpreterPath(python) {
    const [command, ...args] = python.split(' ');
    try {
        const out = (0, child_process_1.execFileSync)(command, [...args, '-c', 'import sys;print(sys.executable)'], {
            encoding: 'utf-8',
            stdio: ['pipe', 'pipe', 'pipe'],
        }).trim();
        return out || null;
    }
    catch {
        return null;
    }
}
function runWiring(bash, projectPath, info, options) {
    const wiring = info.wiring;
    if (!wiring)
        return;
    const env = {};
    // Named by the pack rather than guessed: its script asks for the project name and
    // for confirmation of which repos belong to it, and a script that asks with nothing
    // attached to answer simply waits.
    if (wiring.env.includes('PROJECT_NAME'))
        env.PROJECT_NAME = options.projectName;
    if (wiring.env.includes('AUTO_CONFIRM'))
        env.AUTO_CONFIRM = '1';
    const allowed = options.passthrough.filter(flag => wiring.passthrough.includes(flag));
    const extra = options.passthrough.filter(flag => !wiring.passthrough.includes(flag));
    const shim = pythonShimDir();
    if (shim) {
        env.PATH = `${shim.dir}${path_1.delimiter}${process.env.PATH ?? ''}`;
        console.log('[vsaf] Máy có python3 giả của Microsoft Store — đã tạm trỏ python3 vào bản dùng được');
    }
    try {
        runScript(bash, projectPath, `./${wiring.script}`, [...allowed, ...extra], env, 'nối dây', {
            verbose: options.verbose,
            logPath: (0, path_1.join)(projectPath, '.vsaf', 'install.log'),
        });
    }
    finally {
        shim?.cleanup();
    }
}
/**
 * Hand the machine-wide skills over to the pack's own sync script.
 *
 * Run inside the pack directory, which is why the pack keeps its upstream layout: the
 * script reads its sources relative to itself, so no staging directory has to be built
 * and thrown away on every run.
 */
function runGlobalSync(bash, packDir, info, flags, verbose = false, pack = '<pack>') {
    const sync = info.globalSync;
    if (!sync)
        throw new Error('Pack này không khai script đồng bộ ra máy (globalSync)');
    const unknown = flags.filter(flag => !sync.passthrough.includes(flag));
    if (unknown.length > 0) {
        console.log(`[vsaf] Cờ không thuộc script này, vẫn chuyển tiếp: ${unknown.join(' ')}`);
    }
    const output = runScript(bash, packDir, `./${sync.script}`, flags, {}, 'đồng bộ skill + rule ra máy', {
        verbose,
        summarise: false,
    });
    if (verbose)
        return;
    // No counts. How many skills reached how many directories is this command's own
    // bookkeeping — nobody decides anything with it, and it crowded out the two lines that
    // do matter: what each of the two people here runs next.
    void output;
    // Hai dòng này là gợi ý cho lệnh `vsaf sync` GÕ TAY. Khi sync chạy bên trong một lượt
    // cài — `install.sh` của flow gọi nó — chúng rơi vào giữa transcript của lượt cài, và
    // gợi ý "hãy chạy install" ngay giữa một lượt install là câu vô nghĩa.
    if (process.env.VSAF_INSTALL_NESTED === '1')
        return;
    // Two ways on, because there are two people here. `sync` is the one command both run,
    // and naming only `--new` sent the person joining an existing project down the path that
    // creates a second one.
    //
    // Where to run it, not a `git clone` to copy: the spec repo has to be on disk already —
    // the command runs inside it — and their code repos come from the group link this asks
    // for, not from cloning each one by hand.
    console.log(`[vsaf]   Lead:    vsaf install ${pack} --new`);
    console.log(`[vsaf]   Member:  vsaf install ${pack} --clone`);
}
/** Home directory, refused as an install target: it is nobody's project. */
function refuseHomeDirectory(projectPath) {
    if (projectPath === (0, os_1.homedir)()) {
        throw new Error('Đây là thư mục home, không phải một project — cài vào đây sẽ rải cây artifact ra khắp nhà.\n'
            + '  Muốn chỉ lấy skill về máy: vsaf sync <pack>');
    }
}
/**
 * Name the remaining command when the project still has no telemetry.
 *
 * `install` and `init` stay one command per job, so nothing here runs `init`. What this
 * closes is the failure mode that made the split expensive: a pack shipping its own
 * `.vsaf/config.yaml` arrives with no `telemetry:` section, `doctor` reports "telemetry
 * disabled" with a green tick, and every run of the flow reaches no backend — with no
 * error anywhere to say why. Naming the exact command costs one line and removes the
 * silence.
 */
/**
 * Tên các skill pack mang theo — đọc thư mục một chỗ duy nhất.
 *
 * `skillsLibraryMissing` và `warnIfSkillsNotSynced` đều cần đúng danh sách này: hàm đầu
 * so từng tên với máy, hàm sau chỉ đếm cho câu in. Hai đoạn quét thư mục riêng ở hai hàm
 * là chỗ chúng có thể trôi khỏi nhau khi một bên đổi luật lọc mà bên kia quên theo —
 * dùng chung một hàm thì không còn hai bản để trôi.
 */
function packSkillNames(packDir, packInfo) {
    const root = (0, path_1.join)(packDir, packInfo.skillsRoot ?? '.agent/skills');
    try {
        return (0, fs_1.readdirSync)(root, { withFileTypes: true })
            .filter(entry => entry.isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(root, entry.name, 'SKILL.md')))
            .map(entry => entry.name);
    }
    catch {
        return []; // Không đọc được thư mục thì coi như pack không mang skill nào.
    }
}
/**
 * Máy này chưa có thư viện skill của pack hay chưa — vị từ thuần, không in gì.
 *
 * Tách khỏi hàm cảnh báo vì lượt cài cần biết điều này **trước** khi chạy script (script
 * của flow có thể tự sync), rồi so lại **sau** khi script xong. Một hàm vừa đo vừa in
 * không dùng được cho phép so đó.
 */
function skillsLibraryMissing(packDir, packInfo) {
    const names = packSkillNames(packDir, packInfo);
    // Pack không mang skill nào (kể cả khi lý do là thư mục không đọc được): với CẢ HAI
    // người gọi hàm này, `false` đều đúng — `warnIfSkillsNotSynced` không có gì để cảnh
    // báo, và phép so before/after của lượt cài (`install.ts`) không có gì để coi là "vừa
    // về máy".
    if (names.length === 0)
        return false;
    const home = process.env.HOME;
    if (!home)
        return false;
    return names.every(name => !(0, fs_1.existsSync)((0, path_1.join)(home, '.claude', 'skills', name)));
}
/**
 * Warn when the pack's skill library is not on this machine yet.
 *
 * `vsaf sync` puts the skills under `$HOME`, `vsaf install` wires a project to them.
 * Skipping the first step leaves an install that reports success and a project where no
 * `/pack-*` command resolves — and the failure then shows up much later, inside a
 * workflow, as an empty artifact rather than a missing skill. So say it here, where the
 * fix is one command away.
 */
function warnIfSkillsNotSynced(packDir, packInfo, pack) {
    if (!skillsLibraryMissing(packDir, packInfo))
        return false;
    const count = packSkillNames(packDir, packInfo).length;
    console.log('');
    console.log(`[vsaf] ⚠ Thư viện skill chưa có trên máy — lệnh /${pack}-* sẽ không gõ được.`);
    console.log(`[vsaf]   Chạy tiếp:  vsaf sync ${pack}`);
    console.log(`[vsaf]   Nó copy ${count} skill vào ~/.claude/skills (một lần cho cả máy).`);
    return true;
}
/**
 * Whether `init` has already run here — the telemetry section is what it writes that
 * nothing else does. Read rather than warned about now that `install` runs `init` itself:
 * the only thing left to decide is whether to run it again.
 */
function isProjectInitialised(projectPath) {
    try {
        return /^telemetry:/m.test((0, fs_1.readFileSync)((0, path_1.join)(projectPath, '.vsaf', 'config.yaml'), 'utf-8'));
    }
    catch {
        return false; // No config at all is not initialised.
    }
}
//# sourceMappingURL=delegate.js.map