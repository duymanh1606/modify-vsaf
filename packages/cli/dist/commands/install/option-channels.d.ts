import type { InstallOptions } from '../install.js';
/**
 * Lựa chọn của `install` đi qua biên engine ↔ file cài của flow bằng đường nào.
 *
 * - `arg`: đi bằng tham số dòng lệnh, qua `flowScriptArgs` → `"$@"` của script → `apply-pack`.
 * - `plan`: đi bằng file kế hoạch (`install-plan.ts`), vì dòng lệnh không mang được.
 * - `parent-only`: không cần qua biên, và lý do phải nêu ở chú thích từng mục.
 */
export type OptionChannel = 'arg' | 'plan' | 'parent-only';
/**
 * Bảng phân loại — và đây là chốt chặn, không phải tài liệu.
 *
 * `Record<keyof InstallOptions, …>` bắt buộc đầy đủ: thêm một lựa chọn vào
 * `InstallOptions` mà quên khai ở đây thì **không biên dịch được**. Đúng kiểu hỏng đã
 * xảy ra — sáu lựa chọn (`clone`, `adopt`, `codeRepos`, `refresh`, `upgrade`,
 * `syncGlobal`) rơi im lặng vì không có chỗ nào buộc phải khai chúng. Đo được: gõ
 * `install NTAPP --new --clone <url>` ra `3/4 Chưa clone repo nào` và thoát 0.
 */
export declare const OPTION_CHANNELS: Record<keyof InstallOptions, OptionChannel>;
//# sourceMappingURL=option-channels.d.ts.map