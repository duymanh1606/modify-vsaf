import type { FlowSource } from './flow-source.js';
/**
 * Chạy file cài đặt của chính flow.
 *
 * Mỗi flow mang theo file cài của nó, để một flow tương lai cần làm việc mà engine
 * chưa có khái niệm thì người viết flow thêm dòng vào file đó và phát hành lại flow —
 * không ai phải chạm vào engine, không ai phải chờ engine ra bản mới.
 *
 * Hôm nay cả bốn flow đều dùng đúng một nội dung dài một dòng: gọi `vsaf apply-pack`.
 * Đó là dự tính, không phải thiếu sót.
 */
export interface FlowScriptContext {
    source: FlowSource;
    flow: string;
    projectPath: string;
    projectName: string;
    engineVersion: string;
    /**
     * File kế hoạch lượt cài, hoặc chuỗi rỗng.
     *
     * LUÔN đặt biến này, kể cả khi rỗng: `runFlowScript` trộn `process.env` vào môi trường
     * của tiến trình con, nên bỏ trống khoá sẽ để một giá trị còn sót trong shell của người
     * dùng chảy vào lượt cài này.
     */
    planPath: string;
}
/**
 * Những cờ engine biết mà lượt cài thật cũng phải biết.
 *
 * Đây là chỗ `vsaf install --skip-deps` từng mất tác dụng: engine chỉ chuyển cho script
 * phần người dùng gõ sau `--`, nên bốn cờ engine tự nhận ở dòng lệnh đứng lại ở tiến
 * trình cha. Đo được: `vsaf install sdlc --skip-deps` vẫn chạy `npm install` thật, tải
 * 255 gói, mất 2 phút; và `--force` thì in `⊘ (exists, use --force to overwrite)` —
 * làm đúng ngược lại điều được yêu cầu, không báo lỗi.
 */
export interface FlowScriptFlags {
    force?: boolean;
    skipDeps?: boolean;
    skipGraphify?: boolean;
    projectRoot?: boolean;
    verbose?: boolean;
}
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
export declare function flowScriptArgs(flags: FlowScriptFlags, passthrough?: string[]): string[];
export declare function flowScriptName(platform: NodeJS.Platform): string;
export declare function flowScriptEnv(context: FlowScriptContext): Record<string, string>;
/**
 * Script chưa hề chạy: thiếu file cài cho hệ điều hành này, thiếu bash, hoặc tiến trình
 * không spawn được.
 *
 * Có lớp riêng vì phía gọi phải phân biệt được. Khi script ĐÃ chạy rồi mới thoát khác 0,
 * nó có thể đã rải file và đã ghi sổ, nên engine vẫn phải đọc sổ và in danh sách vấn đề
 * của tự kiểm. Khi nó chưa chạy thì không có gì để đọc, và ba dòng chẩn đoán "flow không
 * ghi sổ, cần gọi apply-pack" ở đó là ba dòng chỉ sai hướng.
 */
export declare class FlowScriptNotRunError extends Error {
}
export interface FlowScriptFailure {
    status?: number | null;
    /**
     * Tín hiệu đã giết tiến trình, nếu có.
     *
     * Có mặt vì lượt tràn bộ đệm để lại `status: null` cùng `signal: 'SIGTERM'` — đo được
     * kể cả khi script định thoát mã 3 ngay sau khi tràn. `code === 'ENOBUFS'` mới là thứ
     * phép phân loại dựa vào, nhưng giữ trường này để hình dạng ở đây khớp hình dạng
     * `spawnSync` thật sự trả về.
     */
    signal?: NodeJS.Signals;
    code?: string;
    message?: string;
    stdout?: Buffer;
    stderr?: Buffer;
}
/** Phần cuối của những gì script đã in, đủ để thấy nó chết ở đâu. */
export declare function tailOfOutput(failure: FlowScriptFailure): string;
/**
 * Câu báo cho từng kiểu hỏng của script — ba kiểu, ba câu khác nhau.
 *
 * Tách khỏi `runFlowScript` để khoá được bằng test mà không phải dựng lại đúng cảnh
 * hỏng: sinh 64 MB output chỉ để xem câu chữ có đúng không là cái giá không đáng trả.
 */
export declare function describeFlowScriptFailure(flow: string, failure: FlowScriptFailure): string;
export declare function runFlowScript(context: FlowScriptContext & {
    flags: FlowScriptFlags;
    passthrough: string[];
}): void;
//# sourceMappingURL=flow-script.d.ts.map