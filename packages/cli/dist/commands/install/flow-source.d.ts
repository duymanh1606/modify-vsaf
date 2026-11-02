import { type Credential } from './credentials.js';
import { assertFlowName, cachedFlowDir, flowsCacheDir } from './flow-home.js';
export { assertFlowName, cachedFlowDir, flowsCacheDir };
/**
 * Nơi nội dung flow được lấy về từ.
 *
 * Trước đây flow nằm trong gói npm, nên phát hành lại một câu chữ trong quy trình
 * cũng phải phát hành lại engine. Giờ flow sống ở repo riêng và chỉ thư mục đang
 * dùng mới được kéo về — sau này sẽ rất nhiều flow, kéo hết về mọi máy là vô lý.
 */
export interface FlowSource {
    /** Thư mục chứa nội dung flow, đường dẫn tuyệt đối. */
    dir: string;
    /** `repo` là lấy từ repo flows; `bundled` là bản đi kèm gói npm. */
    origin: 'repo' | 'bundled';
    /** Mã commit của repo flows. Chỉ có khi `origin` là `repo`. */
    commit?: string;
    /** Một câu nói vì sao phải dùng bản kèm theo. Chỉ có khi `origin` là `bundled`. */
    note?: string;
}
export declare const DEFAULT_FLOWS_REPO = "http://bitbucket.digital.vn/scm/vcoding/vsaf-workflow.git";
/** Repo flows sẽ kéo từ đâu, và đăng nhập bằng gì. */
export interface FlowsRepoTarget {
    /** Địa chỉ đưa cho git. Không bao giờ mang phần đăng nhập. */
    url: string;
    /** Phần đăng nhập bóc ra từ địa chỉ, nếu người dùng viết nó vào đó. */
    credential?: Credential;
}
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
export declare function flowsRepoTarget(): FlowsRepoTarget;
export declare function flowsRepoUrl(): string;
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
export declare function maskUrl(text: string): string;
/**
 * Mốc chờ mặc định cho mỗi lệnh git.
 *
 * Mọi `vsaf install` giờ đi qua đây, kể cả khi rốt cuộc cài bản kèm gói npm. Không đặt
 * mốc thì máy ngoài VPN ngồi chờ hết timeout của tầng TCP — hàng phút, không một dòng
 * nào giải thích — trước khi lùi. Hai phút là rộng rãi cho repo flows đo được 1,5 MB
 * khung, và vẫn ngắn hơn nhiều so với chờ mạng tự bỏ cuộc.
 */
export declare const DEFAULT_FLOW_TIMEOUT_MS = 120000;
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
export declare function gitAuthEnv(url: string, credential: Credential | undefined): Record<string, string>;
/** Bản flow đi kèm gói npm, hoặc rỗng nếu gói không mang theo flow đó. */
export declare function bundledFlowDir(flow: string): string | null;
/**
 * Bản flow đọc được mà không chạm mạng: cache trước, rồi bản kèm gói npm.
 *
 * Cache trước vì nó là bản mới hơn — nó đến từ repo. Dùng cho những chỗ chỉ cần đọc
 * `pack.yaml` (`--dry-run`, câu hỏi về code repo, `skill init`) và không có lý do gì
 * trả giá một vòng qua mạng.
 */
export declare function localFlowDir(flow: string): string | null;
/**
 * Máy có git đủ mới để tải một phần và chọn thư mục hay không.
 *
 * `--filter` cần git 2.19, `--sparse` khi clone cần 2.27. Lấy mốc cao hơn. Git cũ hơn
 * thì không phải lỗi của người dùng, chỉ là phải đi đường lùi.
 */
export declare function gitCanSparseFilter(): boolean;
/**
 * §6 spec: máy không có git đủ mới thì cũng phải nói luôn cách để lần sau không còn
 * phải đi đường lùi, chứ không chỉ nêu tình trạng.
 *
 * Tách riêng thành hàm thuần (không đọc `gitCanSparseFilter()`) để test khoá được nội
 * dung câu chữ mà không cần giả lập git cũ — máy nào chạy test cũng có thể có git mới.
 */
export declare function missingGitReason(): string;
export interface FetchFlowOptions {
    refresh?: boolean;
    /** Mốc chờ cho mỗi lệnh git. Mặc định `DEFAULT_FLOW_TIMEOUT_MS`. */
    timeoutMs?: number;
}
export declare function fetchFlow(flow: string, options?: FetchFlowOptions): FlowSource;
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
export declare function flowSourceForRun(flow: string, options?: FetchFlowOptions): FlowSource;
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
export declare function flowDirFor(flow: string, options?: FetchFlowOptions): string;
//# sourceMappingURL=flow-source.d.ts.map