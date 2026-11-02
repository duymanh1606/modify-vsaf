"use strict";
/**
 * Chốt chặn giữa flow và engine.
 *
 * Flow phát hành ở repo riêng, không cùng nhịp với engine, nên một flow mới hoàn toàn
 * có thể đòi tính năng engine trên máy chưa có. Chặn ở đây — trước khi ghi file nào —
 * đổi một lỗi lạ giữa chừng cài đặt thành một câu bảo nâng engine.
 *
 * Chỉ nhận đúng một dạng khai báo. Không kéo `semver` về chỉ để đọc một dấu `>=`:
 * repo này không có dependency đó, và mọi dạng khai báo khác chưa ai cần tới.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.satisfiesEngineRange = satisfiesEngineRange;
exports.assertEngineSatisfies = assertEngineSatisfies;
const RANGE = /^>=\s*(\d+)\.(\d+)\.(\d+)$/;
const VERSION = /^(\d+)\.(\d+)\.(\d+)/;
function satisfiesEngineRange(version, range) {
    const wanted = RANGE.exec(range.trim());
    if (!wanted) {
        throw new Error(`requiresEngine: "${range}" không đọc được. Dạng duy nhất được nhận là ">=X.Y.Z", ví dụ ">=6.20.0".`);
    }
    // Phần đuôi phát hành thử được bỏ qua: '6.20.0-rc.1' tính là 6.20.0.
    const have = VERSION.exec(version.trim());
    if (!have)
        return false;
    for (let part = 1; part <= 3; part++) {
        const mine = Number(have[part]);
        const need = Number(wanted[part]);
        if (mine > need)
            return true;
        if (mine < need)
            return false;
    }
    return true;
}
function assertEngineSatisfies(packName, requires, engineVersion) {
    if (!requires)
        return;
    // Chạy thẳng từ mã nguồn thì không có package.json đã phát hành để đọc. Chặn hết
    // mọi flow ở đây sẽ làm hỏng máy người phát triển, nên chỉ nói ra rồi đi tiếp.
    if (engineVersion === 'unknown') {
        console.log(`[vsaf] không đọc được bản engine nên bỏ qua chốt chặn của flow "${packName}" (${requires})`);
        return;
    }
    if (satisfiesEngineRange(engineVersion, requires))
        return;
    throw new Error(`Flow "${packName}" cần vsaf ${requires}, máy đang chạy ${engineVersion}.\n`
        + '  Nâng engine rồi cài lại:  npm i -g @ngocsangairvds/vsaf@latest');
}
//# sourceMappingURL=engine-range.js.map