/**
 * What a pack put into the project. Uninstall reads it back, so anything the
 * installer creates and does not record here becomes undeletable litter.
 */
export interface InstallRecord {
    pack: string;
    /** Directory holding the skills, relative to the project. */
    canonicalDir: string;
    /**
     * Directories earlier installs used for the skills. Kept because a pack that
     * changes where it puts them would otherwise leave the old copies undeletable.
     */
    previousCanonicalDirs?: string[];
    /** Skill directory names, prefixed and bundled alike. */
    skills: string[];
    /** Hook file names, relative to the hooks directory. */
    hooks: string[];
    /** Rule file names installed under `.claude/rules`. */
    rules: string[];
    /** Slash command file names under `.vsaf/commands`. */
    commands: string[];
    /** Whether the pack has its own workflow directory to drop. */
    hasWorkflows: boolean;
    /**
     * Paths the multi-repo wiring created, relative to this project — config files,
     * cross-repo links, commit guards, the workspace file. Relative so the record
     * survives being cloned.
     */
    wired?: string[];
    /**
     * Repos whose CLAUDE.md received a scope block, relative to this project. Listed
     * apart from `wired` because those files belong to their repos: only the block
     * comes back out, never the file.
     */
    scopedRepos?: string[];
    /** Nội dung flow lấy từ repo flows hay từ bản kèm gói npm. */
    flowOrigin?: 'repo' | 'bundled';
    /** Mã commit của repo flows. Chỉ có khi `flowOrigin` là `repo`. */
    flowCommit?: string;
    /**
     * The spec repo's config file, relative to the project. Named here so the
     * self-test can prove the skills can read it, not merely that it exists.
     */
    specConfig?: string;
}
/**
 * Every place this project's record for a pack may live, best first.
 *
 * `[0]` is where a new record is written; the whole list is what a read has to look
 * through. Two places rather than one because the single old location, `.vsaf/`,
 * does not exist in a project that was never initialised — and an install there
 * recorded nothing at all, which is how a half-finished install became impossible
 * to undo.
 *
 * An empty list means there is nowhere to write yet. That is reported, never fixed
 * by creating a directory the user did not ask for.
 */
export declare function recordPaths(projectPath: string, pack: string): string[];
/**
 * Write the record, folding in whatever an earlier install of the same pack left.
 *
 * Recording only what the current run created loses everything an earlier run made
 * and this one skipped as "already there" — the workflows, the generated config, the
 * skills in a directory the pack has since moved away from. Uninstall reads the
 * record, so anything that falls out of it becomes undeletable.
 *
 * Called after every step of an install rather than once at the end: a run that dies
 * half way still has to leave behind a list of what it made.
 *
 * Returns the file written, or null when the project offers nowhere to write one.
 */
export declare function recordInstall(projectPath: string, record: InstallRecord): string | null;
/**
 * The record for a pack, merged across every place one was found.
 *
 * Both places hold a true account of a different install, so the union is the only
 * safe reading: dropping either one leaves files nothing will ever remove.
 */
export declare function readInstall(projectPath: string, pack: string): InstallRecord | null;
export declare function forgetInstall(projectPath: string, pack: string): void;
/**
 * Sổ cài đặt của mọi flow trong dự án này.
 *
 * Quét cả hai chỗ và gộp lại, cùng luật với `readInstall`. Dùng cho `vsaf status`: §6 spec
 * hứa "bản flow đang dùng … hiện ra ở `vsaf status`", và hai trường `flowOrigin` /
 * `flowCommit` được ghi từ nhánh trước nhưng chưa ai đọc — nên câu "máy này đang chạy bản
 * flow nào" vẫn chưa trả lời được bằng một lệnh.
 */
export declare function allInstalls(projectPath: string): InstallRecord[];
/**
 * Records of every other installed pack — what must not be removed.
 *
 * Both locations are scanned. Missing one means missing a pack, and an uninstall
 * that cannot see a pack takes the skills that pack still reads.
 */
export declare function otherInstalls(projectPath: string, pack: string): InstallRecord[];
//# sourceMappingURL=manifest.d.ts.map