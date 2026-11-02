"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FlowScriptNotRunError = void 0;
exports.flowScriptArgs = flowScriptArgs;
exports.flowScriptName = flowScriptName;
exports.flowScriptEnv = flowScriptEnv;
exports.tailOfOutput = tailOfOutput;
exports.describeFlowScriptFailure = describeFlowScriptFailure;
exports.runFlowScript = runFlowScript;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const path_1 = require("path");
const delegate_js_1 = require("./delegate.js");
const install_plan_js_1 = require("./install-plan.js");
/**
 * Dòng lệnh đưa cho script của flow: cờ engine trước, cờ người dùng gõ sau `--` sau.
 *
 * Đưa vào **tham số** chứ không vào một biến môi trường kiểu `VSAF_INSTALL_FLAGS`, vì
 * mẫu `install.sh` ở §4.3 spec đã có `"$@"` ở cuối: người viết flow không phải thêm gì,
 * không phải nhớ bỏ dấu ngoặc kép để bash tách từ, và không phải nghĩ về chuỗi rỗng.
 * Mọi cờ ở đây đều là cờ `vsaf apply-pack` nhận, tức là đúng lệnh mà `"$@"` chảy vào.
 *
 * Cờ engine đứng trước cờ người dùng, để một cờ người dùng gõ tay là cờ thắng khi hai
 * bên nói khác nhau.
 */
function flowScriptArgs(flags, passthrough = []) {
    const args = [];
    if (flags.force)
        args.push('--force');
    if (flags.skipDeps)
        args.push('--skip-deps');
    if (flags.skipGraphify)
        args.push('--skip-graphify');
    if (flags.projectRoot)
        args.push('--project-root');
    if (flags.verbose)
        args.push('--verbose');
    return [...args, ...passthrough];
}
function flowScriptName(platform) {
    return platform === 'win32' ? 'install.ps1' : 'install.sh';
}
/** Đường dẫn tới file vào của engine đang chạy. */
function engineEntry() {
    // Không dùng `import.meta.url` được: gói này không khai `"type": "module"` trong
    // package.json nên `module: "Node16"` biên dịch file ra CommonJS, và tsc từ chối
    // `import.meta` trong file build ra CommonJS (TS1470). `__dirname` là cách chỗ khác
    // trong CLI này đã dùng cho đúng việc này (index.ts, server/static.ts) — tự nhiên ở
    // cả bản build lẫn khi vitest chạy thẳng trên mã nguồn.
    //
    // Lấy đuôi file theo `__filename` (không hardcode `.js`) để bản build trỏ đúng
    // dist/index.js.
    //
    // Chạy thẳng từ mã nguồn (vitest, ts-node) thì `src/index.ts` KHÔNG phải thứ node
    // chạy được: mọi import trong đó ghi đuôi `.js` cho những file chỉ tồn tại dạng
    // `.ts`, nên node dừng ở ERR_MODULE_NOT_FOUND. Bản build nằm ngay cạnh mới là file
    // chạy được, nên dùng nó khi có. Không có thì vẫn trả đường dẫn mã nguồn — script
    // của flow sẽ hỏng với một lỗi nói rõ file nào thiếu, tốt hơn là im lặng.
    if ((0, path_1.extname)(__filename) === '.ts') {
        const built = (0, path_1.join)(__dirname, '..', '..', '..', 'dist', 'index.js');
        if ((0, fs_1.existsSync)(built))
            return built;
    }
    return (0, path_1.join)(__dirname, '..', '..', `index${(0, path_1.extname)(__filename)}`);
}
function flowScriptEnv(context) {
    return {
        VSAF_FLOW_DIR: context.source.dir,
        VSAF_PROJECT_DIR: context.projectPath,
        // Hai biến rời chứ không phải một dòng lệnh ghép sẵn: file vào của engine là .js
        // có dòng shebang, POSIX chạy thẳng được còn Windows thì không.
        VSAF_NODE: process.execPath,
        VSAF_CLI: engineEntry(),
        VSAF_FLOW_NAME: context.flow,
        VSAF_FLOW_COMMIT: context.source.commit ?? '',
        VSAF_ENGINE_VERSION: context.engineVersion,
        [install_plan_js_1.PLAN_ENV]: context.planPath,
        // Đặt tường minh, cùng luật với `[PLAN_ENV]` ở trên: engine nói rõ môi trường của
        // tiến trình con là gì, chứ không để nó tự suy ra bằng cách thừa hưởng một biến mà
        // tiến trình cha tình cờ đã đặt. Tiến trình cha đã in khối `Môi trường` (hoặc quyết
        // định không cần in, khi pack không khai `wiring`) trước khi tới đây, nên tiến trình
        // con — script của flow gọi lại `apply-pack` — không cần in lần nữa. Đặt cứng `1`
        // là an toàn: cổng duy nhất gọi tới `checkEnvironment` ở phía con cũng xét đúng
        // `packInfo.wiring`, tức cùng điều kiện tiến trình cha đã dùng để quyết có in hay
        // không — không có nhánh nào mà con cần in mà cờ này lại chặn mất.
        VSAF_ENV_REPORTED: '1',
        // Dấu cho mọi lệnh vsaf chạy bên trong lượt cài này (script của flow gọi ngược lại
        // engine). Nhờ nó, `sync` lồng bỏ hai dòng gợi ý dành cho lượt gõ tay.
        VSAF_INSTALL_NESTED: '1',
        // Không có `VSAF_DRY_RUN` ở đây, và spec §4.1 cũng đã bỏ nó.
        //
        // `--dry-run` in kế hoạch rồi trả về trước khi tới chỗ chạy script, nên biến đó chỉ
        // có thể mang giá trị rỗng — một cái bẫy cho người viết flow: đọc spec thấy hứa `1`
        // rồi code một nhánh không bao giờ chạy. Lời hứa "chạy thử thì không ghi gì" nhờ thế
        // cũng không phụ thuộc vào việc flow có chịu đọc biến đó hay không.
        // Hai biến bootstrap.sh của NTAPP đang đọc. Giữ nguyên tên để pack đó không phải sửa.
        PROJECT_NAME: context.projectName,
        AUTO_CONFIRM: '1',
    };
}
/**
 * Mức trần cho phần stdout gom lại của script.
 *
 * Mặc định của Node là 1 MB, và đó là mức một script cài đặt thật vượt qua dễ dàng:
 * bootstrap của NTAPP dài 2.841 dòng và rải 1.679 file, mỗi file một dòng tường thuật.
 * Tràn trần thì tiến trình bị giết giữa chừng — một lượt cài đang chạy tốt bị bẻ gãy vì
 * nó nói hơi nhiều. 64 MB rộng đến mức không script cài đặt nào chạm tới, mà vẫn là một
 * mức trần thật để một script phát điên in vô hạn không ăn hết bộ nhớ.
 */
const MAX_SCRIPT_OUTPUT = 64 * 1024 * 1024;
/**
 * Script chưa hề chạy: thiếu file cài cho hệ điều hành này, thiếu bash, hoặc tiến trình
 * không spawn được.
 *
 * Có lớp riêng vì phía gọi phải phân biệt được. Khi script ĐÃ chạy rồi mới thoát khác 0,
 * nó có thể đã rải file và đã ghi sổ, nên engine vẫn phải đọc sổ và in danh sách vấn đề
 * của tự kiểm. Khi nó chưa chạy thì không có gì để đọc, và ba dòng chẩn đoán "flow không
 * ghi sổ, cần gọi apply-pack" ở đó là ba dòng chỉ sai hướng.
 */
class FlowScriptNotRunError extends Error {
}
exports.FlowScriptNotRunError = FlowScriptNotRunError;
/**
 * Bao nhiêu output được in lại khi script hỏng.
 *
 * Nâng `maxBuffer` lên 64 MB khiến nhánh này tệ đi 64 lần: đo trên một lượt in 70 MB,
 * phần echo trút **67.149.825 byte** ra terminal, RSS đỉnh 416 MB, rồi mới tới câu lỗi.
 * Trước đó mặc định 1 MiB của Node vô tình chặn giúp — nay không còn ai chặn.
 *
 * Người đọc cần phần CUỐI để biết script chết ở đâu; 67 MB đằng trước không giúp gì. Cắt
 * theo byte trước rồi mới `toString`, để 64 MB đó không bao giờ thành một chuỗi JS.
 */
const ECHO_TAIL_BYTES = 64 * 1024;
const ECHO_TAIL_LINES = 200;
function tailBytes(buffer) {
    if (!buffer || buffer.length === 0)
        return '';
    const cut = buffer.length > ECHO_TAIL_BYTES ? buffer.subarray(buffer.length - ECHO_TAIL_BYTES) : buffer;
    return cut.toString();
}
/** Phần cuối của những gì script đã in, đủ để thấy nó chết ở đâu. */
function tailOfOutput(failure) {
    const joined = `${tailBytes(failure.stdout)}${tailBytes(failure.stderr)}`.trim();
    if (!joined)
        return '';
    const lines = joined.split('\n');
    if (lines.length <= ECHO_TAIL_LINES)
        return joined;
    return [
        `[vsaf] … chỉ in ${ECHO_TAIL_LINES} dòng cuối của script (phần trước đã bị cắt)`,
        ...lines.slice(-ECHO_TAIL_LINES),
    ].join('\n');
}
/**
 * Câu báo cho từng kiểu hỏng của script — ba kiểu, ba câu khác nhau.
 *
 * Tách khỏi `runFlowScript` để khoá được bằng test mà không phải dựng lại đúng cảnh
 * hỏng: sinh 64 MB output chỉ để xem câu chữ có đúng không là cái giá không đáng trả.
 */
function describeFlowScriptFailure(flow, failure) {
    // Tràn bộ đệm: tiến trình bị giết vì in quá nhiều, không phải vì nó thất bại. Nói
    // "thoát mã" hay "chưa ghi sổ" ở đây đều sai, và cả hai đều dẫn người đọc đi sai hướng
    // — thứ họ cần biết là output quá dài, không phải lượt cài hỏng.
    //
    // Kiểm trước hai nhánh dưới, và đây là thứ tự BẮT BUỘC: đo được lần giết này để lại
    // `status: null` cùng `signal: 'SIGTERM'` (kể cả khi script định thoát mã 3 ngay sau
    // khi tràn), nên nó KHÔNG rơi vào nhánh "thoát mã" mà rơi thẳng xuống nhánh cuối —
    // đúng câu "Chưa ghi sổ lượt cài này" vốn đã bị dẹp vì nói sai với người dùng.
    if (failure.code === 'ENOBUFS') {
        return `File cài đặt của flow "${flow}" in ra quá ${Math.round(MAX_SCRIPT_OUTPUT / 1024 / 1024)} MB nên bị dừng giữa chừng.`
            + ' Lượt cài chưa xong và project đang dở — chạy lại với --verbose để xem thẳng,'
            + ' không qua bộ đệm.';
    }
    // `status` là số chỉ khi script thật sự chạy rồi thoát khác 0. Khi tiến trình không
    // spawn được (vd cwd không tồn tại, hoặc không có lệnh để chạy) — Node trả
    // `status: null` kèm `code` như 'ENOENT' — nói "thoát mã 1" ở đây là sai: script chưa
    // hề chạy để mà thoát.
    if (typeof failure.status === 'number') {
        // Không nói "chưa ghi sổ" ở đây: script chạy rồi mới hỏng, nên nó hoàn toàn có thể
        // đã rải file và đã ghi sổ trước khi dừng — `apply-pack` thoát khác 0 khi tự kiểm
        // thấy thủng lỗ là đúng cảnh đó. Nói sai chỗ này khiến người dùng tưởng project còn
        // sạch và không đi dọn.
        return `File cài đặt của flow "${flow}" thoát mã ${failure.status}.`
            + ' Phần nó kịp ghi vẫn nằm trong project — chạy lại lệnh này là an toàn.';
    }
    return `Không chạy được file cài đặt của flow "${flow}" (${failure.code ?? failure.message ?? 'không rõ lý do'}). `
        + 'Chưa ghi sổ lượt cài này.';
}
/**
 * §4.2 spec: đầu ra chuẩn của script được ghi vào `<project>/.vsaf/install.log`.
 *
 * Nối thêm chứ không ghi đè, và chỉ khi `.vsaf/` đã có sẵn. Hai lý do, cả hai đo được:
 * đường nối dây (`runWiring`) cũng ghi vào đúng file này từ trong tiến trình con, nên ghi
 * đè là xoá phần chi tiết hơn của nó; và tự tạo `.vsaf/` sẽ làm engine tưởng dự án có chỗ
 * ghi sổ, đổi mất câu chẩn đoán đúng khi flow không ghi sổ.
 *
 * Ghi log không được thì không phải lý do làm hỏng lượt cài.
 */
function writeInstallLog(projectPath, flow, body) {
    const dir = (0, path_1.join)(projectPath, '.vsaf');
    if (!(0, fs_1.existsSync)(dir))
        return;
    try {
        (0, fs_1.appendFileSync)((0, path_1.join)(dir, 'install.log'), `\n=== ${new Date().toISOString()} — file cài của flow "${flow}" ===\n${body.trimEnd()}\n`, 'utf-8');
    }
    catch { /* nothing to do about it */ }
}
function runFlowScript(context) {
    const name = flowScriptName(process.platform);
    const script = (0, path_1.join)(context.source.dir, name);
    if (!(0, fs_1.existsSync)(script)) {
        throw new FlowScriptNotRunError(`Flow "${context.flow}" chưa có ${name} cho hệ điều hành đang chạy.\n`
            + `  Đã tìm ở: ${script}`);
    }
    const env = { ...process.env, ...flowScriptEnv(context) };
    const scriptArgs = flowScriptArgs(context.flags, context.passthrough);
    const verbose = context.flags.verbose === true;
    let command;
    let args;
    if (process.platform === 'win32') {
        command = 'powershell.exe';
        args = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', script, ...scriptArgs];
    }
    else {
        const bash = (0, delegate_js_1.findBash)();
        if (!bash)
            throw new FlowScriptNotRunError('Máy chưa có bash — không chạy được file cài đặt của flow.');
        command = bash;
        args = [script, ...scriptArgs];
    }
    // `spawnSync`, không phải `execFileSync`, và lý do là `install.log`.
    //
    // `execFileSync` chỉ trả lại stdout; stderr chỉ tới tay khi nó NÉM, và trước đây fd 2
    // còn được nối thẳng ra màn hình nên `failure.stderr` luôn `undefined` — nhánh đọc nó
    // trong `tailOfOutput` là mã chết. Hệ quả đo được: script in `STDOUT-DONG-NAY` và
    // `STDERR-LY-DO-HONG` rồi thoát 7, `install.log` chỉ còn dòng stdout. Lý do hỏng vắng
    // mặt khỏi đúng file người dùng gửi đi nhờ hỗ trợ.
    //
    // `spawnSync` đưa lại cả hai luồng ở CẢ hai kết cục, nên cảnh báo của một lượt chạy
    // THÀNH CÔNG cũng không còn rơi mất. Đánh đổi: ở chế độ không verbose, stderr đến khi
    // script xong thay vì ngay lúc in. Chấp nhận được, vì stdout ở chế độ đó vốn đã bị gom
    // và in một lần khi xong — nay hai luồng đến cùng lúc, tức là đọc được theo đúng thứ
    // tự câu chuyện. Ai cần thấy ngay thì đã có `--verbose`, và ở đó cả hai vẫn chảy
    // thẳng ra terminal.
    const done = (0, child_process_1.spawnSync)(command, args, {
        stdio: verbose ? 'inherit' : ['inherit', 'pipe', 'pipe'],
        cwd: context.projectPath,
        maxBuffer: MAX_SCRIPT_OUTPUT,
        env,
    });
    // `spawnSync` báo lỗi bằng trường `error` chứ không ném. Gộp nó vào cùng một hình dạng
    // mà `describeFlowScriptFailure` đã biết đọc: đo được lượt tràn bộ đệm để lại
    // `status: null`, `signal: 'SIGTERM'` và `error.code === 'ENOBUFS'` — đúng ba trường
    // mà phép phân loại ở đó dựa vào.
    const failed = done.error;
    const failure = {
        status: done.status,
        signal: done.signal ?? undefined,
        code: failed?.code,
        message: failed?.message,
        stdout: done.stdout ?? undefined,
        stderr: done.stderr ?? undefined,
    };
    if (!failed && done.status === 0) {
        // Phải in cả khi chạy được, không chỉ khi hỏng.
        //
        // Script của flow gọi ngược lại `vsaf apply-pack`, và toàn bộ tường thuật lượt cài
        // — "Skills deployed", danh sách skill, kiểm binary, hộp việc phải làm tay — nằm
        // trong tiến trình con đó. Nuốt nó đi thì một lượt cài thành công in ra đúng bằng
        // không: file có, sổ có, màn hình trống. `verbose` vẫn còn nghĩa, chỉ khác chỗ
        // thấy: bật thì chảy ra ngay lúc chạy, tắt thì in gọn một lần khi xong.
        if (verbose) {
            // Output đã chảy thẳng ra terminal, nên không còn gì trong tay để ghi. Nói đúng
            // chuyện đó trong log, chứ không để lại một file trống đọc ra như "script chẳng in gì".
            writeInstallLog(context.projectPath, context.flow, '(chạy với --verbose — output đã in thẳng ra terminal)');
            return;
        }
        const said = done.stdout?.toString().trim() ?? '';
        const warned = done.stderr?.toString().trim() ?? '';
        if (said)
            console.log(said);
        // Cảnh báo ra đúng luồng của nó, để một lượt cài chạy trong pipeline vẫn tách được
        // phần tường thuật khỏi phần cần chú ý.
        if (warned)
            console.error(warned);
        writeInstallLog(context.projectPath, context.flow, [said, warned].filter(Boolean).join('\n'));
        return;
    }
    const output = tailOfOutput(failure);
    if (output)
        console.log(output);
    // Lượt hỏng là lượt cần log nhất, và nay nó có cả stderr — chỗ thường nói vì sao hỏng.
    writeInstallLog(context.projectPath, context.flow, output || '(script không in gì)');
    const said = describeFlowScriptFailure(context.flow, failure);
    // Cùng phép phân loại `describeFlowScriptFailure` dùng: tràn bộ đệm và thoát khác 0 là
    // hai ca script ĐÃ chạy; mọi thứ còn lại là chưa spawn được.
    const ran = failure.code === 'ENOBUFS' || typeof failure.status === 'number';
    throw ran ? new Error(said) : new FlowScriptNotRunError(said);
}
//# sourceMappingURL=flow-script.js.map