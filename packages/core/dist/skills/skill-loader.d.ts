export interface Skill {
    name: string;
    description: string;
    version?: string;
    author?: string;
    body: string;
}
export declare function loadSkill(name: string, projectPath: string): Skill;
//# sourceMappingURL=skill-loader.d.ts.map