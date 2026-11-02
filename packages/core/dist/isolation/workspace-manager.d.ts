export interface Workspace {
    id: string;
    sourcePath: string;
    branchName?: string;
    artifactsPath: string;
    projectPath: string;
    /**
     * 'none' = isolation.type: none — sourcePath === projectPath, không có bản
     * copy/worktree nào để "dùng xong rồi xoá". Giá trị này tồn tại để mọi nơi
     * gọi diff/applyChanges/destroy có thể phân biệt và không coi workspace là
     * disposable (xem createNone(), reattach(), và các nhánh 'none' bên dưới).
     */
    type: 'worktree' | 'ephemeral' | 'none';
}
export interface DiffResult {
    modified: string[];
    added: string[];
    deleted: string[];
}
interface WorkspaceManagerOptions {
    exclude: string[];
}
export interface ReattachParams {
    workflow: string;
    workspacePath: string;
    artifactsPath: string;
    projectPath: string;
}
export declare class WorkspaceManager {
    private workspaces;
    private exclude;
    constructor(options: WorkspaceManagerOptions);
    create(projectPath: string, workflowName: string): Promise<Workspace>;
    private createWorktree;
    private createEphemeral;
    /**
     * isolation.type: 'none' — không copy, không tạo worktree. AI/bash thao
     * tác trực tiếp trên projectPath (sourcePath === projectPath), nên
     * artifactsPath phải là một thư mục ổn định BÊN TRONG project — không
     * nằm dưới /tmp — để test-gate (chạy trên project thật) luôn thấy đúng
     * code vừa ghi. Được đăng ký vào this.workspaces như mọi workspace khác
     * để diff/applyChanges/destroy có thể tra cứu an toàn (xem các nhánh
     * 'none' bên dưới — không nhánh nào trong số đó đụng tới project).
     */
    createNone(projectPath: string): Workspace;
    /**
     * Re-adopt a workspace created by a previous engine process, from the paths
     * persisted in the run's state.json. Worktree id/branch are reconstructed
     * from the same conventions createWorktree used (id = dir name, branch =
     * vsaf/{workflow}/{id}).
     */
    reattach(params: ReattachParams): Workspace;
    diff(workspaceId: string): Promise<DiffResult>;
    private diffWorktree;
    private diffEphemeral;
    private parseDiffOutput;
    applyChanges(workspaceId: string): Promise<DiffResult>;
    private applyWorktreeChanges;
    private applyEphemeralChanges;
    destroy(workspaceId: string): Promise<void>;
    private getWorkspace;
    private walkDir;
}
export {};
//# sourceMappingURL=workspace-manager.d.ts.map