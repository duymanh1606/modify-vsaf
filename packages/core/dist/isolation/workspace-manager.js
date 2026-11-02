"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WorkspaceManager = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const os_1 = require("os");
const crypto_1 = require("crypto");
const child_process_1 = require("child_process");
const util_1 = require("util");
const exec = (0, util_1.promisify)(child_process_1.exec);
class WorkspaceManager {
    workspaces = new Map();
    exclude;
    constructor(options) {
        this.exclude = new Set(options.exclude);
    }
    async create(projectPath, workflowName) {
        const hasGit = (0, fs_1.existsSync)((0, path_1.join)(projectPath, '.git'));
        if (hasGit) {
            return this.createWorktree(projectPath, workflowName);
        }
        return this.createEphemeral(projectPath, workflowName);
    }
    async createWorktree(projectPath, workflowName) {
        const id = `run-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
        const branchName = `vsaf/${workflowName}/${id}`;
        const worktreePath = (0, path_1.join)(projectPath, '.vsaf', 'worktrees', id);
        (0, fs_1.mkdirSync)((0, path_1.join)(projectPath, '.vsaf', 'worktrees'), { recursive: true });
        await exec(`git worktree add -b "${branchName}" "${worktreePath}"`, {
            cwd: projectPath,
        });
        const artifactsPath = (0, path_1.join)(worktreePath, '.vsaf', 'artifacts');
        (0, fs_1.mkdirSync)(artifactsPath, { recursive: true });
        const workspace = {
            id,
            sourcePath: worktreePath,
            branchName,
            artifactsPath,
            projectPath,
            type: 'worktree',
        };
        this.workspaces.set(id, workspace);
        return workspace;
    }
    createEphemeral(projectPath, _workflowName) {
        const id = `run-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
        const rootPath = (0, fs_1.mkdtempSync)((0, path_1.join)((0, os_1.tmpdir)(), `vsaf-${id}-`));
        const sourcePath = (0, path_1.join)(rootPath, 'source');
        const artifactsPath = (0, path_1.join)(rootPath, 'artifacts');
        (0, fs_1.mkdirSync)(sourcePath, { recursive: true });
        (0, fs_1.mkdirSync)(artifactsPath, { recursive: true });
        (0, fs_1.cpSync)(projectPath, sourcePath, {
            recursive: true,
            filter: (src) => {
                const rel = (0, path_1.relative)(projectPath, src);
                if (rel === '')
                    return true;
                const topLevel = rel.split('/')[0];
                return !this.exclude.has(topLevel);
            },
        });
        const workspace = {
            id,
            sourcePath,
            artifactsPath,
            projectPath,
            type: 'ephemeral',
        };
        this.workspaces.set(id, workspace);
        return workspace;
    }
    /**
     * isolation.type: 'none' — không copy, không tạo worktree. AI/bash thao
     * tác trực tiếp trên projectPath (sourcePath === projectPath), nên
     * artifactsPath phải là một thư mục ổn định BÊN TRONG project — không
     * nằm dưới /tmp — để test-gate (chạy trên project thật) luôn thấy đúng
     * code vừa ghi. Được đăng ký vào this.workspaces như mọi workspace khác
     * để diff/applyChanges/destroy có thể tra cứu an toàn (xem các nhánh
     * 'none' bên dưới — không nhánh nào trong số đó đụng tới project).
     */
    createNone(projectPath) {
        const id = `none-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
        const artifactsPath = (0, path_1.join)(projectPath, '.vsaf', 'artifacts', id);
        (0, fs_1.mkdirSync)(artifactsPath, { recursive: true });
        const workspace = {
            id,
            sourcePath: projectPath,
            artifactsPath,
            projectPath,
            type: 'none',
        };
        this.workspaces.set(id, workspace);
        return workspace;
    }
    /**
     * Re-adopt a workspace created by a previous engine process, from the paths
     * persisted in the run's state.json. Worktree id/branch are reconstructed
     * from the same conventions createWorktree used (id = dir name, branch =
     * vsaf/{workflow}/{id}).
     */
    reattach(params) {
        // isolation.type: none — không có bản copy/worktree nào để "gắn lại":
        // workspacePath đã được persist chính là projectPath. Phải nhận diện
        // TRƯỚC nhánh existsSync/isWorktree bên dưới — nếu không, workspace này
        // sẽ rơi vào nhánh 'ephemeral' và destroy() sẽ rmSync(join(sourcePath,
        // '..')), tức là xoá THƯ MỤC CHA của chính project người dùng.
        if (params.workspacePath === params.projectPath) {
            const id = `none-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
            const workspace = {
                id,
                sourcePath: params.workspacePath,
                artifactsPath: params.artifactsPath,
                projectPath: params.projectPath,
                type: 'none',
            };
            this.workspaces.set(id, workspace);
            return workspace;
        }
        if (!(0, fs_1.existsSync)(params.workspacePath)) {
            throw new Error(`Workspace at ${params.workspacePath} no longer exists — start a new run.`);
        }
        const worktreeRoot = (0, path_1.join)(params.projectPath, '.vsaf', 'worktrees');
        const isWorktree = params.workspacePath.startsWith(worktreeRoot);
        const id = isWorktree
            ? (0, path_1.relative)(worktreeRoot, params.workspacePath).split(/[\\/]/)[0]
            : `run-${(0, crypto_1.randomBytes)(6).toString('hex')}`;
        const workspace = {
            id,
            sourcePath: params.workspacePath,
            branchName: isWorktree ? `vsaf/${params.workflow}/${id}` : undefined,
            artifactsPath: params.artifactsPath,
            projectPath: params.projectPath,
            type: isWorktree ? 'worktree' : 'ephemeral',
        };
        this.workspaces.set(id, workspace);
        return workspace;
    }
    async diff(workspaceId) {
        const ws = this.getWorkspace(workspaceId);
        if (ws.type === 'worktree') {
            return this.diffWorktree(ws);
        }
        if (ws.type === 'none') {
            // sourcePath === projectPath: không có gì để so sánh, mọi thay đổi
            // AI ghi đã nằm sẵn trong project rồi.
            return { modified: [], added: [], deleted: [] };
        }
        return this.diffEphemeral(ws);
    }
    async diffWorktree(ws) {
        const { stdout } = await exec(`git diff HEAD~1 --name-status`, { cwd: ws.sourcePath }).catch(() => ({ stdout: '' }));
        return this.parseDiffOutput(stdout);
    }
    diffEphemeral(ws) {
        const modified = [];
        const added = [];
        const deleted = [];
        this.walkDir(ws.sourcePath, ws.sourcePath, (relPath, wsFilePath) => {
            const projFilePath = (0, path_1.join)(ws.projectPath, relPath);
            if (!(0, fs_1.existsSync)(projFilePath)) {
                added.push(relPath);
            }
            else {
                const wsContent = (0, fs_1.readFileSync)(wsFilePath);
                const projContent = (0, fs_1.readFileSync)(projFilePath);
                if (!wsContent.equals(projContent)) {
                    modified.push(relPath);
                }
            }
        });
        return { modified, added, deleted };
    }
    parseDiffOutput(stdout) {
        const modified = [];
        const added = [];
        const deleted = [];
        for (const line of stdout.trim().split('\n')) {
            if (!line)
                continue;
            const [status, file] = line.split('\t');
            if (status === 'M')
                modified.push(file);
            else if (status === 'A')
                added.push(file);
            else if (status === 'D')
                deleted.push(file);
        }
        return { modified, added, deleted };
    }
    async applyChanges(workspaceId) {
        const ws = this.getWorkspace(workspaceId);
        if (ws.type === 'worktree') {
            return this.applyWorktreeChanges(ws);
        }
        if (ws.type === 'none') {
            // Đã ghi thẳng vào project rồi, không cần "áp" lại gì cả.
            return { modified: [], added: [], deleted: [] };
        }
        return this.applyEphemeralChanges(ws);
    }
    async applyWorktreeChanges(ws) {
        const diff = await this.diff(ws.id);
        await exec(`git merge "${ws.branchName}" --no-edit`, {
            cwd: ws.projectPath,
        });
        return diff;
    }
    applyEphemeralChanges(ws) {
        const modified = [];
        const added = [];
        this.walkDir(ws.sourcePath, ws.sourcePath, (relPath, wsFilePath) => {
            const projFilePath = (0, path_1.join)(ws.projectPath, relPath);
            if (!(0, fs_1.existsSync)(projFilePath)) {
                added.push(relPath);
            }
            else {
                const wsContent = (0, fs_1.readFileSync)(wsFilePath);
                const projContent = (0, fs_1.readFileSync)(projFilePath);
                if (!wsContent.equals(projContent)) {
                    modified.push(relPath);
                }
            }
            (0, fs_1.mkdirSync)((0, path_1.join)(projFilePath, '..'), { recursive: true });
            (0, fs_1.copyFileSync)(wsFilePath, projFilePath);
        });
        return { modified, added, deleted: [] };
    }
    async destroy(workspaceId) {
        const ws = this.getWorkspace(workspaceId);
        if (ws.type === 'worktree') {
            await exec(`git worktree remove "${ws.sourcePath}" --force`, {
                cwd: ws.projectPath,
            });
            await exec(`git branch -D "${ws.branchName}"`, {
                cwd: ws.projectPath,
            });
        }
        else if (ws.type === 'none') {
            // KHÔNG xoá gì cả — ws.sourcePath chính là project thật của người
            // dùng, không phải bản copy dùng-xong-thì-xoá. Đây là điểm chốt an
            // toàn: nếu một call site nào đó lỡ coi workspace này là disposable
            // và gọi destroy(), no-op này đảm bảo project không bao giờ bị đụng.
            this.workspaces.delete(workspaceId);
            return;
        }
        else {
            const rootPath = (0, path_1.join)(ws.sourcePath, '..');
            (0, fs_1.rmSync)(rootPath, { recursive: true, force: true });
        }
        this.workspaces.delete(workspaceId);
    }
    getWorkspace(id) {
        const ws = this.workspaces.get(id);
        if (!ws)
            throw new Error(`Workspace not found: ${id}`);
        return ws;
    }
    walkDir(basePath, currentPath, callback) {
        for (const entry of (0, fs_1.readdirSync)(currentPath)) {
            const fullPath = (0, path_1.join)(currentPath, entry);
            const stat = (0, fs_1.statSync)(fullPath);
            if (stat.isDirectory()) {
                this.walkDir(basePath, fullPath, callback);
            }
            else {
                callback((0, path_1.relative)(basePath, fullPath), fullPath);
            }
        }
    }
}
exports.WorkspaceManager = WorkspaceManager;
//# sourceMappingURL=workspace-manager.js.map