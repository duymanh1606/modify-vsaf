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
export declare function assertFlowName(flow: string): void;
export declare function flowsCacheDir(): string;
/**
 * Bản flow đã có sẵn trong cache trên máy, hoặc rỗng nếu chưa từng kéo về.
 *
 * Đọc thôi, không chạm git. Có đúng một chỗ cần thế: `--dry-run` hứa không ghi gì, nên
 * nó không được phép kéo repo về — kéo là ghi vào cache, và trên đường mặc định còn là
 * trả giá một lượt clone qua mạng cho một lệnh vốn chỉ để đọc.
 */
export declare function cachedFlowDir(flow: string): string | null;
/** Những flow đã kéo về máy — thư mục trong cache có `pack.yaml`. */
export declare function cachedFlowNames(): string[];
//# sourceMappingURL=flow-home.d.ts.map