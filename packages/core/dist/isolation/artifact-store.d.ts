export declare class ArtifactStore {
    private readonly basePath;
    constructor(basePath: string);
    write(name: string, content: string): Promise<void>;
    read(name: string): Promise<string>;
    exists(name: string): Promise<boolean>;
    list(): Promise<string[]>;
}
//# sourceMappingURL=artifact-store.d.ts.map