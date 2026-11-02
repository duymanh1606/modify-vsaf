"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.OPTION_CHANNELS = void 0;
/**
 * Bảng phân loại — và đây là chốt chặn, không phải tài liệu.
 *
 * `Record<keyof InstallOptions, …>` bắt buộc đầy đủ: thêm một lựa chọn vào
 * `InstallOptions` mà quên khai ở đây thì **không biên dịch được**. Đúng kiểu hỏng đã
 * xảy ra — sáu lựa chọn (`clone`, `adopt`, `codeRepos`, `refresh`, `upgrade`,
 * `syncGlobal`) rơi im lặng vì không có chỗ nào buộc phải khai chúng. Đo được: gõ
 * `install NTAPP --new --clone <url>` ra `3/4 Chưa clone repo nào` và thoát 0.
 */
exports.OPTION_CHANNELS = {
    // Năm cờ này vốn đã chảy tốt qua dòng lệnh — để nguyên chỗ cũ, không đưa vào kế hoạch,
    // để một lựa chọn không có hai nguồn sự thật.
    force: 'arg',
    skipDeps: 'arg',
    projectRoot: 'arg',
    verbose: 'arg',
    passthrough: 'arg',
    // Sáu thứ mô tả HÌNH DẠNG dự án. Dòng lệnh không mang được: danh sách đường dẫn/url
    // phải qua trích dẫn shell, và chế độ thì `apply-pack` không có cờ để nhận.
    clone: 'plan',
    adopt: 'plan',
    codeRepos: 'plan',
    refresh: 'plan',
    upgrade: 'plan',
    syncGlobal: 'plan',
    // Cũng đi kế hoạch, dù biến `PROJECT_NAME` đã có trong hợp đồng biến môi trường: biến
    // đó là đầu vào của `bootstrap.sh` (NTAPP gốc, không được sửa), còn engine con cần giá
    // trị này cho `resolveProjectName`. Hai đường, một giá trị gốc ở tiến trình cha.
    projectName: 'plan',
    // Trả về trước khi tới chỗ chạy script, nên không có gì để chuyển.
    dryRun: 'parent-only',
    // Tiến trình cha kéo flow; con nhận thẳng thư mục qua `_packDir`.
    refreshFlows: 'parent-only',
    // Chỉ để tiến trình cha in tổng kết cuối lệnh.
    unresolved: 'parent-only',
};
//# sourceMappingURL=option-channels.js.map