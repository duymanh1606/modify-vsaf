"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execApplyPack = execApplyPack;
const fs_1 = require("fs");
const path_1 = require("path");
const install_js_1 = require("./install.js");
const install_plan_js_1 = require("./install/install-plan.js");
const skill_js_1 = require("./skill.js");
function execApplyPack(packDir, projectPath, options = {}) {
    const dir = (0, path_1.resolve)(packDir);
    // Nói ra ngay tại đây thay vì để hỏng sâu bên trong: người đọc lỗi này là người
    // vừa viết `install.sh` cho flow của họ, và thứ họ cần biết là thư mục đưa vào sai.
    if (!(0, fs_1.existsSync)((0, path_1.join)(dir, 'pack.yaml'))) {
        throw new Error(`"${dir}" không phải thư mục flow — không tìm thấy pack.yaml trong đó.`);
    }
    // Tên cài đặt phải đến từ chính `pack.yaml`, không phải tên thư mục đang giữ nó: một
    // cache bị đổi tên, một tarball giải nén ra chỗ khác, một worktree checkout — không
    // cái nào có nghĩa vụ giữ đúng tên thư mục gốc. Dùng `basename(dir)` làm tên cài đặt
    // sẽ làm sổ ghi mang tên thư mục thay vì tên pack, và `vsaf uninstall <tên-thật>` sẽ
    // không tìm thấy gì để gỡ. Chỉ lùi về tên thư mục khi chính `pack.yaml` không khai `name`.
    const name = (0, skill_js_1.readPackInfoFrom)(dir).name ?? (0, path_1.basename)(dir);
    // Kế hoạch trước, cờ dòng lệnh sau — để một cờ người dùng gõ tay là cờ thắng khi hai
    // bên nói khác nhau. Hai tập không giao nhau (kế hoạch mang hình dạng dự án, dòng lệnh
    // mang năm cờ hành vi), nên thứ tự này chỉ là để dành cho tương lai.
    const planPath = process.env[install_plan_js_1.PLAN_ENV];
    const plan = planPath ? (0, install_plan_js_1.readInstallPlan)(planPath, projectPath, name) : null;
    const fromPlan = plan ? (0, install_plan_js_1.planToOptions)(plan) : {};
    return (0, install_js_1.execInstall)(name, projectPath, { ...fromPlan, ...options, _packDir: dir });
}
//# sourceMappingURL=apply-pack.js.map