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
export declare function satisfiesEngineRange(version: string, range: string): boolean;
export declare function assertEngineSatisfies(packName: string, requires: string | undefined, engineVersion: string): void;
//# sourceMappingURL=engine-range.d.ts.map