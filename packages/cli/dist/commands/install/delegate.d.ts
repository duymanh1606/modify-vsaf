import type { PackInfo } from '../skill.js';
/**
 * The shell that will run the pack's scripts, or null.
 *
 * PATH first, so a machine that has arranged its own shell keeps it. The Windows
 * locations are only tried after that, and `wsl` last: it works, but it puts the
 * script in a different filesystem view than the paths it was handed.
 */
export declare function findBash(): string | null;
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
export declare function pythonStubOnPath(): string | null;
export declare function findPython(): string | null;
/**
 * Whether this machine lets a symlink be created at all.
 *
 * Asked by trying, because there is no way to ask. Windows needs Developer Mode or
 * an elevated shell, and without it the wiring silently ends up as copies: the
 * install reports success, the gates never fire, and nothing says so. Knowing the
 * answer up front turns that into a sentence the user can act on.
 */
export declare function canSymlink(): boolean;
export interface Environment {
    bash: string;
    python: string | null;
    symlink: boolean;
}
/**
 * Check what the pack's scripts need, and report it as one block before anything is
 * written. Throws when the shell is missing, since nothing below it can run.
 */
export declare function checkEnvironment(): Environment;
/**
 * Say so when a repo was named that the wiring script will not act on.
 *
 * It only wires siblings that are git repos — reasonably, since there is nowhere to
 * install a commit hook in a directory that is not one. Naming such a directory used to
 * look like it worked: the install finished, and the repo simply had nothing in it.
 * Better to say it out loud than leave it to be noticed later.
 */
export declare function warnUnwirableRepos(projectPath: string, named: string[]): void;
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
export declare function assertScopeIsKnown(projectPath: string, broughtIn: string[], named: boolean, pack?: string): void;
/**
 * Refuse a re-wire of a project the pack was never installed into.
 *
 * `--refresh` and `--upgrade` both mean "the project is laid out, wire it again", so
 * neither copies anything — which leaves nothing to call when the project has no copy
 * yet. Without this the shell reports the missing file, and `bash: ./scripts/bootstrap.sh:
 * No such file or directory` says nothing about which flag to drop.
 */
export declare function assertWiringScriptPresent(projectPath: string, info: PackInfo, rewiring: boolean): void;
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
export declare function copyPackIntoProject(packDir: string, projectPath: string, info: PackInfo, options?: {
    force?: boolean;
}): string[];
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
export declare function repairCommandFrontMatter(projectPath: string): string[];
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
export declare function pythonShimDir(): {
    dir: string;
    cleanup: () => void;
} | null;
export declare function runWiring(bash: string, projectPath: string, info: PackInfo, options: {
    projectName: string;
    passthrough: string[];
    verbose?: boolean;
}): void;
/**
 * Hand the machine-wide skills over to the pack's own sync script.
 *
 * Run inside the pack directory, which is why the pack keeps its upstream layout: the
 * script reads its sources relative to itself, so no staging directory has to be built
 * and thrown away on every run.
 */
export declare function runGlobalSync(bash: string, packDir: string, info: PackInfo, flags: string[], verbose?: boolean, pack?: string): void;
/** Home directory, refused as an install target: it is nobody's project. */
export declare function refuseHomeDirectory(projectPath: string): void;
/**
 * Máy này chưa có thư viện skill của pack hay chưa — vị từ thuần, không in gì.
 *
 * Tách khỏi hàm cảnh báo vì lượt cài cần biết điều này **trước** khi chạy script (script
 * của flow có thể tự sync), rồi so lại **sau** khi script xong. Một hàm vừa đo vừa in
 * không dùng được cho phép so đó.
 */
export declare function skillsLibraryMissing(packDir: string, packInfo: PackInfo): boolean;
/**
 * Warn when the pack's skill library is not on this machine yet.
 *
 * `vsaf sync` puts the skills under `$HOME`, `vsaf install` wires a project to them.
 * Skipping the first step leaves an install that reports success and a project where no
 * `/pack-*` command resolves — and the failure then shows up much later, inside a
 * workflow, as an empty artifact rather than a missing skill. So say it here, where the
 * fix is one command away.
 */
export declare function warnIfSkillsNotSynced(packDir: string, packInfo: PackInfo, pack: string): boolean;
/**
 * Whether `init` has already run here — the telemetry section is what it writes that
 * nothing else does. Read rather than warned about now that `install` runs `init` itself:
 * the only thing left to decide is whether to run it again.
 */
export declare function isProjectInitialised(projectPath: string): boolean;
//# sourceMappingURL=delegate.d.ts.map