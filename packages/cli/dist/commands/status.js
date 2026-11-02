"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRunStatuses = getRunStatuses;
exports.formatStatuses = formatStatuses;
exports.formatFlowVersions = formatFlowVersions;
const path_1 = require("path");
const core_1 = require("@vsaf/core");
const manifest_js_1 = require("./install/manifest.js");
function getRunStatuses(projectPath) {
    const storeDir = (0, path_1.join)(projectPath, '.vsaf', 'storage');
    const store = new core_1.RunStore(storeDir);
    return store.listAll();
}
function formatStatuses(runs) {
    if (runs.length === 0)
        return 'No workflow runs found.';
    const lines = runs.map(r => {
        const icon = r.status === 'completed' ? '✓' : r.status === 'failed' ? '✗' : '●';
        return `${icon} ${r.runId}  ${r.workflow.padEnd(20)} ${r.status.padEnd(10)} ${r.startedAt}`;
    });
    return lines.join('\n');
}
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
function formatFlowVersions(projectPath) {
    const records = (0, manifest_js_1.allInstalls)(projectPath);
    if (records.length === 0)
        return '';
    const lines = records.map(record => {
        const from = record.flowOrigin === 'repo'
            ? `repo flows @ ${record.flowCommit?.slice(0, 8) ?? '?'}`
            // Sổ ghi trước khi engine biết đóng dấu nguồn gốc thì không có trường nào để đọc, và
            // đoán "bản kèm theo" ở đó là bịa. Nói đúng là không biết.
            : record.flowOrigin === 'bundled' ? 'bản kèm theo gói npm' : 'không rõ (sổ cài đặt cũ)';
        return `  ${record.pack.padEnd(20)} ${from}`;
    });
    return ['Bản flow đang dùng:', ...lines].join('\n');
}
//# sourceMappingURL=status.js.map