import type { TelemetryArtifactsConfig } from '@vsaf/core';
export interface SkillListEntry {
    name: string;
    description: string;
    fileCount: number;
    linkedCommand?: string;
}
export interface SkillInfoResult {
    name: string;
    description: string;
    version?: string;
    author?: string;
    files: string[];
    linkedCommands: string[];
}
export interface SkillRemoveResult {
    removed: string;
    warnings: string[];
}
export interface SkillAddOptions {
    only?: string[];
    force?: boolean;
}
export interface SkillAddResult {
    added: string[];
    skipped: string[];
}
export interface SkillInitOptions {
    workflows?: Record<string, string>;
    /** Reinit: overwrite workflow files that already exist (default skip-if-exists). */
    overwriteWorkflows?: boolean;
}
export interface SkillInitResult {
    commandsCreated: string[];
    commandsSkipped: string[];
    workflowsCreated: string[];
}
/** Machine-local paths a pack generates, kept out of git. Policy differs per repo kind. */
export interface GitignorePolicy {
    spec?: string[];
    code?: string[];
}
/** What a pack asks to write outside the project. Requires the user's approval. */
export interface GlobalPolicy {
    skillTargets: string[];
    ruleTarget?: string;
}
/**
 * A pack that ships the script which wires a project up, and wants that script to be
 * the one that runs.
 *
 * Declaring this is how a pack says "my own tooling owns these steps". The installer
 * then skips its internal wiring instead of doing the same work a second time — two
 * passes over the same files leave whichever ran last, which is not a state anyone
 * chose.
 *
 * `env` names the variables that must be set before the script runs. A script that
 * asks questions blocks forever when nothing is attached to answer them.
 */
export interface WiringPolicy {
    script: string;
    env: string[];
    passthrough: string[];
}
/** Same handover, for the script that pushes skills and rules outside the project. */
export interface GlobalSyncPolicy {
    script: string;
    passthrough: string[];
}
/** Telemetry a pack declares for the projects it is installed into. */
export interface PackTelemetry {
    artifacts?: TelemetryArtifactsConfig;
}
export interface PackInfo {
    /**
     * The pack's own name, as it declares itself in `pack.yaml`.
     *
     * Read so a caller holding only a directory — `vsaf apply-pack`, chiefly — has a
     * name to install under that does not depend on what the directory happens to be
     * called on disk. A cache path, an extracted tarball, a worktree checkout: none of
     * those are obliged to keep the pack's own name.
     */
    name?: string;
    skillNames: string[];
    bundledNames: string[];
    workflows: Record<string, string>;
    /**
     * Where the pack keeps its skills, when they are not flat at the pack root.
     *
     * A pack that mirrors an upstream template keeps the upstream layout, so the
     * upstream's own scripts read it without anything being staged for them first.
     */
    skillsRoot?: string;
    /** Whether the directory names under `skillsRoot` already carry the pack prefix. */
    skillsPrefixed?: boolean;
    /** Skills that belong in the project rather than on the machine. */
    skillsKeepInProject?: string[];
    /**
     * Paths inside the pack that only the installer reads, and that a project has no use
     * for — left behind when the pack is copied, the same way `pack.yaml` is.
     */
    packOnly?: string[];
    wiring?: WiringPolicy;
    globalSync?: GlobalSyncPolicy;
    /**
     * Telemetry settings the pack knows better than the engine does — chiefly which
     * paths its skills write deliverables to. `vsaf install` copies these into the
     * project config; the engine defaults suit the sdlc layout only.
     */
    telemetry?: PackTelemetry;
    /**
     * Where the pack wants its skills to live, with IDE directories getting copies.
     * Undefined means the existing behaviour: write straight into `.claude/skills`.
     */
    canonicalSkillsDir?: string;
    /**
     * Bản engine tối thiểu flow này chạy được, dạng ">=X.Y.Z".
     *
     * Không khai thì không ràng buộc — flow cũ vẫn cài được sau khi engine biết đọc
     * khoá này.
     *
     * ⚠️ **PHẢI đặt trong ngoặc kép** trong `pack.yaml`: `requiresEngine: ">=6.20.0"`.
     * Nếu viết `requiresEngine: >=6.20.0` (không quote), js-yaml đọc `>=` theo cú pháp
     * block-scalar của YAML và gãy parser, tạo ra đúng thứ "lỗi lạ giữa chừng cài đặt"
     * mà tính năng này sinh ra để tránh.
     */
    requiresEngine?: string;
    gitignore?: GitignorePolicy;
    global?: GlobalPolicy;
}
/** Pack directories shipped with this package. */
export declare function builtInPacks(): string[];
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
export declare function resolvePackName(input: string): string;
export declare function resolvePackInfo(input: string, projectPath: string): PackInfo;
/**
 * Read a pack straight from a directory.
 *
 * For tests that need a pack shape no shipped pack has: every pack in `skills/` now
 * hands its wiring to its own script, which leaves the installer's own wiring — hooks,
 * rules, the gitignore policy, the per-repo config — with nothing exercising it.
 */
export declare function readPackInfoFrom(packDir: string): PackInfo;
export declare function skillList(projectPath: string): SkillListEntry[];
export declare function skillInfo(name: string, projectPath: string): SkillInfoResult;
export declare function skillRemove(name: string, projectPath: string): SkillRemoveResult;
export declare function skillAdd(source: string, projectPath: string, options: SkillAddOptions): SkillAddResult;
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
export declare function renderCommandFile(name: string, skillFile: string): string;
export interface WorkflowCommandsResult {
    /** Tên đã ghi ra đĩa trong lượt này. */
    created: string[];
    /**
     * Mọi tên pack này chịu trách nhiệm, kể cả file đã có sẵn nên không ghi lại.
     * Đây mới là thứ vào manifest: ghi "lượt này không tạo gì" sẽ khiến các file
     * do lượt trước tạo ra không bao giờ gỡ được.
     */
    owned: string[];
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
export declare function scaffoldWorkflowCommands(workflows: Record<string, string>, projectPath: string, skillsDir: string, options?: {
    overwrite?: boolean;
}): WorkflowCommandsResult;
export declare function skillInit(packName: string, projectPath: string, skillNames: string[], options?: SkillInitOptions): SkillInitResult;
export declare function findPackageRoot(): string;
export declare function resolveSource(source: string): string;
//# sourceMappingURL=skill.d.ts.map