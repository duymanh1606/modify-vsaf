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
export declare function initGitRepo(projectPath: string): string | null;
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
export declare function prepareNewProject(cwd: string, name: string): string;
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
export declare function commitInitial(projectPath: string, message: string): boolean;
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
export declare function refreshInitialCommit(projectPath: string): 'amended' | 'nothing' | 'failed';
/**
 * Why a path cannot be brought into the project, or null when it can.
 *
 * Split out from the copying so the answer can be had before the install writes
 * anything: adopting is one of the last steps, and finding out there that a path is a
 * file leaves a directory half set up.
 *
 * Reads the disk, changes nothing.
 */
export declare function adoptProblem(specRepo: string, given: string): string | null;
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
export declare function adoptCodeRepos(specRepo: string, paths: string[]): string[];
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
export declare function offerCredentialHelper(count: number, deps?: {
    configured?: () => string | undefined;
    osHelper?: () => string | undefined;
    say?: (line: string) => void;
}): 'đã có' | 'đã nhắc';
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
export declare function mayAskForPassword(urls: string[]): boolean;
/** Directory name a url clones into: the last segment, without a trailing `.git`. */
export declare function targetName(url: string): string;
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
export declare function refusesTheAsker(reason: string[]): boolean;
/**
 * Wait for the person at the keyboard to say they have dealt with it.
 *
 * Synchronous on purpose: the whole install is, and making it asynchronous would force
 * `execInstall` — and the thirty tests calling it — to become asynchronous too (ADR D-1).
 * Reads one byte at a time until a newline; returns false when there is nothing to read
 * from, which is every case where nobody is watching.
 */
export declare function waitForEnter(): boolean;
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
export declare function headerForms(credential: {
    secret: string;
    username?: string;
}): string[];
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
export declare function cloneCodeRepos(specRepo: string, urls: string[], options?: {
    pause?: (left: number, home: string) => boolean;
    token?: string;
}): string[];
/**
 * Clone repos into a directory named outright.
 *
 * Same work as `cloneCodeRepos`, which is this with the directory worked out from a spec
 * repo. Named separately because fetching repos is now its own command: someone joining a
 * project has no spec repo on disk yet — that is one of the things they are here to fetch —
 * so there is no repo to derive the parent from.
 */
export declare function cloneInto(parent: string, urls: string[], options?: {
    pause?: (left: number, home: string) => boolean;
    token?: string;
}): string[];
//# sourceMappingURL=bootstrap-repo.d.ts.map