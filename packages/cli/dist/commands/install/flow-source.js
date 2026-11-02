"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_FLOW_TIMEOUT_MS = exports.DEFAULT_FLOWS_REPO = exports.flowsCacheDir = exports.cachedFlowDir = exports.assertFlowName = void 0;
exports.flowsRepoTarget = flowsRepoTarget;
exports.flowsRepoUrl = flowsRepoUrl;
exports.maskUrl = maskUrl;
exports.gitAuthEnv = gitAuthEnv;
exports.bundledFlowDir = bundledFlowDir;
exports.localFlowDir = localFlowDir;
exports.gitCanSparseFilter = gitCanSparseFilter;
exports.missingGitReason = missingGitReason;
exports.fetchFlow = fetchFlow;
exports.flowSourceForRun = flowSourceForRun;
exports.flowDirFor = flowDirFor;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const path_1 = require("path");
const skill_js_1 = require("../skill.js");
const credentials_js_1 = require("./credentials.js");
const flow_home_js_1 = require("./flow-home.js");
Object.defineProperty(exports, "assertFlowName", { enumerable: true, get: function () { return flow_home_js_1.assertFlowName; } });
Object.defineProperty(exports, "cachedFlowDir", { enumerable: true, get: function () { return flow_home_js_1.cachedFlowDir; } });
Object.defineProperty(exports, "flowsCacheDir", { enumerable: true, get: function () { return flow_home_js_1.flowsCacheDir; } });
exports.DEFAULT_FLOWS_REPO = 'http://bitbucket.digital.vn/scm/vcoding/vsaf-workflow.git';
/**
 * Địa chỉ repo flows, đã bóc phần đăng nhập ra khỏi chuỗi.
 *
 * `VSAF_FLOWS_REPO=http://nguoi:token@host/...` là một cách dùng hợp lệ và phải tiếp tục
 * chạy được — nhưng đưa nguyên chuỗi đó cho `git clone` thì git ghi thẳng nó vào
 * `.git/config` của cache: đo được `~/.vsaf/flows/.git/config` chứa token nguyên văn,
 * quyền 664. Che ở câu thông báo (`maskUrl`) chỉ dọn phần màn hình, không dọn phần đĩa.
 *
 * Nên phần đăng nhập được bóc ra ngay tại đây rồi đi tiếp bằng đúng đường `gitAuthEnv`
 * — biến môi trường, một header buộc vào đúng máy chủ đó — vốn có sẵn chính vì lý do
 * này, và đã được đo là chạy. Git nhận một địa chỉ trơn, nên không còn gì để ghi xuống.
 *
 * Chỉ bóc khi có mật khẩu/token: `http://nguoi@host` mang một cái tên, không mang bí
 * mật, và bỏ nó đi là đổi ý nghĩa địa chỉ người dùng viết. Cũng chỉ áp cho http(s):
 * `ssh://` xác thực bằng khoá và `file://` không đăng nhập.
 */
function flowsRepoTarget() {
    const raw = process.env.VSAF_FLOWS_REPO ?? exports.DEFAULT_FLOWS_REPO;
    let parsed;
    try {
        parsed = new URL(raw);
    }
    catch {
        return { url: raw };
    }
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:')
        return { url: raw };
    if (parsed.password === '')
        return { url: raw };
    // `URL` giữ phần userinfo ở dạng percent-encoded; git gửi đi bản đã giải mã, nên
    // credential dựng ở đây cũng phải là bản đã giải mã — nếu không, một token có ký tự
    // đặc biệt sẽ đi sai.
    const credential = {
        secret: decodeURIComponent(parsed.password),
        username: parsed.username === '' ? undefined : decodeURIComponent(parsed.username),
        source: 'env',
    };
    parsed.username = '';
    parsed.password = '';
    return { url: parsed.toString(), credential };
}
function flowsRepoUrl() {
    return flowsRepoTarget().url;
}
/**
 * Cùng một đoạn văn, đã che phần đăng nhập.
 *
 * Địa chỉ repo flows không còn mang phần đăng nhập từ khi `flowsRepoTarget` bóc nó ra,
 * nên đây là lưới thứ hai chứ không phải lưới duy nhất: nguyên văn lỗi của git có thể
 * nhắc lại một địa chỉ khác — một lần chuyển hướng, một submodule, một dòng cấu hình —
 * và câu lỗi đó đi thẳng vào màn hình mà ai cài cũng đọc. `bitbucket.ts` trong repo này
 * đã có nguyên tắc "câu thông báo không được nêu secret"; đây là chỗ áp nó cho địa chỉ.
 *
 * Nhận cả một đoạn văn, không chỉ một địa chỉ: nguyên văn lỗi của git là
 * `Command failed: git clone … <url> …`, nên chuỗi cần che nằm lẫn trong câu.
 */
function maskUrl(text) {
    return text.replace(/([a-zA-Z][a-zA-Z0-9+.\-]*:\/\/)[^/\s@]*@/g, '$1***@');
}
/**
 * Mốc chờ mặc định cho mỗi lệnh git.
 *
 * Mọi `vsaf install` giờ đi qua đây, kể cả khi rốt cuộc cài bản kèm gói npm. Không đặt
 * mốc thì máy ngoài VPN ngồi chờ hết timeout của tầng TCP — hàng phút, không một dòng
 * nào giải thích — trước khi lùi. Hai phút là rộng rãi cho repo flows đo được 1,5 MB
 * khung, và vẫn ngắn hơn nhiều so với chờ mạng tự bỏ cuộc.
 */
exports.DEFAULT_FLOW_TIMEOUT_MS = 120_000;
/**
 * Cấu hình xác thực đưa cho git, dưới dạng biến môi trường.
 *
 * §3.2 spec đòi dùng lại `credentials.ts`: `git credential fill` **hoặc**
 * `BITBUCKET_TOKEN`. Nửa đầu do chính git làm trong lúc clone; nửa sau thì không ai làm
 * — một job CI chỉ có `BITBUCKET_TOKEN` xác thực vô danh rồi lùi về bản kèm npm kèm câu
 * bảo "kiểm tra quyền đọc repo" trong khi quyền họ có.
 *
 * Đưa qua `GIT_CONFIG_*` chứ không qua `-c` hay `remote set-url`, vì cả hai chỗ kia đều
 * làm token rò ra: `-c` đưa nó vào dòng lệnh (thấy được bằng `ps`, và đi vào nguyên văn
 * lỗi của execFileSync), còn địa chỉ có userinfo thì git ghi thẳng vào `.git/config` của
 * cache. Biến môi trường không nằm ở cả hai chỗ đó.
 *
 * Vì lý do đó, đây cũng là đường mà `VSAF_FLOWS_REPO=http://nguoi:token@host/...` đi:
 * `flowsRepoTarget` bóc phần đăng nhập khỏi địa chỉ rồi giao nó vào đây. Trước đây địa
 * chỉ đó đi thẳng vào `git clone`, và đúng chỗ rò mà đoạn trên mô tả bị để mở.
 *
 * Header buộc vào đúng một địa chỉ (`http.<origin>.extraHeader`), để một lần chuyển
 * hướng sang máy chủ khác không mang token đi theo.
 *
 * `GIT_CONFIG_COUNT` cần git 2.31; mốc dùng được sparse+filter là 2.27. Trên git
 * 2.27–2.30 phần này bị bỏ qua, tức là quay về đúng hành vi hôm nay — xác thực vô danh
 * rồi lùi — chứ không hỏng thêm gì.
 */
function gitAuthEnv(url, credential) {
    if (!credential)
        return {};
    let parsed;
    try {
        parsed = new URL(url);
    }
    catch {
        return {};
    }
    // Chỉ http(s) mang được header. `file://` không cần, `ssh://` xác thực bằng khoá.
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:')
        return {};
    // Nối vào sau cấu hình môi trường người dùng đã có, không đè lên nó. Đặt cứng
    // `GIT_CONFIG_COUNT: '1'` sẽ bỏ mọi khoá họ khai và thay khoá thứ nhất bằng khoá của
    // engine — hiếm gặp, nhưng khi gặp thì hỏng âm thầm.
    const already = Number.parseInt(process.env.GIT_CONFIG_COUNT ?? '', 10);
    const at = Number.isInteger(already) && already > 0 ? already : 0;
    return {
        GIT_CONFIG_COUNT: String(at + 1),
        [`GIT_CONFIG_KEY_${at}`]: `http.${parsed.protocol}//${parsed.host}.extraHeader`,
        [`GIT_CONFIG_VALUE_${at}`]: `Authorization: ${(0, credentials_js_1.authorizationHeader)(credential)}`,
    };
}
function runGit(args, options = {}) {
    return (0, child_process_1.execFileSync)('git', args, {
        cwd: options.cwd,
        stdio: ['ignore', 'pipe', 'pipe'],
        encoding: 'utf-8',
        timeout: options.timeoutMs ?? exports.DEFAULT_FLOW_TIMEOUT_MS,
        // Repo nội bộ dùng http và có thể đòi đăng nhập. Không tắt hỏi han thì git treo
        // chờ một câu trả lời không bao giờ tới — stdin đã bị đóng — và mốc chờ ở trên
        // trở thành thứ duy nhất cứu được, sau hai phút đứng im.
        env: { ...process.env, ...(options.auth ?? {}), GIT_TERMINAL_PROMPT: '0' },
    }).trim();
}
/** Lệnh git cho một lượt kéo: cùng mốc chờ, cùng cấu hình xác thực. */
function gitFor(timeoutMs, auth) {
    return (args, cwd) => runGit(args, { cwd, timeoutMs, auth });
}
/** Địa chỉ mà cache đang theo, hoặc rỗng nếu đọc không ra. */
function cachedOrigin(git, cache) {
    try {
        return git(['remote', 'get-url', 'origin'], cache);
    }
    catch {
        return null;
    }
}
/**
 * Hai địa chỉ có trỏ vào cùng một repo hay không.
 *
 * Phải chuẩn hoá trước khi so, vì `git remote get-url origin` trả lại **nguyên văn**
 * chuỗi đã đưa vào lúc clone. So chuỗi thuần thì năm cách viết cùng một repo hoá ra năm
 * repo khác nhau, và mỗi lần khác là một lượt dựng lại cache: đo được thêm dấu `/` cuối
 * → dựng lại, lật về → dựng lại nữa, ba lượt install ra ba lần clone.
 *
 * Chuẩn hoá đúng ba thứ đủ để dẹp cả năm cách viết đo được, và không hơn: bỏ khoảng
 * trắng, bỏ `/` cuối, bỏ hậu tố `.git`, bỏ tiền tố `file://`. Không đụng tới chữ hoa
 * chữ thường hay cổng — đó là chỗ hai địa chỉ có thể thật sự khác nhau.
 */
function sameRepo(a, b) {
    if (a === null)
        return false;
    const canon = (url) => url
        .trim()
        .replace(/^file:\/\//, '')
        .replace(/\/+$/, '')
        .replace(/(\/?)\.git$/, '')
        .replace(/\/+$/, '');
    return canon(a) === canon(b);
}
/** Các flow đang được bật trong cache — để dựng lại cache không làm mất chúng. */
function enabledFlows(git, cache) {
    try {
        return git(['sparse-checkout', 'list'], cache).split('\n').map(line => line.trim()).filter(Boolean);
    }
    catch {
        return [];
    }
}
/**
 * Dựng cache nếu chưa có, cập nhật nếu đã có.
 *
 * `--filter=blob:none` để lần đầu chỉ tải khung, chưa tải nội dung file nào; nội dung
 * chỉ về khi có thư mục được bật. `--sparse` bật sẵn chế độ chọn thư mục. Đo thật trên
 * bitbucket.digital.vn: khung 1,5 MB, bật một flow lên 2,7 MB.
 *
 * `url` truyền vào chứ không tự đọc lại: đây là chỗ địa chỉ được ghi xuống đĩa (git lưu
 * nó vào `.git/config` của cache), nên nó phải là đúng địa chỉ đã bóc phần đăng nhập mà
 * phía gọi đang dùng, không phải một lượt đọc biến môi trường lần nữa.
 */
function ensureCache(git, url, refresh) {
    const cache = (0, flow_home_js_1.flowsCacheDir)();
    // Dựng lại cache thì phải bật lại đúng những flow đang bật, nếu không lượt dựng lại
    // âm thầm gỡ các flow khác khỏi cache — trái hẳn với chủ ý dùng `sparse-checkout add`
    // thay vì `set` ở dưới, vốn có để cài flow thứ hai không làm flow thứ nhất biến mất.
    let keep = [];
    const wipe = () => {
        keep = [...new Set([...keep, ...enabledFlows(git, cache)])];
        (0, fs_1.rmSync)(cache, { recursive: true, force: true });
    };
    // Đổi VSAF_FLOWS_REPO sau lần clone đầu từng không có tác dụng: `fetch origin` đi
    // theo địa chỉ bản clone cũ, nên người trỏ sang repo khác vẫn nhận nội dung repo cũ
    // và không ai báo gì. Dựng lại chứ không `remote set-url`: set-url giữ nguyên nhánh
    // theo dõi của repo cũ, và `@{u}` bên dưới có thể trỏ vào một nhánh repo mới không
    // có — đúng kiểu cache nửa vời mà chỗ này sinh ra để dẹp.
    //
    // Xét TRƯỚC nhánh refresh: xoá cache trước thì không còn `origin` nào để so, và người
    // đổi địa chỉ đúng lúc gõ `--refresh-flows` không được nói cho biết địa chỉ đã đổi —
    // kết quả vẫn đúng, nhưng họ mất dòng duy nhất giải thích vì sao nội dung khác đi.
    if ((0, fs_1.existsSync)((0, path_1.join)(cache, '.git')) && !sameRepo(cachedOrigin(git, cache), url)) {
        console.log(`[vsaf] Địa chỉ repo flows đã đổi — dựng lại cache từ ${maskUrl(url)}`);
        wipe();
    }
    if (refresh && (0, fs_1.existsSync)(cache))
        wipe();
    if (!(0, fs_1.existsSync)((0, path_1.join)(cache, '.git'))) {
        // Xoá phần thừa của một lượt clone hỏng dở, nếu không git từ chối vì thư mục không rỗng.
        if ((0, fs_1.existsSync)(cache))
            (0, fs_1.rmSync)(cache, { recursive: true, force: true });
        (0, fs_1.mkdirSync)((0, path_1.dirname)(cache), { recursive: true });
        git(['clone', '--filter=blob:none', '--sparse', '--no-checkout', url, cache]);
        if (keep.length > 0) {
            git(['sparse-checkout', 'add', ...keep], cache);
            git(['checkout'], cache);
        }
        return;
    }
    // `@{u}` là nhánh theo dõi do lượt clone đặt. Đoán tên nhánh mặc định thì sai ở
    // repo đặt tên khác `main`.
    git(['fetch', 'origin'], cache);
    git(['reset', '--hard', '@{u}'], cache);
}
/**
 * Các flow repo đang có.
 *
 * Một thư mục là một flow chỉ khi nó có `pack.yaml` (§3.1 spec) — nên đọc theo `pack.yaml`
 * chứ không theo danh sách thư mục. Repo thật sẽ có `docs/`, `.github/`, `README.md` bên
 * cạnh bốn flow, và một danh sách thư mục thuần biến chúng thành "Đang có: .github, docs,
 * sdlc" — vừa sai, vừa mời người dùng gõ `vsaf install docs`.
 *
 * `ls-tree -r` đọc từ cây commit nên không cần bật thư mục nào; bản clone `blob:none`
 * vẫn có đủ tree để trả lời.
 */
function flowsInRepo(git, cache) {
    return git(['ls-tree', '-r', '--name-only', 'HEAD'], cache)
        .split('\n')
        .map(line => /^([^/]+)\/pack\.yaml$/.exec(line.trim()))
        .filter((found) => found !== null)
        .map(found => found[1])
        .sort();
}
/** Repo kéo được nhưng không có flow đang hỏi. Một lý do bình thường, không phải sự cố. */
class FlowNotInRepoError extends Error {
}
/** Repo kéo được nhưng chưa ai đẩy commit nào lên. */
class EmptyRepoError extends Error {
}
function classifyRepoFailure(error) {
    if (error instanceof FlowNotInRepoError)
        return 'not-in-repo';
    if (error instanceof EmptyRepoError)
        return 'empty-repo';
    const failure = error;
    // Hết mốc chờ: execFileSync giết tiến trình nên `status` là null, chỉ còn `killed`
    // và `signal`. Đây vẫn là chuyện mạng, không phải lỗi lạ.
    if (failure.killed === true || typeof failure.signal === 'string')
        return 'timeout';
    // `status` là số chỉ khi execFileSync thật sự chạy git rồi git thoát khác 0. Lỗi hệ
    // thống (ENOSPC, EACCES) và lỗi lập trình đều không có trường này.
    if (typeof failure.status === 'number')
        return 'git-refused';
    return 'unexpected';
}
/**
 * Một câu người thường đọc được, thay cho nguyên văn lỗi của git.
 *
 * Nguyên văn là `Command failed: git clone --filter=blob:none --sparse --no-checkout
 * <url> <path>` — đúng nhưng vô dụng với người vừa chỉ muốn cài một flow, và nó đi
 * thẳng vào câu thông báo mà ai cài cũng đọc. Nguyên văn vẫn được giữ, nhưng để dành
 * cho chỗ thật sự cần: lúc không còn đường lùi nào, và lúc lỗi thuộc loại lạ.
 */
function describeRepoFailure(error, kind, timeoutMs) {
    if (kind === 'not-in-repo' || kind === 'empty-repo')
        return error.message;
    if (kind === 'timeout') {
        return `repo flows không trả lời trong ${Math.round(timeoutMs / 1000)} giây — kiểm tra mạng/VPN`;
    }
    if (kind === 'git-refused') {
        return `không đọc được ${maskUrl(flowsRepoUrl())} — kiểm tra mạng/VPN và quyền đọc repo`;
    }
    return maskUrl(error.message);
}
function fetchFromRepo(flow, options = {}) {
    const cache = (0, flow_home_js_1.flowsCacheDir)();
    const { url, credential: fromUrl } = flowsRepoTarget();
    // Nói ra TRƯỚC khi chạm git, và chỉ ở lượt đáng nói.
    //
    // Dòng này sinh ra từ một phép đo: 121 giây đứng im trước khi in gì, với người ngoài
    // VPN — nó đổi "lệnh treo" thành "lệnh đang chờ mạng". Nhưng đó là lượt CLONE ĐẦU TIÊN.
    // Máy đã có cache thì đây chỉ là một lượt fetch tăng dần, thường nhanh, và dòng này
    // rơi vào chỗ transcript §2 để trống.
    //
    // Đánh đổi nói rõ: fetch tăng dần vẫn có thể chậm trên mạng tệ, và ở ca đó người dùng
    // lại thấy im lặng. Chấp nhận, vì đó là ca hiếm hơn clone lần đầu, và `--verbose` vẫn nói.
    if (!(0, flow_home_js_1.cachedFlowDir)(flow) || options.refresh === true) {
        console.log(`[vsaf] Đang lấy flow "${flow}" từ ${maskUrl(url)} …`);
    }
    // Phần đăng nhập viết thẳng trong địa chỉ được ưu tiên hơn `BITBUCKET_TOKEN`: nó là
    // thứ người dùng chỉ đích danh cho repo này, còn biến môi trường là thứ nền chung.
    //
    // Không gọi `git credential fill` ở đây: git tự gọi helper của nó trong lúc clone, nên
    // hỏi thêm một lượt là một lần tra cùng câu trả lời — và trên keychain đang khoá là
    // một lần chờ nữa cho cùng câu đó.
    const credential = fromUrl ?? (0, credentials_js_1.credentialFromEnv)();
    const git = gitFor(options.timeoutMs ?? exports.DEFAULT_FLOW_TIMEOUT_MS, gitAuthEnv(url, credential));
    ensureCache(git, url, options.refresh === true);
    // Repo `AVAILABLE` mà 0 commit là đúng trạng thái repo flows đang có lúc viết dòng này,
    // và `ls-tree HEAD` ở đó thoát 128 — cùng hình dạng với "không đọc được repo", nên câu
    // lỗi hoá ra bảo người dùng kiểm tra mạng và quyền đọc trong khi cả hai đều tốt.
    try {
        git(['rev-parse', '--verify', 'HEAD'], cache);
    }
    catch {
        throw new EmptyRepoError('repo flows chưa có commit nào — chưa ai đẩy nội dung flow lên');
    }
    const available = flowsInRepo(git, cache);
    if (!available.includes(flow)) {
        throw new FlowNotInRepoError(`Repo flows không có flow "${flow}".\n`
            + `  Đang có: ${available.join(', ')}`);
    }
    // `add` chứ không phải `set`: `set` sẽ tắt các flow đã bật trước đó, và người dùng
    // cài flow thứ hai vào máy không hề muốn flow thứ nhất biến mất.
    git(['sparse-checkout', 'add', flow], cache);
    git(['checkout'], cache);
    return {
        dir: (0, path_1.join)(cache, flow),
        origin: 'repo',
        commit: git(['rev-parse', 'HEAD'], cache),
    };
}
/** Bản flow đi kèm gói npm, hoặc rỗng nếu gói không mang theo flow đó. */
function bundledFlowDir(flow) {
    (0, flow_home_js_1.assertFlowName)(flow);
    const dir = (0, path_1.join)((0, skill_js_1.findPackageRoot)(), 'skills', flow);
    return (0, fs_1.existsSync)((0, path_1.join)(dir, 'pack.yaml')) ? dir : null;
}
/**
 * Bản flow đọc được mà không chạm mạng: cache trước, rồi bản kèm gói npm.
 *
 * Cache trước vì nó là bản mới hơn — nó đến từ repo. Dùng cho những chỗ chỉ cần đọc
 * `pack.yaml` (`--dry-run`, câu hỏi về code repo, `skill init`) và không có lý do gì
 * trả giá một vòng qua mạng.
 */
function localFlowDir(flow) {
    return (0, flow_home_js_1.cachedFlowDir)(flow) ?? bundledFlowDir(flow);
}
/**
 * Máy có git đủ mới để tải một phần và chọn thư mục hay không.
 *
 * `--filter` cần git 2.19, `--sparse` khi clone cần 2.27. Lấy mốc cao hơn. Git cũ hơn
 * thì không phải lỗi của người dùng, chỉ là phải đi đường lùi.
 */
function gitCanSparseFilter() {
    try {
        // Mốc chờ riêng, ngắn: đây chỉ là `git --version` trên đĩa, không qua mạng, nên
        // không có lý do gì để nó được phép giữ lệnh hai phút.
        const found = /(\d+)\.(\d+)/.exec(runGit(['--version'], { timeoutMs: 10_000 }));
        if (!found)
            return false;
        const major = Number(found[1]);
        const minor = Number(found[2]);
        return major > 2 || (major === 2 && minor >= 27);
    }
    catch {
        // Không có git trên máy.
        return false;
    }
}
/**
 * §6 spec: máy không có git đủ mới thì cũng phải nói luôn cách để lần sau không còn
 * phải đi đường lùi, chứ không chỉ nêu tình trạng.
 *
 * Tách riêng thành hàm thuần (không đọc `gitCanSparseFilter()`) để test khoá được nội
 * dung câu chữ mà không cần giả lập git cũ — máy nào chạy test cũng có thể có git mới.
 */
function missingGitReason() {
    return 'máy chưa có git, hoặc git cũ hơn 2.27 — cài git bản mới hơn (hoặc nâng cấp git hiện có) để lần sau lấy được bản mới nhất từ repo';
}
// Một tên flow không có trong repo cũng rơi vào nhánh đường lùi này, và đó là đúng —
// nó vẫn có thể là flow gói npm mang theo, nên không được coi là lỗi sớm.
function fetchFlow(flow, options = {}) {
    (0, flow_home_js_1.assertFlowName)(flow);
    // Giữ nguyên văn đầy đủ của lỗi gốc (không cắt dòng đầu): khi flow gõ sai tên,
    // `fetchFromRepo` liệt kê các flow đang có ở dòng thứ hai — cắt mất dòng đó thì
    // người dùng không còn biết nên gõ lại tên gì.
    let reason;
    // Nguyên văn lỗi của git, để dành cho lúc không còn đường lùi — ở đó người đọc là
    // người phải đi sửa, và tên lệnh đầy đủ là thứ họ cần. Đã che phần đăng nhập.
    let detail;
    if (!gitCanSparseFilter()) {
        reason = missingGitReason();
    }
    else {
        try {
            return fetchFromRepo(flow, options);
        }
        catch (error) {
            const kind = classifyRepoFailure(error);
            reason = describeRepoFailure(error, kind, options.timeoutMs ?? exports.DEFAULT_FLOW_TIMEOUT_MS);
            detail = maskUrl(error.message);
            if (kind === 'unexpected') {
                // Nói to ngay tại chỗ, tách khỏi câu "đang dùng bản kèm theo" hiền lành ở dưới:
                // câu đó đọc ra là chuyện thường ngày, còn đây là thứ cần được báo lại.
                console.log('[vsaf] ⚠ Lỗi không lường trước khi lấy flow từ repo — không phải mất mạng hay sai quyền:');
                console.log(`[vsaf]     ${detail.split('\n')[0]}`);
                console.log('[vsaf]   Vẫn cài tiếp bằng bản kèm theo, nhưng hãy báo lại lỗi này.');
            }
        }
    }
    const bundled = bundledFlowDir(flow);
    if (bundled) {
        return {
            dir: bundled,
            origin: 'bundled',
            // Note là một câu ngắn hiển thị cho người dùng lúc cài — chỉ lấy dòng đầu của
            // reason, phần chi tiết (vd danh sách flow đang có) không cần thiết ở đây.
            note: `không lấy được từ repo flows (${reason.split('\n')[0]}) — đang dùng bản kèm theo gói npm, có thể cũ hơn`,
        };
    }
    // Danh sách flow gói npm mang theo phải nằm trong câu này.
    //
    // Người đọc nó thường là người vừa gõ sai tên, và cảnh hay gặp nhất là gõ sai lúc
    // đang ngoài mạng — đúng lúc bốn pack nằm sẵn trên đĩa là thứ duy nhất họ dùng được.
    // Thiếu danh sách thì lỗi chỉ nói về mạng, còn thứ họ cần là một tên gõ đúng.
    const mangTheo = (0, skill_js_1.builtInPacks)();
    throw new Error(`Không cài được flow "${flow}".\n`
        + `  Lấy từ repo flows: không được — ${reason}\n`
        + `  Bản kèm theo gói npm: không có flow này${mangTheo.length > 0 ? ` — đang có: ${mangTheo.join(', ')}` : ''}`
        + (detail && detail !== reason ? `\n  Nguyên văn lỗi git: ${detail.split('\n')[0]}` : ''));
}
/**
 * Những lượt phân giải đã làm trong tiến trình này.
 *
 * Khoá gồm cả địa chỉ repo và thư mục cache, không chỉ tên flow: đổi một trong hai là
 * đổi câu trả lời, và bộ test đổi cả hai giữa các test.
 */
const resolvedInThisRun = new Map();
/**
 * Những lượt kéo đã làm LẠI trong tiến trình này.
 *
 * `--refresh-flows` phải xuyên qua bản nhớ, nhưng chỉ đúng một lần: lần thứ hai trong
 * cùng một lệnh thì bản vừa kéo lại chính là bản mới nhất, và kéo lại nữa là wipe + clone
 * đầy thêm một lượt. Đo được ở `install <flow> --new --refresh-flows`: 2 clone khi cache
 * rỗng, hoặc 1 fetch + 1 clone đầy khi cache đã có.
 */
const refreshedInThisRun = new Set();
function runKey(flow) {
    return `${flowsRepoUrl()}\u0000${(0, flow_home_js_1.flowsCacheDir)()}\u0000${flow}`;
}
/**
 * Kéo flow, nhưng chỉ một lần cho mỗi lệnh — **kể cả khi lượt đó hỏng**.
 *
 * Một lệnh thường cần nội dung flow ở nhiều chỗ: `vsaf install <flow>` hỏi qua
 * `askCodeRepos`, hỏi qua `packInfoIfKnown`, rồi mới tới `execInstall` — ba chỗ, một
 * câu hỏi. Kéo lại lần nữa là một vòng qua mạng cho một câu trả lời không đổi giữa
 * chừng — cộng thêm một câu cảnh báo in trùng và một lần chờ hết mốc nữa khi máy ở
 * ngoài VPN.
 *
 * Lượt hỏng cũng được nhớ, và đó là phần bản trước thiếu. Một lượt phân giải hỏng thì
 * hỏng như nhau ở cả ba chỗ — mạng vẫn đứt, quyền vẫn thiếu, tên vẫn sai — nên thử lại
 * chỉ là trả giá thêm hai lần chờ. Đo được: repo không tới được cộng flow không có bản
 * kèm npm cho **3 lần** `Đang lấy flow` rồi exit 1; với mốc 120 giây là sáu phút.
 *
 * `fetchFlow` để nguyên, không nhớ gì: nó là chỗ hành vi kéo được kiểm bằng test, và một
 * bộ nhớ đệm ẩn bên trong nó sẽ làm những test đó nói dối. Bộ nhớ đệm sống ở đây, nơi
 * tầng lệnh gọi vào.
 *
 * `refresh` đi xuyên qua bộ nhớ đệm — người gõ `--refresh-flows` đang yêu cầu đúng việc
 * kéo lại — nhưng chỉ ở lượt gọi đầu. Sau khi đã kéo lại một lần, bản nằm trong bộ nhớ
 * đệm CHÍNH LÀ bản mới nhất, nên lượt gọi thứ hai trong cùng lệnh dùng lại nó. Không có
 * ngoại lệ này thì hai lượt gọi của một lệnh phải đồng thuận về `refresh` mới dedupe
 * được, và `--new --refresh-flows` — nơi `init` gọi trước `install` — trả giá hai vòng
 * qua mạng, tức hai lần chờ hết mốc 120 giây với người ngoài VPN.
 *
 * Mốc chờ KHÔNG nằm trong khoá: một lệnh chỉ kéo một lần, nên lượt kéo đầu quyết định
 * mốc, và lượt sau dùng lại kết quả chứ không kéo lại với mốc khác.
 */
function flowSourceForRun(flow, options = {}) {
    const key = runKey(flow);
    const refresh = options.refresh === true && !refreshedInThisRun.has(key);
    const remembered = refresh ? undefined : resolvedInThisRun.get(key);
    if (remembered) {
        if (remembered.ok)
            return remembered.source;
        // Ném lại đúng lỗi cũ, không dựng lỗi mới: phía gọi phân biệt các lớp lỗi bằng
        // `instanceof`, và một bản sao chỉ giữ câu chữ sẽ rơi nhầm nhánh.
        throw remembered.error;
    }
    let outcome;
    try {
        outcome = { ok: true, source: fetchFlow(flow, { ...options, refresh }) };
    }
    catch (error) {
        outcome = { ok: false, error };
    }
    resolvedInThisRun.set(key, outcome);
    // Đánh dấu kể cả khi hỏng: lượt kéo lại ĐÃ được thử, và thử lại cũng hỏng như thế.
    if (refresh)
        refreshedInThisRun.add(key);
    if (!outcome.ok)
        throw outcome.error;
    // Nói ra đúng ở lượt kéo thật, một lần cho cả lệnh. In ở phía người gọi thì mỗi chỗ
    // dùng flow lại nói cùng một câu, và đó chính là triệu chứng đã đo được ở `init`.
    if (outcome.source.note)
        console.log(`[vsaf] ${outcome.source.note}`);
    return outcome.source;
}
/**
 * Thư mục nội dung của flow, kèm việc nói ra khi phải dùng bản kèm theo.
 *
 * Dành cho các lệnh chỉ cần thư mục — `sync` chẳng hạn — chứ không cần biết flow đến từ
 * đâu. Có riêng hàm này vì các lệnh đó từng gọi `resolveSource`, thứ chỉ biết các pack
 * ship trong gói npm, nên một flow chỉ sống ở repo flows bị từ chối ngay với câu "Pack
 * not found".
 *
 * Câu cảnh báo do `flowSourceForRun` in, đúng một lần cho cả lệnh.
 */
function flowDirFor(flow, options = {}) {
    return flowSourceForRun(flow, options).dir;
}
//# sourceMappingURL=flow-source.js.map