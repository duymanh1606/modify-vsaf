import { type InstallResult } from './install.js';
/**
 * Cài một pack nằm sẵn trên đĩa.
 *
 * Đây là lối vào cho script của chính flow: `install.sh` của flow gọi lệnh này để
 * engine làm phần chung — rải skill, nhân bản sang thư mục IDE, quản gitignore, ghi
 * sổ để gỡ được — rồi flow tự làm phần riêng của nó.
 *
 * Bên trong không có gì mới: `execInstall` vốn đã nhận được một thư mục qua tuỳ chọn
 * nội bộ `_packDir`, trước nay chỉ test dùng. Mở nó ra thành lệnh thật giữ cho đường
 * cài đặt chỉ có một, nên sổ ghi và cách gỡ không phải viết lại lần thứ hai.
 */
export interface ApplyPackOptions {
    force?: boolean;
    skipDeps?: boolean;
    dryRun?: boolean;
    verbose?: boolean;
    projectRoot?: boolean;
    /**
     * Bỏ qua bước cài graphify.
     *
     * Có cờ `--skip-graphify` ngoài dòng lệnh chứ không chỉ dùng trong test: bước này gọi
     * `pipx install` và ghi vào thư mục công cụ dưới home, tức là ra ngoài dự án. Một lượt
     * chạy tự động hoặc một lần cài lại flow không nên trả giá đó lần nữa.
     */
    _skipGraphify?: boolean;
}
export declare function execApplyPack(packDir: string, projectPath: string, options?: ApplyPackOptions): InstallResult;
//# sourceMappingURL=apply-pack.d.ts.map