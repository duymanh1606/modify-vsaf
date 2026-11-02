"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.execSync = execSync;
const fs_1 = require("fs");
const path_1 = require("path");
const skill_js_1 = require("./skill.js");
const flow_source_js_1 = require("./install/flow-source.js");
const delegate_js_1 = require("./install/delegate.js");
/**
 * Thư mục flow mà lượt cài đang chạy đã trao sẵn, nếu lượt này nằm bên trong một lượt cài.
 *
 * Đo được: một lượt cài in `Đang lấy flow` HAI lần — một của tiến trình cài, một của
 * `vsaf sync` mà `install.sh` gọi. `flowSourceForRun` chỉ dedupe trong cùng một tiến
 * trình, nên tiến trình con kéo lại từ đầu: thêm một vòng qua mạng cho đúng nội dung
 * đang nằm trên đĩa.
 *
 * Ba điều kiện, không phải một: có dấu "đang trong lượt cài", biến tên flow trỏ ĐÚNG
 * flow đang sync, và thư mục đó thật sự là một flow. Thiếu điều kiện giữa thì một biến
 * còn sót từ lượt khác sẽ đồng bộ sai pack — và đích của việc này là $HOME của người dùng.
 */
function flowDirFromInstallRun(pack) {
    if (process.env.VSAF_INSTALL_NESTED !== '1')
        return undefined;
    if (process.env.VSAF_FLOW_NAME !== pack)
        return undefined;
    const dir = process.env.VSAF_FLOW_DIR;
    if (!dir || !(0, fs_1.existsSync)((0, path_1.join)(dir, 'pack.yaml')))
        return undefined;
    return dir;
}
/**
 * Push a pack's skill library and coding rules into the tool directories under the
 * user's home.
 *
 * Its own command rather than a flag on `install`, because the two answer to different
 * things. This one belongs to the machine: run once, shared by every project, and
 * needing no project to exist at all. Installing belongs to a project. Upstream keeps
 * them as two scripts for that reason, and folding them together would mean setting up
 * a project just to refresh a skill.
 *
 * It also covers the case a flag on `install` cannot: a fresh machine with no project
 * yet, where the editor should still show the skills.
 */
function execSync(input, options = {}) {
    const pack = (0, skill_js_1.resolvePackName)(input);
    // Qua repo flows như `install`, không phải chỉ các pack ship trong gói npm: nếu không,
    // `vsaf sync <flow>` từ chối đúng những flow mà `vsaf install <flow>` vừa cài xong.
    const packDir = flowDirFromInstallRun(pack) ?? (0, flow_source_js_1.flowDirFor)(pack);
    const info = (0, skill_js_1.readPackInfoFrom)(packDir);
    if (!info.globalSync) {
        throw new Error(`Pack "${pack}" không khai script đồng bộ ra máy.\n`
            + '  Pack có khai `global:` thì dùng: vsaf install <pack> --sync-global');
    }
    const bash = (0, delegate_js_1.findBash)();
    if (!bash) {
        throw new Error('Cần bash để chạy script đồng bộ của pack, nhưng không tìm thấy.\n'
            + '  Windows: cài Git for Windows (git-scm.com/download/win), hoặc dùng WSL2.');
    }
    // Flag names are the pack's own, so what the user reads in its documentation is what
    // they type here.
    const flags = [];
    if (options.dryRun)
        flags.push('--dry-run');
    if (options.skillsOnly)
        flags.push('--skills-only');
    if (options.rulesOnly)
        flags.push('--rules-only');
    if (options.clean)
        flags.push('--clean');
    flags.push(...(options.passthrough ?? []));
    (0, delegate_js_1.runGlobalSync)(bash, packDir, info, flags, options.verbose === true, pack);
}
//# sourceMappingURL=sync.js.map