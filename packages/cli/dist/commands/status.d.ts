import { type WorkflowRun } from '@vsaf/core';
export declare function getRunStatuses(projectPath: string): WorkflowRun[];
export declare function formatStatuses(runs: WorkflowRun[]): string;
/**
 * Bản flow dự án này đang chạy — §6 spec.
 *
 * `flowOrigin` và `flowCommit` được ghi vào sổ cài đặt từ nhánh tách flow, nhưng không ai
 * đọc, nên câu "máy này đang chạy bản flow nào" vẫn chưa trả lời được bằng một lệnh. Đây
 * là chỗ trả lời: hai máy cài cùng một flow mà ra hai kết quả khác nhau thì đây là dòng
 * phân biệt được chúng.
 *
 * Rỗng khi dự án chưa cài flow nào — `vsaf status` vốn nói về lượt chạy workflow, và một
 * mục trống là một mục để cuộn qua.
 */
export declare function formatFlowVersions(projectPath: string): string;
//# sourceMappingURL=status.d.ts.map