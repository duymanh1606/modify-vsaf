"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.assertFlowName = assertFlowName;
exports.flowsCacheDir = flowsCacheDir;
exports.cachedFlowDir = cachedFlowDir;
exports.cachedFlowNames = cachedFlowNames;
const fs_1 = require("fs");
const os_1 = require("os");
const path_1 = require("path");
/**
 * Nơi cache flow nằm trên máy, và những flow đã có trong đó.
 *
 * Tách khỏi `flow-source.ts` vì `skill.ts` cũng cần đọc: sau khi flow ra khỏi gói npm,
 * "những pack máy này biết" không còn là "những thư mục gói npm mang theo" nữa. Đặt
 * chung vào `flow-source.ts` thì `skill.ts` phải import nó, mà nó lại import `skill.ts`
 * — một vòng import, và cách vòng đó hỏng phụ thuộc vào thứ tự nạp module.
 *
 * Chỉ đọc đĩa. Không lệnh git nào ở đây, nên gọi từ đâu cũng an toàn.
 */
/** Tên flow phải là một thư mục ở gốc repo, không phải một đường dẫn. */
function assertFlowName(flow) {
    // Ba hình dạng, một lý do: tên flow đi thẳng vào `join(cache, flow)` và vào
    // `sparse-checkout add`, nên một tên mang dấu phân cách hay `..` là một đường dẫn
    // trỏ ra ngoài cache — và `--refresh-flows` thì `rmSync` đúng chỗ nó trỏ tới.
    if (flow.trim() === '' || flow.includes('/') || flow.includes('\\') || flow.includes('..')) {
        throw new Error(`"${flow}" không phải tên flow hợp lệ.\n`
            + '  Tên flow là tên một thư mục ở gốc repo flows — không chứa "/", "\\" hay "..".');
    }
}
function flowsCacheDir() {
    // `||` chứ không phải `??`: `VSAF_HOME=""` vẫn phải rơi về mặc định. Nếu không, `cache`
    // thành đường dẫn tương đối `flows` dưới thư mục hiện hành, và `ensureCache` sẽ `rmSync`
    // đúng thư mục đó — xoá nhầm một thư mục `./flows` chẳng liên quan gì của người dùng.
    const home = process.env.VSAF_HOME || (0, path_1.join)((0, os_1.homedir)(), '.vsaf');
    return (0, path_1.join)(home, 'flows');
}
/**
 * Bản flow đã có sẵn trong cache trên máy, hoặc rỗng nếu chưa từng kéo về.
 *
 * Đọc thôi, không chạm git. Có đúng một chỗ cần thế: `--dry-run` hứa không ghi gì, nên
 * nó không được phép kéo repo về — kéo là ghi vào cache, và trên đường mặc định còn là
 * trả giá một lượt clone qua mạng cho một lệnh vốn chỉ để đọc.
 */
function cachedFlowDir(flow) {
    assertFlowName(flow);
    const dir = (0, path_1.join)(flowsCacheDir(), flow);
    return (0, fs_1.existsSync)((0, path_1.join)(dir, 'pack.yaml')) ? dir : null;
}
/** Những flow đã kéo về máy — thư mục trong cache có `pack.yaml`. */
function cachedFlowNames() {
    const cache = flowsCacheDir();
    try {
        return (0, fs_1.readdirSync)(cache, { withFileTypes: true })
            .filter(entry => entry.isDirectory() && (0, fs_1.existsSync)((0, path_1.join)(cache, entry.name, 'pack.yaml')))
            .map(entry => entry.name)
            .sort();
    }
    catch {
        // Chưa có cache. Không phải sự cố, chỉ là chưa cài flow nào.
        return [];
    }
}
//# sourceMappingURL=flow-home.js.map