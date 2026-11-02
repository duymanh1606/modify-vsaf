import type { PackInfo } from '../skill.js';
export interface PlanOptions {
    force?: boolean;
    refresh?: boolean;
    upgrade?: boolean;
    syncGlobal?: boolean;
    codeRepos?: string[];
    /** Repo urls to clone beside the project, and paths to copy in. */
    clone?: string[];
    adopt?: string[];
    projectName?: string;
}
export declare function planInstall(packDir: string, packName: string, projectPath: string, info: PackInfo, options?: PlanOptions): string[];
//# sourceMappingURL=plan.d.ts.map