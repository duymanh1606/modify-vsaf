import type { VSAFConfig } from '../config/config-loader.js';
import { WorkspaceManager, type Workspace } from './workspace-manager.js';
/**
 * Điểm quyết định DUY NHẤT cho việc chọn chiến lược workspace theo
 * config.isolation.type. Mọi entry point (CLI `run`, HTTP execution-manager,
 * MCP server) phải gọi hàm này thay vì gọi thẳng `wsManager.create()` —
 * trước đây isolation.type: none bị bỏ qua hoàn toàn (mọi nơi đều tạo bản
 * copy /tmp), khiến test-gate không thấy code Claude vừa ghi vào project
 * (bug A).
 *
 * - 'ephemeral' (mặc định, kể cả khi config thiếu `type`): giữ nguyên hành
 *   vi cũ — uỷ quyền cho `WorkspaceManager.create()` (git worktree nếu
 *   project có .git, ngược lại copy sang thư mục tạm dưới /tmp).
 * - 'none': không copy, không tạo worktree — AI/bash thao tác trực tiếp
 *   trên projectPath (sourcePath === projectPath).
 */
export declare function resolveWorkspace(config: Pick<VSAFConfig, 'isolation'>, projectPath: string, workflowName: string, wsManager: WorkspaceManager): Promise<Workspace>;
//# sourceMappingURL=workspace-resolver.d.ts.map