import type { InstallOptions } from '../install.js';
/**
 * Ý định của một lượt cài, chuyển từ engine sang lượt `apply-pack` mà script của flow gọi.
 *
 * Vì sao một FILE chứ không phải thêm cờ dòng lệnh: hợp đồng thôi không còn là danh sách
 * cờ. Thêm lựa chọn mới sau này không phải sửa `install.sh`/`install.ps1` của bất kỳ flow
 * nào — biến môi trường được tiến trình con tự thừa hưởng. Và danh sách url/đường dẫn
 * không phải đi qua trích dẫn shell nữa.
 */
export declare const PLAN_ENV = "VSAF_INSTALL_PLAN";
/** Đổi số này khi hình dạng kế hoạch đổi. Bản khác số thì bên đọc bỏ qua, không đoán. */
export declare const PLAN_VERSION = 1;
/**
 * Ba chế độ, ánh đúng biến `rewiring` mà `installDelegated` vốn đã dùng.
 *
 * Gọi là `install` chứ không phải `new`: `vsaf install NTAPP` gõ trơn (không `--new`)
 * cũng đi nhánh này, và tên `new` sẽ đọc ra như "có tạo thư mục mới" — không đúng.
 */
export type InstallMode = 'install' | 'refresh' | 'upgrade';
export interface InstallPlan {
    planVersion: number;
    flow: string;
    engineVersion: string;
    /** Dự án mà kế hoạch này nói về. Bên đọc so với dự án nó đang cài, lệch thì bỏ qua. */
    projectPath: string;
    projectName?: string;
    mode: InstallMode;
    clone?: string[];
    adopt?: string[];
    codeRepos?: string[];
    syncGlobal?: boolean;
}
/** Tên các lựa chọn khai là đi bằng file kế hoạch, đọc thẳng từ bảng phân loại. */
export declare function planFields(): string[];
export declare function buildInstallPlan(input: {
    flow: string;
    engineVersion: string;
    projectPath: string;
    options: InstallOptions;
}): InstallPlan;
/**
 * Ghi ra thư mục tạm, tên có phần ngẫu nhiên.
 *
 * Không ghi vào `<project>/.vsaf/`: ở lượt `--new` của một flow mang theo khung dự án,
 * `.vsaf/` chưa tồn tại tại thời điểm này — `init` chạy SAU khi nối dây.
 */
export declare function writeInstallPlan(plan: InstallPlan): string;
/**
 * Đọc kế hoạch cho ĐÚNG dự án đang cài, hoặc không có gì.
 *
 * Trả `null` chứ không ném ở mọi ca đáng ngờ: lượt cài đã đang chạy, và một kế hoạch
 * đọc không ra không phải lý do làm hỏng nó — đi tiếp không có kế hoạch chỉ mất phần
 * engine bù thêm, còn ném là hỏng cả lượt.
 */
export declare function readInstallPlan(path: string, projectPath: string, flow: string): InstallPlan | null;
/** Kế hoạch đổi về đúng những tuỳ chọn cài mà nó mang. */
export declare function planToOptions(plan: InstallPlan): Partial<InstallOptions>;
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
export declare function logInstallPlan(projectPath: string, plan: InstallPlan): void;
/** Xoá kế hoạch. Không xoá được cũng không phải lý do làm hỏng lượt cài. */
export declare function dropInstallPlan(path: string): void;
//# sourceMappingURL=install-plan.d.ts.map