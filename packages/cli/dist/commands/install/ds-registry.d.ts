/** Where every design system of a project lives, relative to the spec repo. */
export declare const DS_FAMILY: string;
/** The file listing each design system and which repo owns it. */
export declare const REGISTRY_FILE = "registry.yaml";
export interface DesignSystems {
    /** Registry path when one was written, absent when a single system needs none. */
    registry?: string;
    /**
     * Sub-directory under the family root per code repo, keyed by absolute repo path.
     * An absent key means that repo uses the family root itself.
     */
    roots: Map<string, string>;
    /** Set when the layout could not be split and a person has to finish the job. */
    warning?: string;
}
/** Directory-safe id derived from the repo name, matching what the skills expect. */
export declare function designSystemId(repoName: string): string;
/**
 * Describe what `resolveDesignSystems` would do, without writing anything.
 *
 * Returns null when there is nothing to say — one front end needs no registry.
 */
export declare function planDesignSystems(specRepo: string, codeRepos: string[]): string | null;
/**
 * Decide which design system each code repo uses, and write the registry when a
 * project needs more than one.
 *
 * One front end needs no registry: its design system is the family root, and a
 * registry would only add a file to keep in sync. Two or more each get their own
 * namespaced root, because a single shared root would let one repo's tokens
 * silently overwrite another's.
 *
 * The one case left to a person is a project that already has a flat design system
 * and has since grown a second front end: nothing in the files says which repo the
 * existing tokens belong to, so guessing could attach them to the wrong repo.
 */
export declare function resolveDesignSystems(specRepo: string, codeRepos: string[]): DesignSystems;
//# sourceMappingURL=ds-registry.d.ts.map