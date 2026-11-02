export interface Command {
    name: string;
    description: string;
    argumentHint?: string;
    skill?: string;
    body: string;
}
export declare function loadCommand(name: string, projectPath: string): Command;
//# sourceMappingURL=command-loader.d.ts.map