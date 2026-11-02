"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.initGitRepo = initGitRepo;
exports.prepareNewProject = prepareNewProject;
exports.commitInitial = commitInitial;
exports.refreshInitialCommit = refreshInitialCommit;
exports.adoptProblem = adoptProblem;
exports.adoptCodeRepos = adoptCodeRepos;
exports.offerCredentialHelper = offerCredentialHelper;
exports.mayAskForPassword = mayAskForPassword;
exports.targetName = targetName;
exports.refusesTheAsker = refusesTheAsker;
exports.waitForEnter = waitForEnter;
exports.headerForms = headerForms;
exports.cloneCodeRepos = cloneCodeRepos;
exports.cloneInto = cloneInto;
const child_process_1 = require("child_process");
const credentials_js_1 = require("./credentials.js");
const fs_1 = require("fs");
const path_1 = require("path");
function git(args, cwd, env) {
    return (0, child_process_1.execFileSync)('git', args, {
        cwd,
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
        // Never let git ask. stdin is a pipe, so on Linux and macOS it already gives up and
        // fails — but Windows answers a missing credential by opening a Git Credential
        // Manager window instead, and an install run from a terminal has no way to surface
        // it. Measured on Windows: the run stopped after "2/4 git init + commit đầu" with no
        // further output, waiting on a dialog behind the window. Refusing the prompt turns
        // that hang into git's own error, which the caller already knows how to report.
        // Last, not first: `withToken` spreads `process.env`, and a shell that exported
        // GIT_TERMINAL_PROMPT=1 would otherwise put the prompt back.
        env: { ...(env ?? process.env), GIT_TERMINAL_PROMPT: '0', GCM_INTERACTIVE: 'never' },
    }).toString();
}
/** True when the directory is inside a git repo, its own or an enclosing one. */
function insideRepo(dir) {
    try {
        return git(['rev-parse', '--is-inside-work-tree'], dir).trim() === 'true';
    }
    catch {
        return false;
    }
}
/**
 * The repo this directory sits inside, when that repo is not the directory itself.
 *
 * Used to tell "already a repo, nothing to do" apart from "somebody else's repo is
 * further up" — two situations the inside-a-work-tree question answers identically.
 */
function enclosingRepo(dir) {
    try {
        const top = git(['rev-parse', '--show-toplevel'], dir).trim();
        if (!top)
            return null;
        return (0, path_1.resolve)(top) === (0, path_1.resolve)(dir) ? null : top;
    }
    catch {
        return null;
    }
}
/** True when the directory holds other git repos — a workspace, not a project. */
function holdsRepos(dir) {
    try {
        return (0, fs_1.readdirSync)(dir, { withFileTypes: true })
            .some(entry => entry.isDirectory() && entry.name !== '.git' && (0, fs_1.existsSync)((0, path_1.join)(dir, entry.name, '.git')));
    }
    catch {
        return false;
    }
}
/**
 * Start a repo in the project directory when there is none.
 *
 * Nothing is committed. What the install generates is for the user to read before
 * it enters their history, and a commit made on their behalf is not something an
 * installer should decide.
 *
 * Two directories are left alone:
 *
 * - one already inside a repo, because a repo inside a repo hides the inner files
 *   from the outer one;
 * - one that holds other git repos, because that is a workspace and not a project.
 *   Measured consequence of getting this wrong: an empty repo appeared at a workspace
 *   root holding nine unrelated repos, and from then on every project created beneath
 *   it silently skipped its own `git init` — so their documents and sign-off gates had
 *   nowhere to be committed.
 *
 * Returns the directory when a repo was started, or null when there was nothing
 * to do.
 */
function initGitRepo(projectPath) {
    // Already its own repo: nothing to start.
    if ((0, fs_1.existsSync)((0, path_1.join)(projectPath, '.git')))
        return null;
    // A directory holding repos of its own is a workspace, not a project. Starting one
    // here would swallow those repos as gitlinks on the first `git add -A`.
    if (holdsRepos(projectPath)) {
        console.log(`[vsaf] ${(0, path_1.basename)(projectPath)} holds other git repos — not starting one here`);
        return null;
    }
    // Sitting inside somebody else's repo used to mean "decline", which left the project
    // without a `.git` and let the pack's script fail forty lines later on a check it was
    // right to make. Nesting is legal and is what the user asked for: the inner repo
    // shadows the outer one for everything under it, and the outer sees one untracked
    // directory. Measured on Windows, where a home folder that happens to be a repo made
    // every install in it fail — while the same install on Linux, outside any repo, worked.
    // Not announced: nesting is now the normal outcome, and a line reporting that things
    // went as they should is the kind of line that makes the ones reporting trouble hard
    // to see. A machine whose home directory is a repo would print it on every install.
    try {
        git(['init', '-q'], projectPath);
        return projectPath;
    }
    catch (error) {
        console.log(`[vsaf] Could not start a git repo here — ${error.message}`);
        return null;
    }
}
/**
 * Lay out a new project: `<name>/<name>-spec` under the current directory, which is
 * the shape the flow expects — the documents repo with room beside it for the code
 * repos. Returns the documents repo path.
 *
 * The older template did this with a copy command, so the tool creating the
 * directory is what people expect; asking them to `mkdir` first is a step the tool
 * can take itself.
 *
 * An existing directory is reused rather than refused: installing again into a
 * project already laid out this way must work.
 */
function prepareNewProject(cwd, name) {
    const trimmed = name.trim();
    if (!trimmed || trimmed.includes('/') || trimmed.includes('\\') || trimmed.startsWith('.')) {
        throw new Error(`"${name}" is not a usable project name — use a plain name like "nen-tang"`);
    }
    const specRepo = (0, path_1.join)(cwd, trimmed, `${trimmed}-spec`);
    (0, fs_1.mkdirSync)(specRepo, { recursive: true });
    return specRepo;
}
/**
 * Make the first commit, so the repo has a commit at all.
 *
 * A repo with `git init` and nothing else has an unborn HEAD, and the flow's own
 * workflows run in git worktrees: creating one against an unborn HEAD leaves a branch
 * that never becomes a ref, so the run finishes and then fails while cleaning up, with
 * `git branch -D` reporting a branch it cannot find. The upstream setup instructions
 * end their copy step with a commit for the same reason.
 *
 * Returns true when a commit was made. An existing history is left alone.
 */
function commitInitial(projectPath, message) {
    try {
        // An existing commit means this is not a fresh repo; adding one would be noise.
        git(['rev-parse', '--verify', 'HEAD'], projectPath);
        return false;
    }
    catch {
        // Unborn HEAD — that is the case this exists for.
    }
    try {
        git(['add', '-A'], projectPath);
        git(['commit', '-q', '-m', message], projectPath);
        return true;
    }
    catch (error) {
        // Missing git identity is the usual cause, and it is not worth failing an install
        // over: the files are all there, only the commit is not.
        console.log(`[vsaf] ⚠ Chưa tạo được commit đầu — ${error.message.split('\n')[0]}`);
        console.log('[vsaf]   Workflow dùng worktree sẽ báo lỗi lúc dọn. Commit tay rồi chạy lại.');
        return false;
    }
}
/**
 * Đưa những gì script cấu hình vừa sửa vào chính commit đầu.
 *
 * The commit has to happen before the wiring runs — the wiring is what installs the
 * pre-commit hook, and that hook refuses this very repo: `scripts/*.sh` and `hooks/*.py`
 * carry no `id:` header, which is Rule 1. So the first commit is made early, and it
 * captures the project *before* the script renames it: the committed `CLAUDE.md` still
 * says `# Project: NTAPP (VSAF Blended)` while the file on disk says the real name.
 *
 * Measured, and the reason this exists: a lead who pushes that commit publishes a spec
 * repo carrying the template's name, and then every teammate's `--clone` ends at
 * "nối dây thất bại" — the pack's own self-test refuses a project still named after the
 * template. Nothing looked wrong on the lead's machine, because on disk it was right.
 *
 * So once the wiring is done, fold its edits into the same commit. `--amend` rather than
 * a second commit: two commits would mean the first is still pushable on its own, which
 * is the state being fixed.
 *
 * Kept out on purpose — this machine's own state, which has no business in a repo other
 * people clone: vsaf's install record and storage, the pack's notification spool. The
 * pack's `.gitignore` block already covers `*.bak.*` and the install log.
 *
 * Staged then unstaged, rather than excluded by pathspec: `git add -- ':(exclude)<path>'`
 * fails outright when the named path is one `.gitignore` already covers — measured, the
 * whole amend was lost to `git add` refusing over `.vsaf/install.log`. `reset` on a path
 * that was never staged does nothing, which is the behaviour wanted here.
 *
 * `--no-verify`, for the same reason the commit came first.
 */
function refreshInitialCommit(projectPath) {
    // The log is listed even though the pack's `.gitignore` block covers it: relying on
    // somebody else's ignore file to keep this machine's paths out of a shared repo is a
    // dependency worth not having.
    const machineLocal = [
        '.vsaf/install.log', '.vsaf/installed', '.vsaf/storage', 'NTAPP-output/_notifications',
    ];
    try {
        git(['add', '-A'], projectPath);
        try {
            git(['reset', '-q', '--', ...machineLocal], projectPath);
        }
        catch {
            // None of them staged — nothing to take back out.
        }
        try {
            // Nothing staged: the wiring changed nothing the repo tracks, so leave the commit be.
            git(['diff', '--cached', '--quiet'], projectPath);
            return 'nothing';
        }
        catch {
            // Something is staged — that is the case this exists for.
        }
        git(['commit', '--amend', '--no-edit', '--no-verify', '-q'], projectPath);
        return 'amended';
    }
    catch (error) {
        // Not worth failing an install over: every file is in place, only the commit lags.
        // But say it, because the consequence lands on somebody else's machine.
        console.log(`[vsaf] ⚠ Commit đầu chưa gồm phần cấu hình — ${error.message.split('\n')[0]}`);
        console.log('[vsaf]   Commit tay trước khi push, nếu không người khác clone về sẽ thấy tên dự án cũ.');
        return 'failed';
    }
}
/**
 * Why a path cannot be brought into the project, or null when it can.
 *
 * Split out from the copying so the answer can be had before the install writes
 * anything: adopting is one of the last steps, and finding out there that a path is a
 * file leaves a directory half set up.
 *
 * Reads the disk, changes nothing.
 */
function adoptProblem(specRepo, given) {
    const parent = (0, path_1.dirname)(specRepo);
    const source = (0, path_1.resolve)(specRepo, given);
    if (source === specRepo || source === parent) {
        return `"${given}" is the project itself — it cannot be one of its own code repos`;
    }
    if (!(0, fs_1.existsSync)(source) || !(0, fs_1.statSync)(source).isDirectory()) {
        return `"${given}" is not a directory on disk`;
    }
    return null;
}
/**
 * Bring code repos that already exist on disk into the project's directory, beside
 * the documents repo, which is where the layout expects them.
 *
 * Copied, leaving the original where it is — the caller asked for this over moving.
 * Worth knowing what it costs: a working repo is often hundreds of megabytes, and
 * uncommitted work ends up in both copies, free to diverge. The copy in the project
 * is the one that gets wired, so that is the one to work in.
 *
 * `git clone <url>` is what the flow's own documents prescribe for code repos; this
 * is for repos already on disk that should not be fetched again.
 *
 * A repo already in the right place is left alone. Anything that is not a directory,
 * or that would take the project into itself, is refused by name rather than skipped
 * quietly.
 *
 * Returns the repos' paths inside the project.
 */
function adoptCodeRepos(specRepo, paths) {
    if (paths.length === 0)
        return [];
    const parent = (0, path_1.dirname)(specRepo);
    const adopted = [];
    for (const given of paths) {
        const problem = adoptProblem(specRepo, given);
        if (problem)
            throw new Error(problem);
        const source = (0, path_1.resolve)(specRepo, given);
        const target = (0, path_1.join)(parent, (0, path_1.basename)(source));
        if (source === target) {
            adopted.push(target);
            continue;
        }
        // Never copied over, and no longer a reason to stop.
        //
        // Refusing outright was right about the danger — whichever repo lost the name
        // would be destroyed — and wrong about what to do with it, once re-running the
        // same command became the way a half-finished install is finished: the second run
        // of `--adopt <path>` refused, which is the one command the installer had just
        // told the user to run. Both repos survive either way; the difference is only
        // whether the run continues. It does, and says which copy it kept.
        if ((0, fs_1.existsSync)(target)) {
            console.log(`[vsaf] ${(0, path_1.basename)(target)} đã có trong ${(0, path_1.basename)(parent)}/ — giữ nguyên, không copy đè`);
            console.log(`[vsaf]   (không sao chép từ ${source} — nếu đó là repo khác thì đổi tên một trong hai rồi chạy lại)`);
            adopted.push(target);
            continue;
        }
        // Said before it happens, with what it costs and what the other option was: a
        // working repo is often hundreds of megabytes, the copy takes uncommitted work
        // with it, and from here on only the copy inside the project is wired.
        console.log(`[vsaf] Copy ${(0, path_1.basename)(source)} vào ${(0, path_1.basename)(parent)}/ — bản gốc giữ nguyên chỗ cũ`);
        console.log('[vsaf]   (muốn dùng tại chỗ, không nhân đôi: đưa đường dẫn cho --code-repos thay vì --adopt)');
        (0, fs_1.cpSync)(source, target, { recursive: true });
        adopted.push(target);
    }
    return adopted;
}
/**
 * Why git refused, in git's own words.
 *
 * The first line of the thrown error only ever says `Command failed: git clone …`, which
 * repeats the command back at the user and explains nothing. Measured against a real
 * project: twelve repos failed with "Your Bitbucket account has been locked, solve a
 * CAPTCHA" and the install reported twelve identical `Command failed` lines instead —
 * the one sentence that named the fix was thrown away.
 */
function gitReason(error) {
    const stderr = error?.stderr?.toString() ?? '';
    const lines = stderr.split('\n').map(line => line.trim()).filter(Boolean);
    if (lines.length > 0)
        return lines.slice(0, 6);
    return [error?.message?.split('\n')[0] ?? 'không rõ nguyên nhân'];
}
/**
 * Offer to turn on a credential helper, before a password gets typed twelve times.
 *
 * With no helper git has nowhere to keep what it asked for: it uses the answer once and
 * forgets, so every repo asks again. macOS ships no helper by default — measured there,
 * cloning a group of twelve meant twelve prompts, and none of them stuck. Windows has
 * `manager` already, which is why the same install feels fine there.
 *
 * Asked, not done quietly: `credential.helper` is this person's global git config, and
 * turning it on decides where their passwords get stored. Nobody at the keyboard means no
 * question — just the one line, so the reason for the twelve prompts is on screen.
 */
function offerCredentialHelper(count, deps = {}) {
    const configured = deps.configured ?? credentials_js_1.configuredHelper;
    const osHelper = deps.osHelper ?? credentials_js_1.helperForThisOs;
    const say = deps.say ?? ((line) => console.log(line));
    if (configured())
        return 'đã có';
    // One line, and no question. The batch below asks for the password once and carries it to
    // every clone, so nothing here is urgent — a helper only saves the *next* run from asking
    // at all. Asking permission to change someone's global git config, to fix an
    // inconvenience already handled, is a question that buys nothing.
    const helper = osHelper() ?? 'libsecret';
    say(`[vsaf]   (${count} repo — nhập mật khẩu một lần. Muốn lần sau khỏi nhập:`
        + ` git config --global credential.helper ${helper})`);
    return 'đã nhắc';
}
/**
 * True when cloning these urls could stop on a password prompt nobody sees.
 *
 * Git asks for a credential through whatever helper the machine has, and inside VS Code or
 * Antigravity that helper is the editor: a small input opens in the middle of the window
 * while the terminal — the only place the person is looking — shows nothing at all. It
 * reads as a hang, and the people this install is for include PO and BA, who have no
 * reason to know where git asks things.
 *
 * Http only. An ssh url uses a key on disk and asks nobody, so a warning there would fire
 * where it cannot apply — which is how warnings stop being read.
 */
function mayAskForPassword(urls) {
    return urls.some(url => /^https?:/i.test(url.trim()));
}
/** `(3/12)` — where in the batch this is. Padded so the names below line up. */
function step(index, total) {
    const width = String(total).length;
    return `(${String(index + 1).padStart(width)}/${total})`;
}
/** Directory name a url clones into: the last segment, without a trailing `.git`. */
function targetName(url) {
    const trimmed = url.replace(/\/+$/, '').replace(/\/\.git$/, '');
    return (0, path_1.basename)(trimmed).replace(/\.git$/, '');
}
/**
 * True when the server refused over who is asking, not over which repo was asked for.
 *
 * The difference decides whether to keep going. A repo that does not exist costs that
 * one url. An account the server has stopped trusting costs every url after it too — and
 * on Bitbucket each further attempt counts as another failed login, so carrying on
 * digs the hole deeper. Measured against a real project: clones three and four went
 * through, then the account locked and the remaining ten each printed the same six-line
 * CAPTCHA notice.
 */
function refusesTheAsker(reason) {
    return /CAPTCHA|Authentication failed|could not read Username|could not read Password|Permission denied|403 Forbidden|401 Unauthorized/i
        .test(reason.join(' '));
}
/** Where to go and solve it, taken from the url that was refused. */
function serverHome(url) {
    try {
        return new URL(url).origin;
    }
    catch {
        return url;
    }
}
/**
 * How many times to stop and let someone unlock the account before giving up.
 *
 * Measured: each unlock lets two to four repos through before the server locks again, so
 * a project of a dozen needs three or four rounds. A cap keeps a server that will never
 * let go from turning the install into an Enter-pressing machine.
 */
const MAX_UNLOCK_PAUSES = 3;
/**
 * Wait for the person at the keyboard to say they have dealt with it.
 *
 * Synchronous on purpose: the whole install is, and making it asynchronous would force
 * `execInstall` — and the thirty tests calling it — to become asynchronous too (ADR D-1).
 * Reads one byte at a time until a newline; returns false when there is nothing to read
 * from, which is every case where nobody is watching.
 */
function waitForEnter() {
    // Read the terminal, not fd 0. An earlier prompt in the same run opens a readline
    // interface over stdin and closes it, after which `readSync(0, …)` returns zero bytes
    // at once instead of blocking — so a prompt built on fd 0 prints its question and falls
    // straight through, telling the person they have a choice they do not have. Measured on
    // Linux. `/dev/tty` is the same terminal and is unaffected; where there is none, fd 0
    // is still worth trying before giving up.
    for (const source of ['/dev/tty', 0]) {
        let fd;
        try {
            fd = typeof source === 'string' ? (0, fs_1.openSync)(source, 'r') : source;
            const byte = Buffer.alloc(1);
            for (;;) {
                const read = (0, fs_1.readSync)(fd, byte, 0, 1, null);
                if (read === 0)
                    break; // Nothing to read here — try the next source.
                if (byte[0] === 0x0a)
                    return true;
            }
        }
        catch {
            // No /dev/tty (Windows), or it cannot be opened: fall through to the next source.
        }
        finally {
            if (typeof source === 'string' && fd !== undefined)
                (0, fs_1.closeSync)(fd);
        }
    }
    return false;
}
/** Ask at the terminal, and only there. A script has nobody to ask. */
function askAtTerminal(left, home) {
    if (!process.stdin.isTTY)
        return false;
    console.log('');
    console.log('[vsaf] Máy chủ đang khoá tài khoản — thường là đòi giải CAPTCHA.');
    console.log(`[vsaf]   Mở ${home} trên trình duyệt, đăng nhập lại để giải.`);
    console.log(`[vsaf]   Xong thì bấm Enter để tải tiếp ${left} repo còn lại (Ctrl-C để dừng — chạy lại sau vẫn được).`);
    return waitForEnter();
}
/**
 * Put a personal access token on the wire for one git command, without writing it down.
 *
 * `GIT_CONFIG_*` applies to this child process and nothing else: the header never
 * reaches `~/.gitconfig`, never reaches the cloned repo's own config, and never appears
 * in the command line where `ps` would show it to every other user on the machine.
 * Measured after a clone made this way — the repo's `.git/config` held nothing but the
 * plain remote url.
 *
 * Whatever `GIT_CONFIG_*` the caller already exported is kept and appended to, because
 * replacing it would silently drop config a user set for this very run.
 */
function withToken(authorization) {
    const declared = Number.parseInt(process.env.GIT_CONFIG_COUNT ?? '0', 10);
    const count = Number.isInteger(declared) && declared > 0 ? declared : 0;
    return {
        ...process.env,
        GIT_CONFIG_COUNT: String(count + 1),
        [`GIT_CONFIG_KEY_${count}`]: 'http.extraHeader',
        [`GIT_CONFIG_VALUE_${count}`]: `Authorization: ${authorization}`,
    };
}
/**
 * The header forms worth trying for a credential, in order.
 *
 * A personal access token goes as `Bearer`; a username and password go as `Basic`. Nothing
 * tells the two apart by looking, and getting it wrong is not a small miss: the header is
 * refused, the probe falls back to the credential helper, and then **every clone asks for
 * the password again** — the twelve-prompt case, on a machine where the header was supposed
 * to prevent exactly that.
 *
 * A username present means a pair, so `Basic` leads. A bare secret can only be `Bearer`.
 */
function headerForms(credential) {
    const bearer = `Bearer ${credential.secret}`;
    if (!credential.username)
        return [bearer];
    const pair = `${credential.username}:${credential.secret}`;
    return [`Basic ${Buffer.from(pair, 'utf-8').toString('base64')}`, bearer];
}
/**
 * Ask a host one cheap question before cloning anything from it.
 *
 * Two answers come out of the single round trip.
 *
 * The first is whether the account is locked. Without asking, the installer finds out by
 * cloning — and on Bitbucket every failed clone counts as another failed login, so a
 * project of twelve repos spent twelve more attempts extending the very lock it was
 * reporting. Measured on a real project: four repos cloned, the fifth returned "CAPTCHA
 * required", and eight further attempts followed before the run stopped.
 *
 * The second is whether a header clears it. Cloning goes through the credential helper,
 * and the helper path is the one a CAPTCHA lock closes — while the same secret sent as a
 * header goes straight through. Measured on that locked account: plain `git ls-remote`
 * refused with the CAPTCHA notice, and the identical command carrying the credential in a
 * header answered in full. The secret is the same one the helper holds, so this costs the
 * user nothing and needs no token exported by hand.
 *
 * `ls-remote` rather than `clone`: one request, writes nothing, costs nothing to repeat.
 *
 * `lookUp` is false when the caller named a credential — including naming none — so a test
 * can say "pretend this machine holds nothing" without depending on what the machine it
 * runs on actually holds.
 */
function probeHost(url, cwd, token, lookUp = true) {
    // The store git itself would read, asked the way git asks it. Reached only when nothing
    // was handed in: someone who has cloned from this host before has an answer here, which
    // is the whole point — a CAPTCHA lock closes the helper path but not the header one, and
    // until now clearing it meant exporting a token by hand.
    // The same credential the repo-list read used — remembered per host, so a batch of
    // twelve clones asks once and then never again. Where nothing is stored and nobody is at
    // the keyboard this is still undefined, and cloning falls back to git's own asking.
    const held = token
        ? { secret: token }
        : (lookUp ? (0, credentials_js_1.credentialForHost)(url) : undefined);
    // Only an http url can carry a header, and only a credential that exists can fill one.
    for (const authorization of held && /^https?:/i.test(url) ? headerForms(held) : []) {
        const env = withToken(authorization);
        try {
            git(['ls-remote', url, 'HEAD'], cwd, env);
            // Which credential answered is not a decision the reader makes. It mattered while
            // the token path was new and unproven; now it is one more line between them and
            // the clone lines that follow.
            return { env, locked: false };
        }
        catch {
            // Wrong form, wrong server, or not allowed here. Try the other form; failing that,
            // the ambient credential may still work, so this is not yet a refusal to report.
        }
    }
    try {
        git(['ls-remote', url, 'HEAD'], cwd);
        return { locked: false };
    }
    catch (error) {
        // Only an account refusal stops the run. Anything else — a repo that is not there, a
        // host that is down — belongs to that one url, and the clone below reports it in
        // git's own words rather than blaming every url after it.
        const reason = gitReason(error);
        return refusesTheAsker(reason) ? { locked: true, reason } : { locked: false };
    }
}
/**
 * Clone the project's code repos into the directory beside the spec repo, which is
 * where the layout expects them.
 *
 * A repo already there is kept, never re-cloned over: it may hold work that is not
 * committed yet. A url that fails to clone is reported and skipped rather than
 * failing the whole install — the rest of the setup is still worth having.
 *
 * When the server refuses over the account rather than the repo, and someone is at the
 * keyboard, the run stops there and waits: unlocking takes a browser and half a minute,
 * and having to re-run the whole install afterwards — four times over, for a project of
 * twelve repos — is the part worth removing. `pause` is the seam that lets a test stand
 * in for that person.
 *
 * Returns the repos on disk afterwards, cloned or already present.
 */
function cloneCodeRepos(specRepo, urls, options = {}) {
    return cloneInto((0, path_1.dirname)(specRepo), urls, options);
}
/**
 * Clone repos into a directory named outright.
 *
 * Same work as `cloneCodeRepos`, which is this with the directory worked out from a spec
 * repo. Named separately because fetching repos is now its own command: someone joining a
 * project has no spec repo on disk yet — that is one of the things they are here to fetch —
 * so there is no repo to derive the parent from.
 */
function cloneInto(parent, urls, options = {}) {
    if (urls.length === 0)
        return [];
    const pause = options.pause ?? askAtTerminal;
    // Same rule as reading the repo list: the caller may name a token, and a caller that
    // says nothing means the environment's. A test passes `token: undefined` to say
    // "pretend there is none" without having to unset a variable the whole suite shares.
    const token = 'token' in options ? options.token : process.env.BITBUCKET_TOKEN;
    // Same convention as reading the repo list: a named credential is the only one tried.
    const lookUp = !('token' in options);
    const cloned = [];
    // One probe per host, not per url: twelve repos of one project are one server.
    const access = new Map();
    let pauses = 0;
    /**
     * What to do about a server that has stopped trusting this account.
     *
     * Either someone is here to unlock it and we go round again, or nobody is and the run
     * says what it got, what it did not, and how to finish it later.
     */
    const afterRefusal = (from, home) => {
        const missing = urls.slice(from)
            .map(targetName)
            .filter(name => !(0, fs_1.existsSync)((0, path_1.join)(parent, name)));
        if (pauses < MAX_UNLOCK_PAUSES && pause(missing.length, home)) {
            pauses += 1;
            // An unlock changes the answer every probe gave, so none of them can be trusted.
            access.clear();
            return 'retry';
        }
        console.log('');
        console.log('[vsaf] Dừng tải repo: máy chủ từ chối vì tài khoản, không phải vì repo.');
        console.log(`[vsaf]   Đã có ${cloned.length}/${urls.length} repo. Còn thiếu ${missing.length}: ${missing.join(', ')}`);
        console.log(`[vsaf]   Mở ${home} trên trình duyệt, đăng nhập lại (giải CAPTCHA nếu bị hỏi),`);
        console.log('[vsaf]   rồi chạy lại đúng lệnh này. Repo đã tải về được giữ nguyên, chỉ tải phần còn thiếu.');
        console.log('');
        return 'stop';
    };
    // Said before the first clone, once.
    if (mayAskForPassword(urls)) {
        offerCredentialHelper(urls.length);
        console.log('[vsaf] Đang tải repo — nếu thấy đứng im, xem cửa sổ nhỏ hỏi mật khẩu ở giữa màn hình IDE.');
    }
    for (let index = 0; index < urls.length; index += 1) {
        const url = urls[index];
        const target = (0, path_1.join)(parent, targetName(url));
        if ((0, fs_1.existsSync)(target)) {
            console.log(`[vsaf]   ${step(index, urls.length)} ${targetName(url)} — đã có, giữ nguyên`);
            cloned.push(target);
            continue;
        }
        const home = serverHome(url);
        let reach = access.get(home);
        if (!reach) {
            reach = probeHost(url, parent, token, lookUp);
            access.set(home, reach);
        }
        // Refused before a single clone was attempted, so the lock is not made worse by
        // finding out about it. Said once, for the host, rather than once per url.
        if (reach.locked) {
            console.log(`[vsaf] ⚠ ${home} chưa cho tải repo`);
            for (const line of reach.reason ?? [])
                console.log(`[vsaf]   ${line}`);
            if (afterRefusal(index, home) === 'retry') {
                index -= 1;
                continue;
            }
            break;
        }
        try {
            // Position, name, then where from. The position is what says it is working rather
            // than stuck while a large repo takes its time; the url is what lets someone check
            // they are pulling from the group they meant.
            console.log(`[vsaf]   ${step(index, urls.length)} ${targetName(url)} — ${url}`);
            git(['clone', '--quiet', url, target], parent, reach.env);
            cloned.push(target);
        }
        catch (error) {
            const reason = gitReason(error);
            console.log(`[vsaf]   ${step(index, urls.length)} ⚠ ${targetName(url)} — không tải được`);
            for (const line of reason)
                console.log(`[vsaf]   ${line}`);
            if (!refusesTheAsker(reason))
                continue;
            // It answered the probe and refuses now: the account locked partway through, so
            // what the probe learned about this host no longer holds.
            access.delete(home);
            if (afterRefusal(index, home) === 'retry') {
                index -= 1;
                continue;
            }
            break;
        }
    }
    return cloned;
}
//# sourceMappingURL=bootstrap-repo.js.map