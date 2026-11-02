import { type SkillInitResult } from './skill.js';
/**
 * Câu tổng kết cho bước mang repo về: đã tải mấy cái, đã có sẵn mấy cái.
 *
 * Separate from the install so it can be read at a glance and tested without running one.
 *
 * `fetched` and `kept` are counted apart on purpose. `cloneInto` returns both — a repo
 * already sitting beside the project is kept and reported, which is right — and adding
 * them up told six people repos had come down when five had, the sixth being the spec
 * repo this very run had just created.
 *
 * `beside` is the `--code-repos` case: nothing was brought in because the repos are
 * already on disk, and saying "chưa clone repo nào" right after someone typed the flag
 * reads as the flag being ignored.
 */
export declare function broughtLine(fetched: number, kept: number, beside: number): string;
/**
 * The command that continues this install, spelled out.
 *
 * Rebuilt from the options rather than from `process.argv`, so it is the same string
 * whether the install was started from the command line, from another command, or
 * from a test.
 */
export declare function rerunCommand(pack: string, options: InstallOptions): string;
/**
 * Files in a code repo that hold the repo's own content alongside ours: an install
 * edits them in place, so they must never reach the list of paths an uninstall
 * deletes. They are restored by removing our block instead.
 */
export declare const SHARED_IN_CODE_REPO: readonly [string, "CLAUDE.md", ".gitignore", ".claude/skills", ".cursor/skills"];
export interface InstallOptions {
    force?: boolean;
    skipDeps?: boolean;
    /**
     * Approve writing the pack's skills into the tool directories under the user's
     * home. Off by default: personal configuration is not the installer's to change.
     */
    syncGlobal?: boolean;
    /**
     * Names of the code repos beside a spec repo to wire up. Nothing is wired unless
     * named: siblings in the same parent directory may belong to other projects.
     */
    codeRepos?: string[];
    /** Project name for the workspace file and the placeholders. Defaults to the directory name. */
    projectName?: string;
    /** Urls of code repos to clone beside this project, then wire. */
    clone?: string[];
    /** Paths of code repos already on disk to copy beside this project, then wire. */
    adopt?: string[];
    /**
     * Recreate only what is machine-local, for someone joining a project that is
     * already set up. Committed files arrived with their clone and are left alone.
     */
    refresh?: boolean;
    /**
     * Re-wire a project that has gained code repos since it was set up: everything a
     * first install does bar naming the project, which is already named.
     *
     * Kept apart from `refresh` because refresh skips the committed files — the
     * workspace file and the gitignore blocks — and a project going from one repo to
     * several needs exactly those rewritten. Reaching for refresh here is the documented
     * mistake, so the flag it should have been exists under its own name.
     */
    upgrade?: boolean;
    /**
     * Confirm this directory is the project root even though it holds code. Without
     * it, installing a pack that ships a project skeleton into a code repo is refused.
     */
    projectRoot?: boolean;
    /** Print what an install would do and write nothing. */
    dryRun?: boolean;
    /**
     * Throw away the flow cache on this machine and clone it again.
     *
     * The way out of a cache left broken by a run that died mid-clone. Not the default:
     * every install would then pay for a full clone of the flows repo.
     */
    refreshFlows?: boolean;
    /** Show the wiring script's full narration instead of only its warnings. */
    verbose?: boolean;
    /**
     * Flags to hand straight to the pack's own wiring script, from after a bare `--`.
     *
     * There so the upstream script can grow a flag without this installer needing to
     * learn it: the user forwards it, rather than waiting for a release here.
     */
    passthrough?: string[];
    /**
     * Things the caller asked for and could not get before the install began — a
     * project link that could not be read, for one. Repeated in the closing summary
     * and counted among its issues: they are said long before the install's hundred
     * lines of output, and "Install complete: 0 issue(s)" at the bottom of that is a
     * false account of what the user asked for.
     */
    unresolved?: string[];
}
export interface DeployResult {
    deployed: string[];
    skipped: string[];
}
export interface BinaryCheck {
    name: string;
    found: boolean;
    required: boolean;
    version?: string;
}
export interface GraphifyResult {
    installed: boolean;
    version?: string;
    skillDeployed: boolean;
    error?: string;
}
export interface InstallResult {
    deploy: DeployResult;
    binaries: BinaryCheck[];
    depsRan: boolean;
    graphify: GraphifyResult;
    /** Workflows and slash commands written for the pack. */
    scaffold: SkillInitResult;
    /** Paths written outside the project. Empty unless the user approved it. */
    globalSynced: string[];
    /** Paths written by the multi-repo wiring, relative to this project. */
    wired: string[];
    /**
     * What the self-test found wrong with the install it just did. Empty means sound.
     * Handed back so the command can exit non-zero on it: printing a warning and
     * exiting 0 told every script that a broken install had succeeded.
     */
    problems: string[];
    /**
     * Thư mục nội dung flow mà lượt cài này đã dùng.
     *
     * Có để lớp lệnh không phải đi hỏi lại lần thứ hai. `resolveSource(pack)` chỉ biết các
     * pack ship trong gói npm, nên câu trả lời của nó lệch khỏi thứ vừa được cài ngay khi
     * repo flows có nội dung khác — và sau bước 7.0 (bỏ `skills/` khỏi npm) thì nó không
     * còn câu trả lời nào.
     */
    flowDir?: string;
}
export interface InternalInstallOptions extends InstallOptions {
    _skillsDir?: string;
    _skipGraphify?: boolean;
    /**
     * Install from this directory instead of a pack shipped in `skills/`, for testing.
     *
     * Every shipped pack now either deploys skills and stops, or hands its wiring to its
     * own script. Neither shape reaches the installer's own wiring — hooks, coding rules,
     * the gitignore policy, the per-code-repo config — so a test wanting that path has to
     * bring a pack with it.
     */
    _packDir?: string;
}
/**
 * Deploy a pack's `_shared/` assets (helper files skills reference at runtime,
 * e.g. the sonar-viettel quality profile/gate) to `<skillsDir>/_shared/<pack>/`.
 *
 * Namespaced by pack so two packs' helpers never collide, and always overwritten
 * (no --force) so helpers stay in sync with the skills that read them. Returns
 * the deployed entry name, or null when the pack ships no `_shared/`.
 *
 * Deploying skills is `vsaf install`'s job alone, so this belongs to it — the assets a
 * skill reads have to arrive with the skill.
 */
export declare function deploySharedAssets(packDir: string, pack: string, skillsDir: string): string | null;
export declare function deploySkills(packDir: string, packName: string, skills: string[], targetDir: string, options: {
    force?: boolean;
    noPrefix?: boolean;
}): DeployResult;
export declare function checkBinaries(): BinaryCheck[];
export declare function installGraphify(): GraphifyResult;
/**
 * Cài một flow vào project.
 *
 * Vỏ mỏng quanh `runInstall` để phần telemetry của flow được ghi trên MỌI đường cài —
 * script của chính flow, script `wiring` của pack, hay đường engine tự rải. Ba đường đó
 * `return` ở ba chỗ khác nhau, nên đặt bước này ở từng chỗ là ba lần phải nhớ; ở đây
 * thì không nhớ cũng đúng. Chạy thử không trả về `flowDir`, nên nó không ghi gì.
 */
export declare function execInstall(input: string, projectPath: string, options?: InternalInstallOptions): InstallResult;
//# sourceMappingURL=install.d.ts.map