/** Where the flow writes its artifacts, and the config file that points at it. */
export declare const ARTIFACT_ROOT = "NTAPP-output";
/**
 * The directories the flow's stages write into.
 *
 * Created up front because a skill that cannot find its output directory fails in
 * the middle of a run, after the expensive part.
 */
export declare const ARTIFACT_DIRS: readonly ["Stage_1_Discovery", "Stage_2_Architecture", "Stage_3_Specs", "Stage_4_Design", "Stage_5_Build_Verify", "design-system", "evaluation", "_notifications"];
/** Create the artifact tree. Existing artifacts are the user's work and stay. */
export declare function scaffoldArtifactTree(specRepo: string): string[];
/**
 * Reserve the place for skills written for this one project.
 *
 * Left empty on purpose, with a keep-file so git tracks the directory. The pack's
 * own skills do not go here — they are reinstallable and live where git ignores
 * them. This directory is the one a code repo is linked at, so a skill added here
 * is seen by every repo in the workspace.
 *
 * Returns the keep-file, or null when the directory already holds something.
 */
export declare function reserveProjectSkills(specRepo: string): string | null;
/**
 * Copy the module configuration the pack's skills read at runtime.
 *
 * An existing copy is left alone: it holds per-project edits, and a reinstall
 * overwriting them would undo work silently.
 *
 * Returns the directory written, or null when there was nothing to write.
 */
export declare function deployModuleConfig(packDir: string, specRepo: string): string | null;
/**
 * Install the shared reference files the design-system skills read at runtime.
 *
 * They do not live beside the skills: every skill resolves them through the artifact
 * tree, as `{design_system_root}/_shared/<name>.md`, so that one project's schemas
 * and procedures are the ones its skills follow. Scaffolding created
 * `design-system` and left it empty, which pointed 153 references across the pack at
 * files no install ever wrote — the bootstrap skill went looking for its own schema
 * and found nothing there.
 *
 * Copied file by file rather than as a directory, for two reasons. A project set up
 * before this shipped already has the directory and none of the files, and must be
 * repaired by reinstalling. And a file already there is the project's copy, which
 * may have been tuned — it stays.
 *
 * Returns the files written, one path each, never the directory holding them. The
 * difference is what an uninstall takes back: the record it reads is a list of paths
 * it deletes, and naming the directory there meant deleting everything inside it —
 * including a file the project put there itself, which the installer never wrote and
 * has no business removing.
 */
export declare function deployDesignSystemShared(packDir: string, specRepo: string): string[];
/**
 * Put the pack's project-context document in place, but only when the project has
 * none. `CLAUDE.md` is the file the agent reads first and the one a team is most
 * likely to have written themselves; overwriting it would replace their words.
 *
 * The copy ships with the project-name placeholder, which the naming step fills in.
 *
 * Returns the file written, or null when one was already there.
 */
export declare function deployProjectContext(packDir: string, specRepo: string, projectName: string): string | null;
/**
 * Put the pack's README in place — the page that tells whoever opens this repo next
 * how the flow runs. Same rule: only when the project has none.
 */
export declare function deployProjectReadme(packDir: string, specRepo: string): string | null;
export declare function deployRepoAssets(packDir: string, specRepo: string): string[];
/**
 * Write the spec repo's own `.bmm-config.yaml`.
 *
 * Generated rather than copied on purpose. The file that shipped with the old
 * template was a leftover from running the bootstrap inside the template itself:
 * it announced itself as a code-repo config and pointed `spec_repo_root` at a
 * personal folder on one machine. Every spec repo made by copying the template
 * inherited that, so 28 skills have been reading paths that resolve nowhere.
 *
 * An existing config is left alone — it may have been tuned by hand.
 *
 * Returns the file written, or null when one was already there.
 */
export declare function writeSpecRepoConfig(specRepo: string, projectName: string): string | null;
//# sourceMappingURL=spec-scaffold.d.ts.map