"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PLAN_VERSION = exports.PLAN_ENV = void 0;
exports.planFields = planFields;
exports.buildInstallPlan = buildInstallPlan;
exports.writeInstallPlan = writeInstallPlan;
exports.readInstallPlan = readInstallPlan;
exports.planToOptions = planToOptions;
exports.logInstallPlan = logInstallPlan;
exports.dropInstallPlan = dropInstallPlan;
const crypto_1 = require("crypto");
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
const flow_source_js_1 = require("./flow-source.js");
const option_channels_js_1 = require("./option-channels.js");
/**
 * Ý định của một lượt cài, chuyển từ engine sang lượt `apply-pack` mà script của flow gọi.
 *
 * Vì sao một FILE chứ không phải thêm cờ dòng lệnh: hợp đồng thôi không còn là danh sách
 * cờ. Thêm lựa chọn mới sau này không phải sửa `install.sh`/`install.ps1` của bất kỳ flow
 * nào — biến môi trường được tiến trình con tự thừa hưởng. Và danh sách url/đường dẫn
 * không phải đi qua trích dẫn shell nữa.
 */
exports.PLAN_ENV = 'VSAF_INSTALL_PLAN';
/** Đổi số này khi hình dạng kế hoạch đổi. Bản khác số thì bên đọc bỏ qua, không đoán. */
exports.PLAN_VERSION = 1;
/** Tên các lựa chọn khai là đi bằng file kế hoạch, đọc thẳng từ bảng phân loại. */
function planFields() {
    return Object.entries(option_channels_js_1.OPTION_CHANNELS)
        .filter(([, channel]) => channel === 'plan')
        .map(([name]) => name);
}
function modeFrom(options) {
    if (options.upgrade === true)
        return 'upgrade';
    if (options.refresh === true)
        return 'refresh';
    return 'install';
}
function buildInstallPlan(input) {
    const { flow, engineVersion, projectPath, options } = input;
    return {
        planVersion: exports.PLAN_VERSION,
        flow,
        engineVersion,
        projectPath: (0, path_1.resolve)(projectPath),
        projectName: options.projectName,
        mode: modeFrom(options),
        clone: options.clone,
        adopt: options.adopt,
        codeRepos: options.codeRepos,
        syncGlobal: options.syncGlobal,
    };
}
/**
 * Ghi ra thư mục tạm, tên có phần ngẫu nhiên.
 *
 * Không ghi vào `<project>/.vsaf/`: ở lượt `--new` của một flow mang theo khung dự án,
 * `.vsaf/` chưa tồn tại tại thời điểm này — `init` chạy SAU khi nối dây.
 */
function writeInstallPlan(plan) {
    const path = (0, path_1.join)((0, os_1.tmpdir)(), `vsaf-plan-${(0, crypto_1.randomBytes)(4).toString('hex')}.json`);
    (0, fs_1.writeFileSync)(path, `${JSON.stringify(plan, null, 2)}\n`, { encoding: 'utf-8', mode: 0o600 });
    return path;
}
/**
 * Đọc kế hoạch cho ĐÚNG dự án đang cài, hoặc không có gì.
 *
 * Trả `null` chứ không ném ở mọi ca đáng ngờ: lượt cài đã đang chạy, và một kế hoạch
 * đọc không ra không phải lý do làm hỏng nó — đi tiếp không có kế hoạch chỉ mất phần
 * engine bù thêm, còn ném là hỏng cả lượt.
 */
function readInstallPlan(path, projectPath, flow) {
    if (!(0, fs_1.existsSync)(path))
        return null;
    let plan;
    try {
        plan = JSON.parse((0, fs_1.readFileSync)(path, 'utf-8'));
    }
    catch {
        console.log(`[vsaf] ⚠ Không đọc được kế hoạch lượt cài (${path}) — bỏ qua, cài theo cờ dòng lệnh.`);
        return null;
    }
    if (plan.planVersion !== exports.PLAN_VERSION) {
        console.log(`[vsaf] ⚠ Kế hoạch lượt cài là bản ${plan.planVersion}, engine này đọc bản ${exports.PLAN_VERSION} — bỏ qua.`);
        return null;
    }
    // Biến môi trường còn sót trong shell là chuyện có thật: một lượt cài hỏng giữa chừng
    // rồi người dùng gõ tay `vsaf apply-pack` trong cùng shell. Áp kế hoạch của dự án khác
    // lên đây là ghi sai chỗ mà không ai được cảnh báo.
    if ((0, path_1.resolve)(plan.projectPath) !== (0, path_1.resolve)(projectPath)) {
        console.log('[vsaf] ⚠ Kế hoạch lượt cài nói về một dự án khác — bỏ qua, cài theo cờ dòng lệnh.');
        console.log(`[vsaf]   kế hoạch: ${plan.projectPath}`);
        console.log(`[vsaf]   đang cài: ${(0, path_1.resolve)(projectPath)}`);
        return null;
    }
    // Cùng một lý do với kiểm tra dự án ở trên, nhưng cho FLOW: biến môi trường còn sót lại
    // trong shell, người dùng gõ tay `vsaf apply-pack <flow-khác>` trong khi
    // `VSAF_INSTALL_PLAN` vẫn trỏ tới kế hoạch của flow cũ — đường dẫn dự án có thể trùng
    // (cùng thư mục, cài nối tiếp hai flow khác nhau) nên kiểm tra dự án ở trên không chặn
    // được ca này. Không kiểm `engineVersion`: `planVersion` đã khoá hình dạng kế hoạch.
    if (plan.flow !== flow) {
        console.log('[vsaf] ⚠ Kế hoạch lượt cài nói về một flow khác — bỏ qua, cài theo cờ dòng lệnh.');
        console.log(`[vsaf]   kế hoạch: ${plan.flow}`);
        console.log(`[vsaf]   đang cài: ${flow}`);
        return null;
    }
    return plan;
}
/** Kế hoạch đổi về đúng những tuỳ chọn cài mà nó mang. */
function planToOptions(plan) {
    return {
        clone: plan.clone,
        adopt: plan.adopt,
        codeRepos: plan.codeRepos,
        projectName: plan.projectName,
        syncGlobal: plan.syncGlobal,
        refresh: plan.mode === 'refresh',
        upgrade: plan.mode === 'upgrade',
    };
}
/**
 * Nối kế hoạch vào sổ log của dự án — chỉ khi dự án đã có chỗ ghi.
 *
 * File tạm bị xoá ngay sau lượt cài, nên đây là chỗ duy nhất còn lại để về sau truy được
 * lượt cài ĐÃ ĐƯỢC YÊU CẦU làm gì, chứ không chỉ nó đã in ra gì.
 *
 * Không tự tạo `.vsaf/`: `runFlowScript` phân biệt "dự án không có chỗ ghi sổ" với "có chỗ
 * mà flow không ghi", và tự dựng thư mục ở đây sẽ đổi mất câu chẩn đoán đúng. Ghi log
 * không được cũng không phải lý do làm hỏng lượt cài.
 *
 * `clone`/`adopt` MANG BÍ MẬT: `flow-source.ts` đọc rõ `--clone https://user:token@host/x.git`
 * là input hợp lệ (ưu tiên credential nhúng trong URL hơn cả `BITBUCKET_TOKEN`), và chính
 * `flow-source.ts` đã che nó bằng `maskUrl` ở năm chỗ vì lý do đó. `.vsaf/install.log` nằm
 * TRONG dự án — `pack.yaml` của NTAPP không liệt `.vsaf/` vào danh sách gitignore của nó
 * (cả `spec` lẫn `code`) — nên ghi nguyên văn ở đây là ghi thẳng bí mật vào một file mà
 * `bootstrap-repo.ts` còn phải tự tay `git reset` ra khỏi commit đầu tiên. Chỉ che bản ghi
 * LOG: `plan` gốc đưa cho tiến trình con (`writeInstallPlan`) phải giữ nguyên URL thật, nếu
 * không `git clone` ở phía flow sẽ hỏng vì mất phần đăng nhập.
 */
function logInstallPlan(projectPath, plan) {
    const dir = (0, path_1.join)(projectPath, '.vsaf');
    if (!(0, fs_1.existsSync)(dir))
        return;
    try {
        const daChe = {
            ...plan,
            clone: plan.clone?.map(flow_source_js_1.maskUrl),
            adopt: plan.adopt?.map(flow_source_js_1.maskUrl),
        };
        (0, fs_1.appendFileSync)((0, path_1.join)(dir, 'install.log'), `\n=== ${new Date().toISOString()} — kế hoạch lượt cài flow "${plan.flow}" ===\n`
            + `${JSON.stringify(daChe, null, 2)}\n`, 'utf-8');
    }
    catch { /* nothing to do about it */ }
}
/** Xoá kế hoạch. Không xoá được cũng không phải lý do làm hỏng lượt cài. */
function dropInstallPlan(path) {
    try {
        (0, fs_1.rmSync)(path, { force: true });
    }
    catch { /* nothing to do about it */ }
}
//# sourceMappingURL=install-plan.js.map