#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const commander_1 = require("commander");
const promises_1 = require("readline/promises");
const fs_1 = require("fs");
const path_1 = require("path");
const delegate_js_1 = require("./commands/install/delegate.js");
const init_js_1 = require("./commands/init.js");
const bootstrap_repo_js_1 = require("./commands/install/bootstrap-repo.js");
const run_js_1 = require("./commands/run.js");
const doctor_js_1 = require("./commands/doctor.js");
const list_js_1 = require("./commands/list.js");
const status_js_1 = require("./commands/status.js");
const serve_js_1 = require("./commands/serve.js");
const mcp_js_1 = require("./commands/mcp.js");
const install_js_1 = require("./commands/install.js");
const apply_pack_js_1 = require("./commands/apply-pack.js");
const uninstall_js_1 = require("./commands/uninstall.js");
const bootstrap_repo_js_2 = require("./commands/install/bootstrap-repo.js");
const resolve_inputs_js_1 = require("./commands/install/resolve-inputs.js");
const prompt_read_js_1 = require("./commands/install/prompt-read.js");
const workspace_js_1 = require("./commands/install/workspace.js");
const sync_js_1 = require("./commands/sync.js");
/**
 * Ask for the project's code repos when the project was just created.
 *
 * A brand-new project has no siblings to list, so there is nothing to pick from — but
 * leaving the user to run a second command with a flag is the step they should not
 * have to remember. One question covers both cases: a url is cloned, a path on disk
 * is copied in.
 */
/**
 * Split what someone pasted into entries, however they pasted it.
 *
 * A comma between two links is how the prompt asks for them, so it is also how people type
 * them on the command line — and there the shell hands each word over separately, commas
 * still attached. `vsaf clone <a>, <b>` then asked the server for a project called
 * `PLATFORM,` and got a 404 naming a key nobody typed.
 */
function splitEntries(raw) {
    return raw
        .flatMap(part => part.split(','))
        .map(part => part.trim())
        .filter(Boolean);
}
/**
 * Ask what to fetch, for `clone`.
 *
 * Not the install's question: that one also accepts a directory already on disk, because
 * the install can adopt one. Fetching cannot — a path names something that is already here
 * — so offering it would be offering an answer this command drops on the floor.
 */
/**
 * Spec repos under a directory, at most two levels down.
 *
 * A spec repo is a directory carrying the artifact tree *and* the pack's wiring script —
 * both, because the tree alone means a project nobody has installed into yet, and that is
 * not something `--upgrade` can re-wire.
 *
 * Two levels because that is the shape the layout prescribes: `<project>/<project>-spec`.
 * Running the command from the folder above the project is the common slip, and one it can
 * recover from without asking anybody to `cd` first.
 */
function findSpecRepos(root, script) {
    const isSpec = (dir) => (0, fs_1.existsSync)((0, path_1.join)(dir, workspace_js_1.SPEC_REPO_MARKER)) && (0, fs_1.existsSync)((0, path_1.join)(dir, script));
    const children = (dir) => {
        try {
            return (0, fs_1.readdirSync)(dir, { withFileTypes: true })
                .filter(entry => entry.isDirectory() && !entry.name.startsWith('.')
                && entry.name !== 'node_modules')
                .map(entry => (0, path_1.join)(dir, entry.name));
        }
        catch {
            return [];
        }
    };
    const found = [];
    for (const first of children(root)) {
        if (isSpec(first)) {
            found.push(first);
            continue;
        }
        for (const second of children(first)) {
            if (isSpec(second))
                found.push(second);
        }
    }
    return found.sort();
}
/**
 * Which project to re-wire, when the command was not run inside one.
 *
 * It used to stop here: "không phải spec repo … cd vào spec repo rồi chạy lại". Correct, and
 * still work for the person to do — the tool can see the projects from where it is standing.
 * One found is used outright and named; several are offered; none is the only case left that
 * has to refuse.
 */
async function pickProject(root, script, pack) {
    const found = findSpecRepos(root, script);
    if (found.length === 0) {
        console.error(`[vsaf] Error: không thấy dự án ${pack} nào ở đây hay trong thư mục con.`);
        console.error(`[vsaf]   Cài lần đầu:  vsaf install ${pack}`);
        return undefined;
    }
    // Nobody to ask. One project is unambiguous; several are not, and picking for them is
    // exactly the kind of guess that wires the wrong repos.
    if (!process.stdin.isTTY) {
        if (found.length === 1) {
            console.log(`[vsaf] Dự án: ${(0, path_1.relative)(root, found[0])}`);
            return found[0];
        }
        console.error(`[vsaf] Error: có ${found.length} dự án ở đây — cd vào spec repo của dự án cần làm:`);
        for (const path of found)
            console.error(`[vsaf]     ${(0, path_1.relative)(root, path)}`);
        return undefined;
    }
    // The same question `--new` and `--clone` ask, in the same words: a name, typed. The list
    // is shown because these names are directories on disk, not something to remember — and a
    // number is accepted for the same reason. Enter takes the first, which is the whole answer
    // when there is only one.
    console.log(`\n[vsaf] Dự án ${pack} tìm thấy ở đây:`);
    found.forEach((path, at) => console.log(`[vsaf]   ${at + 1} ${(0, path_1.relative)(root, path)}`));
    const answer = await askForName('[vsaf] Tên dự án (hoặc số, Enter = dòng đầu): ');
    if (!answer)
        return found[0];
    const at = Number(answer);
    if (Number.isInteger(at) && at >= 1 && at <= found.length)
        return found[at - 1];
    // A name matches the project folder or the spec repo — people say either. `duan-a` and
    // `duan-a-spec` both mean the one project.
    const named = found.filter(path => (0, path_1.basename)(path) === answer || (0, path_1.basename)((0, path_1.dirname)(path)) === answer
        || (0, path_1.relative)(root, path) === answer);
    if (named.length === 1)
        return named[0];
    console.error(`[vsaf] Error: không có dự án nào tên "${answer}".`);
    return undefined;
}
/**
 * Everything someone joining a project has to do, in one command.
 *
 * They used to run four: fetch the repos, work out which of them is the spec repo, `cd`
 * into it, then install with `--refresh`. Each step only ever existed to reach the next
 * one, and the third was a guess — five directories arrive and only one is the place the
 * install can run.
 *
 * The spec repo is found, not guessed: the directory carrying the artifact tree is it. No
 * such directory means the group link did not include the spec repo, and that is worth
 * saying rather than papering over — nothing else in the folder can stand in for it.
 */
/**
 * Point at the workspace file, when there is one to point at.
 *
 * Read off disk (`workspaceFileIn`), not built from a name the code assumed: `--new` asks
 * for the project name separately from the folder, `--clone` infers it from the folder
 * someone typed, and either can be overridden with `--project-name`. A path built from the
 * wrong one of those points at a file that is not there — the exact bug this replaces
 * (screenshot from Ngọc Anh, 24/08: the printed path had the right shape but a project
 * name that would only ever be right by coincidence).
 *
 * Silent when there is none yet — greenfield with no code repo cloned, where NTAPP has
 * nothing to list and so generates none. A single-repo project needs no instruction for
 * opening its own folder; the earlier fallback line said so anyway and read as an
 * afterthought next to the other case (Ngọc Anh, same day: asked for it gone).
 */
function printOpenWorkspace(specRepo) {
    const file = (0, workspace_js_1.workspaceFileIn)(specRepo);
    if (!file)
        return;
    const where = (0, path_1.relative)(process.cwd(), specRepo);
    console.log(`[vsaf]   Đã hoàn thành cài đặt. Mở ${(0, path_1.join)(where, file)}, chọn Open workspace để bắt đầu.`);
}
/**
 * `--upgrade` is the one command that can write the workspace file into an IDE session
 * that is already open — creating it for the first time (single → multi-repo, the case
 * the docs already point people at `--upgrade` for) or adding a folder to one that
 * existed. Either way the file on disk just changed, and the open IDE will not show the
 * new folder until that file is reopened.
 *
 * Silent when nothing was actually fetched this run: `--upgrade` re-wiring a project's
 * already-known repos touches no folder in the workspace file, so there is nothing to
 * reopen for.
 */
function printWorkspaceUpdated(specRepo) {
    const file = (0, workspace_js_1.workspaceFileIn)(specRepo);
    if (!file)
        return;
    const where = (0, path_1.relative)(process.cwd(), specRepo);
    console.log(`[vsaf]   Đã thêm repo mới. Mở lại ${(0, path_1.join)(where, file)}, chọn Open workspace để IDE nhận đủ.`);
}
async function joinProject(pack, opts) {
    const folder = await askForName('[vsaf] Tên thư mục chứa dự án: ');
    if (!folder) {
        console.log('[vsaf] Chưa có tên thư mục.');
        return;
    }
    const parent = (0, path_1.resolve)(process.cwd(), folder);
    (0, fs_1.mkdirSync)(parent, { recursive: true });
    // Said before anything is fetched. A folder that already holds repos is a folder where
    // the wiring will claim them all as this project's — and finding that out after the
    // clones, from a guard, costs the download and reads as a bug in the command.
    const already = (0, workspace_js_1.resolveWorkspace)((0, path_1.join)(parent, 'x'), undefined, { assumeSpecRepo: true })
        .candidates.map(path => (0, path_1.relative)(parent, path));
    if (already.length > 0) {
        console.log(`[vsaf] ⚠ ${folder} đã có ${already.length} repo: ${already.join(', ')}`);
        console.log('[vsaf]   Nối dây sẽ coi hết chúng là code repo của dự án này.'
            + ' Muốn tách thì Ctrl-C rồi chạy lại với tên thư mục khác.');
    }
    const asked = await askWhatToClone();
    if (asked.length === 0) {
        console.log('[vsaf] Chưa có link nào để tải.');
        return;
    }
    const resolved = await (0, resolve_inputs_js_1.resolveInputs)(asked, { beside: parent });
    for (const path of resolved.adopt) {
        console.log(`[vsaf] ⚠ ${path} là đường dẫn trên máy, không phải thứ để tải — bỏ qua.`);
    }
    for (const { entry, reason } of resolved.unresolved) {
        console.log(`[vsaf] ⚠ Không lấy được gì từ ${entry} — ${reason}`);
    }
    const brought = (0, bootstrap_repo_js_2.cloneInto)(parent, resolved.clone);
    if (brought.length === 0) {
        console.log('[vsaf] Không repo nào được tải về.');
        return;
    }
    console.log(`[vsaf] Đã tải ${brought.length} repo vào ${(0, path_1.relative)(process.cwd(), parent) || '.'}`);
    const spec = brought.find(path => (0, fs_1.existsSync)((0, path_1.join)(path, workspace_js_1.SPEC_REPO_MARKER)));
    if (!spec) {
        console.log('[vsaf] ⚠ Không thấy spec repo trong số vừa tải (thư mục có NTAPP-output/).');
        console.log('[vsaf]   Chọn thêm spec repo của dự án rồi chạy lại, hoặc vào spec repo có sẵn'
            + ` và chạy: vsaf install ${pack} --refresh`);
        return;
    }
    console.log(`[vsaf] Spec repo: ${(0, path_1.relative)(process.cwd(), spec)}`);
    // The repos this very command just fetched, named as the scope guard wants them. Without
    // that the guard stops the install over siblings it "did not bring in" — which is exactly
    // what the lines above brought in, and it refuses with advice to pass a flag by hand.
    const codeRepos = brought
        .filter(path => path !== spec)
        .map(path => (0, path_1.relative)(spec, path));
    // Hỏi TRƯỚC lượt cài. Phần telemetry của config giờ do `install` bù vào — nó là chỗ
    // biết flow khai thư mục sản phẩm ở đâu — nên sau lượt cài, dấu hiệu "đã init chưa"
    // không còn phân biệt được nữa: mọi project vừa cài đều mang phần đó.
    const initStillOwed = !(0, delegate_js_1.isProjectInitialised)(spec);
    (0, install_js_1.execInstall)(pack, spec, {
        refresh: true,
        codeRepos: codeRepos.length > 0 ? codeRepos : undefined,
        refreshFlows: Boolean(opts.refreshFlows),
        verbose: Boolean(opts.verbose),
        passthrough: passthroughArgs(),
    });
    // Cấu hình project, cùng cách `--new` có nó: một bước mà thiếu đi cũng không ai thấy
    // là bước công cụ phải tự làm.
    //
    // `force` vì câu hỏi đã hỏi ở trên, lúc câu trả lời còn đúng: init CHƯA chạy ở đây.
    if (initStillOwed) {
        try {
            await (0, init_js_1.execInit)(spec, { force: true });
        }
        catch (error) {
            console.log(`[vsaf] ⚠ Chưa dựng được cấu hình dự án — ${error.message.split('\n')[0]}`);
            console.log(`[vsaf]   Chạy tiếp:  cd ${(0, path_1.relative)(process.cwd(), spec)} && vsaf init`);
        }
    }
    printOpenWorkspace(spec);
}
/**
 * Ask for a name at the terminal, or return nothing.
 *
 * `--new` and `--clone` both used to demand their argument on the command line, so the
 * shape of the command changed with what you were doing. One shape now: the command names
 * the job, everything it needs is asked afterwards.
 */
async function askForName(question) {
    if (!process.stdin.isTTY)
        return undefined;
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    try {
        const answer = await rl.question(question);
        return answer.trim() || undefined;
    }
    catch (error) {
        // A cut-off prompt is the person leaving, and the caller already says what it means
        // to have no name. Anything else is a name that was typed and lost, and reading that
        // as "nothing typed" tells the user something untrue about their own run.
        if (!(0, prompt_read_js_1.promptWasCutOff)(error)) {
            console.log(`[vsaf] ⚠ Không đọc được câu trả lời — ${(0, prompt_read_js_1.promptFailureReason)(error)}`);
        }
        return undefined;
    }
    finally {
        rl.close();
    }
}
async function askWhatToClone() {
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    let answer = '';
    try {
        // Màn hình này phải giống hệt màn hình của `askForCodeRepos()` (§2 Bước 3) từng dòng —
        // đó là hợp đồng tài liệu ghi rõ. Thiếu dòng mở đầu này là một trong ba chỗ lệch mà
        // nghiệm thu Linux đo được.
        console.log('\n[vsaf] Repo mã nguồn của dự án — dán url để clone, hoặc đường dẫn có sẵn trên máy.');
        console.log('[vsaf] Dán link nhóm dự án (…/projects/KEY) thì chọn repo trong nhóm ở bước sau.');
        answer = await rl.question('Nhiều repo/folder thì cách nhau bởi dấu phẩy (Enter để bỏ qua): ');
    }
    catch (error) {
        // Ctrl-D means "nothing", same as an empty line — and nothing more is owed there.
        // A read that failed for any other reason is a pasted link thrown away, so it is said
        // out loud with the command that picks the job back up.
        if (!(0, prompt_read_js_1.promptWasCutOff)(error)) {
            console.log(`[vsaf] ⚠ Không đọc được câu trả lời — ${(0, prompt_read_js_1.promptFailureReason)(error)}`);
            console.log('[vsaf]   Chưa nhận được link nào. Dán lại bằng:'
                + ' vsaf install <flow> --clone <link>');
        }
    }
    finally {
        rl.close();
    }
    return splitEntries([answer]);
}
async function askForCodeRepos() {
    if (!process.stdin.isTTY)
        return [];
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    let answer = '';
    try {
        console.log('\n[vsaf] Repo mã nguồn của dự án — dán url để clone, hoặc đường dẫn có sẵn trên máy.');
        console.log('[vsaf] Dán link nhóm dự án (…/projects/KEY) thì chọn repo trong nhóm ở bước sau.');
        answer = await rl.question('Nhiều repo/folder thì cách nhau bởi dấu phẩy (Enter để bỏ qua): ');
    }
    catch (error) {
        // Ctrl+D at the prompt means "none", not "abandon the install": the project
        // directory has already been created by this point. A read that failed some other
        // way still finishes the install — but silently calling it "none" would hide that
        // the repos named here never got as far as being tried.
        if (!(0, prompt_read_js_1.promptWasCutOff)(error)) {
            console.log(`[vsaf] ⚠ Không đọc được câu trả lời — ${(0, prompt_read_js_1.promptFailureReason)(error)}`);
            console.log('[vsaf]   Dự án vẫn được cài, chỉ thiếu code repo. Thêm sau bằng:'
                + ' vsaf install <flow> --clone <link>');
        }
    }
    finally {
        rl.close();
    }
    return splitEntries([answer]);
}
/**
 * Ask what to do with a repo that is already on the disk somewhere else.
 *
 * Two things can be meant by pasting a path, and they are not close: wire the repo
 * where it stands, or copy it into the project's directory. Copying was what happened
 * silently, and it is the surprising one — a working repo is often hundreds of
 * megabytes, uncommitted work lands in both copies, and from that moment the two are
 * free to drift apart while only one of them is wired.
 *
 * Asked only for a path someone pasted at the prompt, never for one typed after
 * `--adopt`: that flag says copy, and second-guessing a flag is its own kind of rude.
 * With nobody at the keyboard, the answer is the one that changes nothing on disk.
 */
async function askHowToAttach(paths, parent) {
    if (paths.length === 0 || !process.stdin.isTTY)
        return { copy: [], inPlace: paths };
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    let answer = '';
    try {
        console.log(`\n[vsaf] Đường dẫn có sẵn trên máy: ${paths.map(path => (0, path_1.basename)(path)).join(', ')}`);
        console.log('[vsaf]   [t] dùng tại chỗ — repo nằm nguyên chỗ cũ, chỉ nối dây (mặc định)');
        console.log(`[vsaf]   [c] copy vào ${(0, path_1.basename)(parent)}/ — repo bị nhân đôi trên đĩa, phần chưa commit cũng được copy`);
        answer = await rl.question('Chọn (t/c): ');
    }
    catch (error) {
        // Ctrl+D, or a closed pipe. The question has a safe answer, so an install that
        // reached this far finishes with it rather than dying at a prompt. Said either way,
        // because the fallback is a decision about the user's disk — with the reason attached
        // when it was not simply the prompt being closed.
        console.log('[vsaf] Không đọc được câu trả lời — dùng tại chỗ, không copy'
            + ((0, prompt_read_js_1.promptWasCutOff)(error) ? '' : ` (${(0, prompt_read_js_1.promptFailureReason)(error)})`));
    }
    finally {
        rl.close();
    }
    return answer.trim().toLowerCase().startsWith('c')
        ? { copy: paths, inPlace: [] }
        : { copy: [], inPlace: paths };
}
/**
 * Ask which of the repos found nearby belong to this project.
 *
 * The older script asked the same question. Replacing it with a mandatory flag kept
 * the safety — nothing is written into a repo nobody named — but made the command
 * something no one can remember. Asking gets both.
 *
 * Only when there is a terminal to ask at: a script or CI run falls back to the
 * flag, and writes nothing without it.
 */
async function askCodeRepos(pack, projectPath, options = {}) {
    const rewiring = options.rewiring === true;
    let candidates;
    let known;
    let packOwnsWiring;
    try {
        // Nội dung flow thật, không phải danh sách thư mục gói npm mang theo: một flow chỉ
        // sống trên repo từng rơi vào `catch` ở dưới và im lặng không hỏi gì.
        const packDir = flowDirOnThisMachine(pack, {
            allowFetch: options.allowFetch !== false,
            refresh: options.refresh === true,
        });
        if (!packDir)
            return undefined;
        // Only packs that generate a per-repo config have anything to wire.
        if (!(0, fs_1.existsSync)((0, path_1.join)(packDir, 'config', 'bmm-config.template.yaml')))
            return undefined;
        candidates = (0, workspace_js_1.resolveWorkspace)(projectPath).candidates;
        // What the project already claims, from its own committed workspace file.
        known = (0, workspace_js_1.reposInWorkspaceFile)(projectPath);
        packOwnsWiring = (0, skill_js_1.readPackInfoFrom)(packDir).wiring !== undefined;
    }
    catch {
        return undefined;
    }
    // Rewiring a pack that owns its wiring: do not ask, because the answer is not used.
    // The pack's script scans the parent directory itself and wires every repo it finds —
    // measured on NTAPP, `--upgrade --code-repos ../one-repo` wired all three siblings, and
    // the script takes no repo list on its command line at all. A question whose answer is
    // discarded is worse than no question: it reads as a choice, and the user who picks two
    // of five and gets five has been told something untrue.
    if (rewiring && packOwnsWiring) {
        // Said only when there is something to say. With nothing known, the install stops at
        // its own guard a moment later and asks for `--code-repos` — announcing "everything
        // beside the project will be wired" and then refusing to wire anything reads as a bug.
        if (known.length === 0)
            return undefined;
        console.log(`\n[vsaf] ${known.length} repo của dự án — nối lại hết.`
            + ' Script của pack tự quét thư mục cha, không lọc theo danh sách.');
        return known;
    }
    // Repos the project already listed are wired again without a word — that is what
    // `--upgrade` means, and asking someone to re-pick five repos because they cloned a
    // sixth is how an entry eventually gets dropped from the list.
    const fresh = candidates.filter(path => !known.includes(path));
    if (known.length > 0 && fresh.length === 0) {
        console.log(`\n[vsaf] ${known.length} repo mã nguồn của dự án — nối lại hết.`);
        return known;
    }
    // Nothing known and nobody to ask: as before, the caller names repos or none are wired.
    if (!process.stdin.isTTY)
        return known.length > 0 ? known : undefined;
    if (fresh.length === 0)
        return known.length > 0 ? known : undefined;
    console.log(known.length > 0
        ? `\n[vsaf] ${known.length} repo của dự án sẽ được nối lại. Còn repo chưa thuộc dự án:`
        : '\n[vsaf] Repo mã nguồn tìm thấy quanh đây:');
    fresh.forEach((path, i) => console.log(`    ${i + 1}) ${(0, workspace_js_1.candidateName)(projectPath, path)}`));
    const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
    let answer;
    try {
        answer = await rl.question('Repo nào thuộc dự án này? (vd: 1,2 · a = tất cả · Enter = bỏ qua): ');
    }
    finally {
        rl.close();
    }
    const picked = (0, workspace_js_1.parseRepoChoice)(answer, fresh, projectPath) ?? [];
    const all = [...known, ...picked.map(name => (0, path_1.resolve)(projectPath, name))];
    return all.length > 0 ? all : undefined;
}
const skill_js_1 = require("./commands/skill.js");
const engine_version_js_1 = require("./commands/install/engine-version.js");
const flow_source_js_1 = require("./commands/install/flow-source.js");
/**
 * Thư mục nội dung của một flow, đọc từ máy này.
 *
 * Một chỗ, vì bốn chỗ trong file này từng tự trả lời câu đó bằng danh sách thư mục gói
 * npm mang theo (`resolveSource` / `resolvePackInfo`), và câu trả lời đó lệch khỏi thứ
 * `vsaf install` vừa cài ngay khi repo flows có nội dung khác — sau bước 7.0, khi `skills/`
 * ra khỏi gói npm, nó không còn câu trả lời nào. Triệu chứng đã thấy: một flow chỉ sống
 * trên repo thì không được hỏi về code repo, và `vsaf skill init <flow>` ném
 * "Pack not found".
 *
 * `allowFetch` để `--dry-run` giữ được lời hứa không ghi gì: kéo flow về là ghi vào cache.
 *
 * Trả lời ĐÚNG BẰNG cách `execInstall` trả lời, không xấp xỉ:
 *
 * - Kéo được (`allowFetch`) thì đi qua `flowDirFor` — cùng bộ nhớ đệm `execInstall` dùng,
 *   nên một lệnh chỉ kéo một lần và cả hai bên đọc đúng một thư mục.
 * - Không kéo được (`--dry-run`) thì đọc `localFlowDir`, đúng thứ `execInstall` đọc ở
 *   nhánh chạy thử.
 *
 * Bản trước hỏi `localFlowDir` TRƯỚC rồi mới kéo, và đó là chỗ hai bên tách nhau ra:
 * `localFlowDir` là `cachedFlowDir ?? bundledFlowDir`, nên trên máy cache còn lạnh, ba
 * chỗ gọi ở đây trả lời bằng `skills/<pack>/pack.yaml` của gói npm trong khi
 * `execInstall` cài bản trên repo. Hôm nay hai bản giống nhau nên vô hại; sau khi repo
 * flows có nội dung riêng thì đó là hai câu trả lời khác nhau cho cùng một câu hỏi.
 *
 * `refresh` phải chuyển tiếp xuống, không được bỏ rơi: bỏ rơi thì lượt gọi ở đây kéo
 * bản thường, rồi `execInstall` kéo LẠI vì `--refresh-flows` chưa được dùng — đo được
 * 2 lượt clone trên cache lạnh cho `install <flow> --skip-deps --refresh-flows`.
 */
function flowDirOnThisMachine(pack, options) {
    // Trong một try: một tên không phải tên flow (`../khac`) bị chặn ngay, và ba câu hỏi
    // đi qua đây đều là câu hỏi phụ — câu lỗi đúng cho tên sai là câu `execInstall` in một
    // lát sau, không phải câu ở đây.
    try {
        if (!options.allowFetch)
            return (0, flow_source_js_1.localFlowDir)(pack);
        return (0, flow_source_js_1.flowDirFor)(pack, { refresh: options.refresh === true });
    }
    catch {
        return null;
    }
}
/** `pack.yaml` của flow, đọc từ máy này. */
function flowInfoOnThisMachine(pack, options) {
    const dir = flowDirOnThisMachine(pack, options);
    if (!dir)
        return undefined;
    try {
        return (0, skill_js_1.readPackInfoFrom)(dir);
    }
    catch {
        return undefined;
    }
}
/**
 * What the pack declares, or nothing when this machine cannot read it yet.
 *
 * `resolvePackInfo` only knows two places: the packs shipped inside the npm package, and
 * a pack already installed in the project. A flow that lives only in the flows repo is in
 * neither until `execInstall` fetches it — so asking here threw "Pack not found. Available:
 * …" and refused the install before the fetch ever happened. Measured against a flow that
 * existed only in the repo: the command died at that line every time.
 *
 * The three questions asked through this helper all mean "does this pack lay a project out
 * around itself", and a pack this machine has never seen is answered no. That is also what
 * happens today for every pack without a wiring policy, so nothing shipped changes: all
 * four bundled packs are still read exactly as before. A name that is simply a typo is not
 * swallowed either — `execInstall` refuses it a moment later, and lists the flows the repo
 * actually has, which is the more useful list of the two.
 */
function packInfoIfKnown(pack, projectPath, options = {}) {
    // Nội dung flow trước, `.claude/skills/<pack>/pack.yaml` của dự án sau: chỗ thứ hai là
    // bản đã cài, còn chỗ thứ nhất là bản sắp cài — và ba câu hỏi đi qua đây đều hỏi về bản
    // sắp cài. Cả ba lượt gọi đều nằm ngoài `--dry-run`, nên kéo flow ở đây là hợp lệ, và
    // lượt kéo được nhớ lại nên `install` bên dưới không đi thêm vòng nào.
    const fromFlow = flowInfoOnThisMachine(pack, { allowFetch: true, refresh: options.refresh === true });
    if (fromFlow)
        return fromFlow;
    try {
        return (0, skill_js_1.resolvePackInfo)(pack, projectPath);
    }
    catch {
        return undefined;
    }
}
const program = new commander_1.Command();
program
    .name('vsaf')
    .description('DAG-based workflow engine for AI coding agents')
    .version((0, engine_version_js_1.resolveEngineVersion)());
program
    .command('init')
    .description('Initialize .vsaf/ in current project — directories only, no flow')
    .option('--key <key>', 'AI Gateway virtual key (prompted for if omitted)')
    .option('--force', 'Reinitialize an existing .vsaf/ — keep docs/, storage/ and config.yaml')
    // Cờ vẫn đăng ký dù không còn tác dụng. Xoá trần thì commander đáp "unknown option
    // --pack" — người có script cũ đọc câu đó ra là mình gõ sai chữ, chứ không ra là phân
    // vai đã đổi. Giữ cờ để nói được lý do.
    .option('--pack <name>', 'Không còn dùng — cài flow bằng `vsaf install <flow>`')
    .action(async (opts) => {
    // `vsaf init` không cài flow nữa: nó dựng thư mục cho dự án, và `vsaf install
    // <flow>` là chỗ cài skill với workflow. `--pack` giờ chỉ để nói ra điều đó — lý do
    // vì sao nói ra rồi vẫn chạy tiếp (thay vì im lặng bỏ qua, hay từ chối cả lệnh) nằm
    // ở chú thích ngay dưới đây.
    if (opts.pack !== undefined) {
        const asked = String(opts.pack);
        // Nói rõ rồi vẫn làm, chứ không từ chối cả lệnh.
        //
        // Từ chối là hành vi trước đó, và lý do của nó vẫn đúng: im lặng bỏ qua một cờ
        // người dùng gõ là kiểu hỏng tệ nhất. Nhưng câu `vsaf init --pack NTAPP` là lệnh
        // cứu hộ được in ra cho người dùng khi telemetry lỗi (tài liệu NTAPP §6), nên từ
        // chối nó là chặn đúng đường thoát. Đường giữa giữ được cả hai: cờ được nói ra là
        // không còn cần, và việc người dùng cần vẫn xảy ra.
        console.log('[vsaf] Cờ --pack không còn cần thiết — `vsaf init` chỉ dựng thư mục cho dự án.');
        console.log(asked === 'none'
            ? '[vsaf]   Bỏ hẳn cờ này đi: không cài gì vốn là việc `vsaf init` làm.'
            : `[vsaf]   Cài flow bằng lệnh riêng:  vsaf install ${asked}`);
    }
    try {
        let gatewayKey = opts.key;
        if (init_js_1.GATEWAY_ENV_ENABLED && !gatewayKey?.trim() && !(0, init_js_1.hasGatewayToken)(process.cwd()) && process.stdin.isTTY) {
            const rl = (0, promises_1.createInterface)({ input: process.stdin, output: process.stdout });
            try {
                gatewayKey = await rl.question('AI Gateway virtual key (https://ai-gateway.viettel.digital): ');
            }
            finally {
                rl.close();
            }
        }
        await (0, init_js_1.execInit)(process.cwd(), { gatewayKey, force: Boolean(opts.force) });
        // Một dòng, vì bước tiếp theo không đoán ra được từ những gì `init` vừa ghi: thư
        // mục đã dựng xong nhưng chưa có skill nào, và người mới không biết vì sao.
        console.log('[vsaf] Đã dựng .vsaf/ cho dự án. Bước tiếp theo — cài flow:  vsaf install <tên flow>');
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program
    .command('run <workflow>')
    .description('Execute a workflow')
    .option('--args <args>', 'Arguments to pass to the workflow', '')
    .option('--resume <runId>', 'Resume an interrupted workflow run')
    .action(async (workflow, opts) => {
    try {
        await (0, run_js_1.execRun)(workflow, process.cwd(), { args: opts.args, resume: opts.resume });
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program
    .command('doctor')
    .description('Check environment and dependencies')
    .action(async () => {
    const results = await (0, doctor_js_1.runChecks)(process.cwd());
    console.log((0, doctor_js_1.formatChecks)(results));
});
program
    .command('list')
    .description('List available workflows')
    .action(() => {
    const workflows = (0, list_js_1.listWorkflows)(process.cwd());
    if (workflows.length === 0) {
        console.log('No workflows found. Run "vsaf init" first.');
        return;
    }
    for (const wf of workflows) {
        console.log(`  ${wf.name.padEnd(25)} ${wf.description}`);
    }
});
program
    .command('status')
    .description('Show workflow run statuses, and which flow version this project runs')
    .action(() => {
    // Bản flow trước: nó là thứ hiếm khi đổi và thường là thứ đang cần đối chiếu giữa hai
    // máy. Danh sách lượt chạy có thể dài, và một dòng đứng sau nó là một dòng phải cuộn.
    const flows = (0, status_js_1.formatFlowVersions)(process.cwd());
    if (flows)
        console.log(`${flows}\n`);
    const runs = (0, status_js_1.getRunStatuses)(process.cwd());
    console.log((0, status_js_1.formatStatuses)(runs));
});
program
    .command('serve')
    .description('Start API server and web dashboard')
    .option('--port <port>', 'Port number', '3000')
    .option('--open', 'Auto-open browser', false)
    .action(async (opts) => {
    try {
        await (0, serve_js_1.execServe)(process.cwd(), { port: parseInt(opts.port, 10), open: opts.open });
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program
    .command('mcp')
    .description('Start MCP server for Claude integration')
    .action(async () => {
    try {
        await (0, mcp_js_1.execMCP)();
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
/**
 * Everything after a bare `--`, for a pack whose own script owns some of the flags.
 *
 * Read from argv rather than through the option parser: the point is to pass along
 * flags this CLI has never heard of, and anything that parses them first would reject
 * them before they got there.
 */
function passthroughArgs() {
    const marker = process.argv.indexOf('--');
    return marker === -1 ? [] : process.argv.slice(marker + 1);
}
program
    .command('sync <pack>')
    .description("Push a pack's skills and coding rules to the tool directories under your home")
    .option('--dry-run', 'Show what would be written and write nothing', false)
    .option('--skills-only', 'Skills only, leave the coding rules alone', false)
    .option('--rules-only', 'Coding rules only, leave the skills alone', false)
    .option('--clean', 'Also drop skills the pack no longer ships', false)
    .option('--verbose', "Print the pack's sync script in full", false)
    .action((pack, opts) => {
    try {
        (0, sync_js_1.execSync)(pack, {
            dryRun: opts.dryRun,
            skillsOnly: opts.skillsOnly,
            rulesOnly: opts.rulesOnly,
            clean: opts.clean,
            verbose: opts.verbose,
            passthrough: passthroughArgs(),
        });
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program
    .command('uninstall <pack>')
    .description('Remove an installed skill pack from the current project')
    .option('--global', 'Also remove what the pack wrote outside the project', false)
    .action((pack, opts) => {
    try {
        (0, uninstall_js_1.execUninstall)(pack, process.cwd(), { global: opts.global });
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program
    .command('apply-pack <dir>')
    .description("Deploy a flow from a directory on disk — called by a flow's own install script")
    .option('--project <path>', 'Project to install into (default: this directory)')
    .option('--force', 'Overwrite existing skills', false)
    .option('--skip-deps', 'Skip npm dependency installation', false)
    .option('--skip-graphify', 'Bỏ qua bước cài graphify (nó ghi ra ngoài dự án, và chỉ cần cài một lần)', false)
    .option('--dry-run', 'Show what would happen and write nothing', false)
    .option('--verbose', "Print the pack's wiring script in full, not just its warnings", false)
    .option('--project-root', 'Confirm this directory is the project root even though it holds code', false)
    .action((dir, opts) => {
    try {
        const result = (0, apply_pack_js_1.execApplyPack)(dir, opts.project ?? process.cwd(), {
            force: opts.force,
            skipDeps: opts.skipDeps,
            _skipGraphify: opts.skipGraphify,
            dryRun: opts.dryRun,
            verbose: opts.verbose,
            projectRoot: opts.projectRoot,
        });
        // Cùng luật với `install`: lượt cài mà tự kiểm thấy thủng lỗ không phải lượt cài
        // thành công. Thiếu dòng này thì đây là lệnh mà script của mọi flow gọi, và nó
        // báo về "xong" kể cả khi vừa để lại một project hỏng.
        if (result.problems.length > 0)
            process.exit(1);
    }
    catch (error) {
        console.error(`[vsaf] ${error.message}`);
        process.exit(1);
    }
});
program
    .command('install <pack>')
    .description('Install a skill pack (deploys to .claude/skills/ in current project)')
    .option('--force', 'Overwrite existing skills', false)
    .option('--skip-deps', 'Skip npm dependency installation', false)
    .option('--sync-global', "Also copy the pack's skills into your other tools under ~ (off by default)", false)
    .option('--code-repos <names>', 'Comma-separated sibling code repos to wire to this spec repo (generates .bmm-config.yaml + skill link)')
    .option('--project-name <name>', 'Project name for the workspace file (default: this directory, minus -spec/-doc)')
    .option('--clone [urls]', 'Fetch code repos and wire them. Bare: asks for the folder name, the group link, '
    + 'then which repos — one command for someone joining a project')
    .option('--adopt <paths>', 'Comma-separated code repos already on disk to COPY beside this project, then wire '
    + '(the original stays put; to wire one where it stands instead, pass its path to --code-repos)')
    .option('--project-root', 'Confirm this directory is the project root even though it holds code', false)
    .option('--refresh', 'Joining a project already set up: recreate only machine-local files', false)
    .option('--upgrade', 'Project gained code repos since setup: re-wire everything but its name', false)
    .option('--dry-run', 'Show what would happen and write nothing', false)
    .option('--refresh-flows', 'Xoá cache flow trên máy và tải lại từ đầu', false)
    .option('--verbose', "Print the pack's wiring script in full, not just its warnings", false)
    .option('--new [name]', 'Create <name>/<name>-spec here, initialise it, and install into it')
    .action(async (pack, opts) => {
    try {
        // Kiểm môi trường trước khi hỏi hay ghi bất cứ thứ gì — tài liệu §2 Bước 1.
        //
        // Trước đây nó nằm trong `installDelegated`, tức SAU khi đã hỏi tên và đã tạo thư
        // mục: máy thiếu bash thì người dùng trả lời xong hai câu hỏi rồi mới thấy lệnh
        // chết, và thư mục dở dang nằm lại. Biết flow có cần bash hay không đòi đọc
        // `pack.yaml` của flow, nên bước lấy flow đứng trước — đó cũng là hỏng nhanh: mất
        // mạng thì dừng trước khi hỏi.
        if (!opts.dryRun) {
            const info = packInfoIfKnown(pack, process.cwd(), { refresh: opts.refreshFlows });
            if (info?.wiring)
                (0, delegate_js_1.checkEnvironment)();
        }
        // `--new` makes the tool lay the project out, instead of asking for a mkdir and
        // a separate init first.
        let target = process.cwd();
        // Set when the pack brings its own project skeleton, so `install` leaves the
        // project-level setup to a `vsaf init` run of its own, after the wiring.
        let madeProject = false;
        let packBringsSkeleton = false;
        // A bare `--new` asks for the name instead of refusing the command.
        if (opts.new === true) {
            opts.new = await askForName('[vsaf] Tên dự án: ');
            if (!opts.new) {
                console.log('[vsaf] Chưa có tên dự án.');
                return;
            }
        }
        // A bare `--clone` is the whole job for someone joining a project: name a folder,
        // paste the group link, pick the repos, and let it wire what it fetched. Four steps
        // in one command, because the four were only ever done together.
        if (opts.clone === true) {
            await joinProject(pack, opts);
            return;
        }
        let pasted = typeof opts.clone === 'string'
            ? opts.clone.split(',').map((u) => u.trim()).filter(Boolean)
            : undefined;
        let adopt = opts.adopt?.split(',').map((p) => p.trim()).filter(Boolean);
        if (opts.new && opts.dryRun) {
            // `--dry-run` promises nothing is written, and that has to hold for the
            // project directory too — creating it and initialising it before the plan
            // even runs is the loudest possible way to break that promise.
            target = (0, path_1.join)(target, opts.new, `${opts.new}-spec`);
            console.log(`[vsaf] Would create ${(0, path_1.relative)(process.cwd(), target)}`);
        }
        else if (opts.new) {
            target = (0, bootstrap_repo_js_2.prepareNewProject)(target, opts.new);
            // Remembered because the last step of this branch amends the project's only commit,
            // and that is only ever ours to amend: `--clone` and `--upgrade` sit on history
            // somebody else pushed.
            madeProject = true;
            // Running the same command again is how a half-finished install is finished,
            // so a project that is already there is carried on rather than refused. It
            // used to stop at `.vsaf/ already exists, pass --force` — which left the one
            // command the user had been told to re-run as the one command that could not
            // be re-run. Reinitialising keeps docs/, storage/ and config.yaml.
            const already = (0, fs_1.existsSync)((0, path_1.join)(target, '.vsaf'));
            // A pack that carries its own project skeleton is not initialised here. Running
            // `init` first created a two-line `.gitignore`, and the copy then declined to
            // overwrite it, so the pack's own sixty-line one never arrived. Such a pack is
            // initialised after the wiring instead — one command per job, and the ordering
            // falls out right.
            packBringsSkeleton = packInfoIfKnown(pack, target, { refresh: opts.refreshFlows })?.wiring !== undefined;
            if (!packBringsSkeleton) {
                await (0, init_js_1.execInit)(target, { force: already });
            }
            console.log(already
                ? `[vsaf] ${(0, path_1.relative)(process.cwd(), target)} đã có sẵn — chạy tiếp phần còn thiếu`
                : `[vsaf] Created ${(0, path_1.relative)(process.cwd(), target)}`);
            // Nothing named on the command line, and a new project has no siblings to
            // list — so ask, rather than leave a second command to remember.
            if (!pasted && !adopt && !opts.codeRepos) {
                const asked = await askForCodeRepos();
                pasted = asked.length > 0 ? asked : undefined;
            }
        }
        // Refuse a re-wire of somewhere that is not a project — before asking anything.
        //
        // The check already existed, but downstream: `--upgrade` asked for a link, fetched
        // the repos, and only then reported "chưa cài pack". Run from the wrong directory —
        // one above the spec repo, say — that cost a download and read as a bug in the
        // command rather than a wrong `cd`.
        if ((opts.refresh === true || opts.upgrade === true) && !opts.dryRun) {
            const script = packInfoIfKnown(pack, target, { refresh: opts.refreshFlows })?.wiring?.script;
            if (script && !(0, fs_1.existsSync)((0, path_1.join)(target, script))) {
                const picked = await pickProject(target, script, pack);
                if (!picked)
                    process.exit(1);
                target = picked;
            }
        }
        // `--upgrade` means the project gained repos, so ask which — the same question
        // `--new` and `--clone` ask, in the same order: command first, input after. Nothing
        // named and nobody at the keyboard leaves it as it was, re-wiring what is already
        // beside the project.
        if (opts.upgrade === true && !pasted && !adopt && !opts.codeRepos && !opts.dryRun
            && process.stdin.isTTY) {
            const asked = await askWhatToClone();
            pasted = asked.length > 0 ? asked : undefined;
        }
        // A project link stands for every repo in it, so it is expanded here, where waiting
        // for the answer is allowed — the install itself stays synchronous.
        // `beside` is where code repos land, so the picker can mark the ones already there
        // — the spec repo itself is usually one of them.
        const resolved = await (0, resolve_inputs_js_1.resolveInputs)(pasted ?? [], { beside: (0, path_1.dirname)(target) });
        const clone = resolved.clone.length > 0 ? resolved.clone : undefined;
        // Carried to the end of the install, with the command that finishes the job.
        // Said only up front, it is a hundred lines above the last thing on screen.
        const where = (0, path_1.relative)(process.cwd(), target);
        // One entry per thing that did not happen, however many lines it takes to say:
        // the summary counts these as issues, and counting lines would inflate it.
        const unresolved = resolved.unresolved.map(({ entry, reason }) => {
            // No `export BITBUCKET_TOKEN=<token> &&` in front of it any more. That line was
            // shell redirection, so pasting it either errored or set an empty value — and the
            // command below now asks for the token itself when the machine holds none.
            const needsToken = reason.includes('credential');
            // First sentence only. The full reason — with what to do about it — was printed
            // where it happened; repeating all of it in the closing summary put the same long
            // paragraph on screen twice, and glued a second full stop onto the first.
            const why = reason.split('. ')[0].replace(/\.$/, '');
            return `Chưa lấy được repo nào từ ${entry} — ${why}. Dự án cài xong rồi, chỉ thiếu code repo.`
                + `\n[vsaf]     ${needsToken ? 'Có credential rồi thì chạy' : 'Sửa xong rồi chạy'}: `
                + `${where ? `cd ${where} && ` : ''}`
                + `vsaf install ${pack} --clone ${entry}`;
        });
        // A path pasted into the clone box is still a path, and `--adopt` still means
        // adopt. What the pasted one does not say is whether the repo should move, so
        // that is asked rather than assumed.
        const pastedPaths = resolved.adopt.map(path => (0, path_1.resolve)(process.cwd(), path));
        const attach = await askHowToAttach(pastedPaths, (0, path_1.dirname)(target));
        const toAdopt = [...(adopt ?? []), ...attach.copy];
        const named = opts.codeRepos?.split(',').map((name) => name.trim()).filter(Boolean);
        // Repos staying where they are join the named ones: resolution takes an absolute
        // path as a name, so nothing else has to know the difference.
        const rewiring = opts.refresh === true || opts.upgrade === true;
        const codeRepos = [
            ...(named ?? await askCodeRepos(pack, target, {
                rewiring, allowFetch: !opts.dryRun, refresh: opts.refreshFlows,
            }) ?? []), ...attach.inPlace,
        ];
        if (!opts.dryRun) {
            packBringsSkeleton = packInfoIfKnown(pack, target, { refresh: opts.refreshFlows })?.wiring !== undefined;
        }
        // Hỏi TRƯỚC lượt cài, lúc câu trả lời còn đúng. Phần telemetry của config giờ do
        // `install` bù vào — nó là chỗ biết flow khai thư mục sản phẩm ở đâu — nên hỏi sau
        // lượt cài thì project nào cũng đọc ra là "đã init rồi", kể cả project chưa bao giờ
        // chạy `init`.
        const initStillOwed = packBringsSkeleton && !opts.dryRun && !(0, delegate_js_1.isProjectInitialised)(target);
        const result = (0, install_js_1.execInstall)(pack, target, {
            force: opts.force,
            skipDeps: opts.skipDeps,
            syncGlobal: opts.syncGlobal,
            codeRepos: codeRepos.length > 0 ? codeRepos : undefined,
            projectName: opts.projectName,
            clone,
            adopt: toAdopt.length > 0 ? toAdopt : undefined,
            projectRoot: opts.projectRoot,
            refresh: opts.refresh,
            upgrade: opts.upgrade,
            dryRun: opts.dryRun,
            refreshFlows: opts.refreshFlows,
            verbose: opts.verbose,
            passthrough: passthroughArgs(),
            unresolved,
        });
        // Dựng cấu hình project ở đây, không để lại thành một lệnh người dùng phải nhớ.
        //
        // Every other pack already gets this: `install --new` calls `init` for any pack
        // without its own wiring script. NTAPP was the single exception, and for a reason
        // that was about ordering rather than about scope — `init` running BEFORE the copy
        // wrote a two-line `.gitignore`, the copy then declined to overwrite it, and the
        // pack's own sixty-line one never arrived. Running it AFTER the wiring has neither
        // problem: both files it touches are merged, not rewritten — `.mcp.json` gains only
        // the keys it lacks, and `.claude/settings.json` keeps the hooks block the pack's
        // script just merged in.
        //
        // Without it nothing errors anywhere: the pack ships a `.vsaf/config.yaml` with no
        // SessionStart hook and no `.mcp.json`, `doctor` reports a green tick, and every run
        // of the flow goes silent. A step whose absence is invisible is a step a tool should
        // take itself.
        //
        // `force` vì câu hỏi đã hỏi trước lượt cài, lúc câu trả lời còn đúng: init CHƯA chạy
        // ở đây.
        if (initStillOwed) {
            try {
                await (0, init_js_1.execInit)(target, { force: true });
            }
            catch (error) {
                // A wired project is a successful install. The project config is the last step
                // and the least of them, so its failure reports itself and names the command to
                // retry — it does not undo everything above it.
                console.log(`[vsaf] ⚠ Chưa dựng được cấu hình dự án — ${error.message.split('\n')[0]}`);
                console.log('[vsaf]   Chạy tiếp:  vsaf init');
            }
        }
        // The wiring set the project's real name, `install` wrote the flow's artifact paths
        // into the telemetry section, and `init` wrote the SessionStart hook and `.mcp.json`
        // — all of it after the commit made back at step 2/4, which is
        // made that early because the wiring installs a pre-commit hook that refuses this
        // repo's own files. Fold the lot into that commit, so what a lead pushes is the
        // project as it stands. Measured before this existed: the pushed commit still said
        // `# Project: NTAPP (VSAF Blended)`, and every teammate's `--clone` then stopped at
        // the pack's self-test, with nothing wrong on the lead's own machine.
        if (madeProject && !opts.dryRun)
            (0, bootstrap_repo_js_1.refreshInitialCommit)(target);
        // Last, where it is still on screen.
        //
        // The classic install path ends with its own summary and prints these there. The
        // pack path has no such summary: it ended on "Xong.", which reads as "everything you
        // asked for happened" — while the one line saying a project link could not be read
        // scrolled off two hundred lines earlier. So an install that failed to bring twelve
        // repos looked exactly like one that brought them.
        if (packBringsSkeleton && !opts.dryRun) {
            for (const line of unresolved)
                console.log(`[vsaf] ⚠ ${line}`);
        }
        // Machine scope stays a separate command: `sync` writes under $HOME, and a project
        // install reaching outside the project is a surprise nobody asked for. Naming it is
        // enough — the install itself succeeded.
        // Thư mục flow mà lượt cài vừa dùng, do chính nó trả về. Trước đây chỗ này đếm skill
        // của bản kèm gói npm để khuyên về bản vừa cài từ repo — hai bản khác nhau, một con số.
        // Đọc trong try riêng: lượt cài đã xong và đã thành công, nên một `pack.yaml` đọc
        // không ra ở đây không được phép biến nó thành một lệnh báo lỗi.
        let installedFlow;
        try {
            if (result.flowDir)
                installedFlow = { dir: result.flowDir, info: (0, skill_js_1.readPackInfoFrom)(result.flowDir) };
        }
        catch { /* không đọc được thì bỏ câu nhắc, không làm hỏng lượt cài */ }
        const pending = packBringsSkeleton && !opts.dryRun && installedFlow !== undefined
            && (0, delegate_js_1.warnIfSkillsNotSynced)(installedFlow.dir, installedFlow.info, pack);
        if (packBringsSkeleton && !opts.dryRun && !pending) {
            // The next thing to do, not a report that the last thing finished. `--refresh`
            // leaves the person where they already were, so there is nothing to say there.
            if (opts.new || opts.clone) {
                printOpenWorkspace(target);
            }
            else if (opts.upgrade && result.wired.length > 0) {
                printWorkspaceUpdated(target);
            }
        }
        // An install the self-test found holes in is not a successful install. It used
        // to print the holes and exit 0, so anything scripted around it carried on.
        if (result.problems.length > 0)
            process.exit(1);
    }
    catch (err) {
        // The installer reports its own failures in full — where it stopped, what is
        // done, and the command that finishes it. Repeating the bare message after that
        // buries the part worth reading.
        const error = err;
        if (!error.reported)
            console.error(`[vsaf] Error: ${error.message}`);
        process.exit(1);
    }
});
const skillCmd = program
    .command('skill')
    .description('Manage skills');
skillCmd
    .command('add <source>')
    .description('Install skill from local path, git URL, or built-in pack')
    .option('--only <names>', 'Only install specific skills (comma-separated)', (val) => val.split(','))
    .option('--force', 'Overwrite existing skills', false)
    .action((source, opts) => {
    try {
        const result = (0, skill_js_1.skillAdd)(source, process.cwd(), { only: opts.only, force: opts.force });
        for (const name of result.added)
            console.log(`[vsaf] Added: ${name}`);
        for (const name of result.skipped)
            console.log(`[vsaf] Skipped: ${name} (already exists)`);
        console.log(`[vsaf] ${result.added.length} skills installed`);
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
skillCmd
    .command('list')
    .description('List installed skills')
    .action(() => {
    const skills = (0, skill_js_1.skillList)(process.cwd());
    if (skills.length === 0) {
        console.log('No skills installed. Run "vsaf skill add <source>" to install.');
        return;
    }
    console.log('NAME'.padEnd(20) + 'DESCRIPTION'.padEnd(35) + 'FILES  LINKED');
    for (const s of skills) {
        const linked = s.linkedCommand ? `✓ ${s.linkedCommand}` : '✗';
        console.log(`${s.name.padEnd(20)}${s.description.padEnd(35)}${String(s.fileCount).padEnd(7)}${linked}`);
    }
});
skillCmd
    .command('info <name>')
    .description('Show skill details')
    .action((name) => {
    try {
        const info = (0, skill_js_1.skillInfo)(name, process.cwd());
        console.log(`Name:         ${info.name}`);
        console.log(`Description:  ${info.description}`);
        if (info.version)
            console.log(`Version:      ${info.version}`);
        if (info.author)
            console.log(`Author:       ${info.author}`);
        console.log(`\nFiles:`);
        for (const f of info.files)
            console.log(`  ${f}`);
        if (info.linkedCommands.length > 0) {
            console.log(`\nUsed by:`);
            for (const c of info.linkedCommands)
                console.log(`  ${c}`);
        }
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
skillCmd
    .command('remove <name>')
    .description('Remove an installed skill')
    .action((name) => {
    try {
        const result = (0, skill_js_1.skillRemove)(name, process.cwd());
        if (result.warnings.length > 0) {
            console.log(`[vsaf] Warning: these commands reference the removed skill:`);
            for (const w of result.warnings)
                console.log(`  ${w}`);
        }
        console.log(`[vsaf] Removed skill: ${result.removed}`);
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
skillCmd
    .command('init <pack>')
    .description('Scaffold commands and workflows for a skill pack')
    .action((pack) => {
    try {
        // Qua repo flows như `install`: nếu không, `vsaf skill init <flow>` ném
        // "Pack not found" cho đúng những flow mà `vsaf install <flow>` vừa cài xong.
        const packInfo = flowInfoOnThisMachine(pack, { allowFetch: true })
            ?? (0, skill_js_1.resolvePackInfo)(pack, process.cwd());
        // Same transformation as `vsaf init`: commands must reference the
        // DEPLOYED (prefixed) skill names, or workflows' `command:` nodes and
        // the skill lookup both miss. `setup` is install-time only.
        const prefixedNames = packInfo.skillNames
            .filter(n => n !== 'setup')
            .map(n => `${pack}-${n}`);
        const result = (0, skill_js_1.skillInit)(pack, process.cwd(), prefixedNames, { workflows: packInfo.workflows });
        for (const c of result.commandsCreated)
            console.log(`[vsaf] Created command: commands/${c}.md (→ skill: ${c})`);
        for (const c of result.commandsSkipped)
            console.log(`[vsaf] Skipped command: commands/${c}.md (already exists)`);
        for (const w of result.workflowsCreated)
            console.log(`[vsaf] Created workflow: workflows/${w}`);
        console.log(`[vsaf] ${result.commandsCreated.length} commands + ${result.workflowsCreated.length} workflows created`);
        if (result.commandsCreated.length > 0) {
            console.log(`[vsaf] → Edit commands/ files to add project-specific context`);
        }
    }
    catch (err) {
        console.error(`[vsaf] Error: ${err.message}`);
        process.exit(1);
    }
});
program.parse();
//# sourceMappingURL=index.js.map