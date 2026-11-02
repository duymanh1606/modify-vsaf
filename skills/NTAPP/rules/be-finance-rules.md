# Rule khi code Backend (hệ thống tài chính số)

Các rule dưới đây áp dụng khi sửa/tạo file Backend (Java/Spring Boot, hoặc service code nói chung). Với file Frontend hoặc file không thuộc BE thì bỏ qua toàn bộ mục này. Cách áp dụng giống rule Sonar: review phần code BE đã đụng tới TRƯỚC khi báo hoàn thành, phát hiện vi phạm thì sửa luôn và nêu trong báo cáo cuối.

# Kiểm tra Sonar sau khi sửa code

Mỗi khi sửa code xong (bất kỳ task nào có chỉnh sửa file code), TRƯỚC khi báo hoàn thành phải tự review các file vừa sửa/tạo theo các rule Sonar dưới đây. Nếu phát hiện vi phạm → sửa luôn rồi mới kết thúc. Chỉ review phần code đã đụng tới trong task, không quét toàn repo.

Báo cáo ngắn gọn ở cuối: liệt kê file đã review + rule nào vi phạm (nếu có) + đã sửa thế nào, hoặc "không vi phạm".

## Các rule chính cần kiểm tra

**`java:S3776` — Cognitive Complexity of methods should not be too high**
- Ngưỡng mặc định: cognitive complexity của 1 method **> 15** là vi phạm.
- Tăng điểm khi: mỗi cấu trúc rẽ nhánh/lặp (`if`, `else if`, `else`, `for`, `while`, `do`, `catch`, ternary `?:`, `switch`); mỗi mức lồng nhau (nesting) cộng thêm penalty; chuỗi toán tử logic hỗn hợp (`&&`, `||`) xen kẽ; `break`/`continue` có label; đệ quy.
- Cách sửa: tách method lớn thành các method con (extract method), early-return / guard clause để giảm nesting, gộp điều kiện trùng, dùng polymorphism/map thay cho switch dài, tách vòng lặp lồng nhau ra hàm riêng.

**`java:S1192` — String literals should not be duplicated**
- Ngưỡng mặc định: cùng một string literal (≥ 5 ký tự) lặp lại **≥ 3 lần** trong cùng 1 file là vi phạm.
- Bỏ qua các literal quá ngắn (< 5 ký tự) và annotation values.
- Cách sửa: tách thành `private static final String` constant đặt tên có nghĩa, rồi thay thế tất cả chỗ dùng.

**`java:S125` — Sections of code should not be commented out**
- BẮT BUỘC kiểm tra mọi file vừa sửa/tạo. Mọi dòng/khối **code** bị comment-out (không phải comment giải thích) đều là vi phạm — kể cả khi chỉ có **1 dòng**, không có ngưỡng tối thiểu.
- 🔴 **TIÊU CHÍ SẮC — chạy TRƯỚC khi báo hoàn thành, không có ngoại lệ.** Signature bắt được chắc chắn (đã kiểm chứng thực nghiệm, xem mục "Bằng chứng đo được" bên dưới) là: **line comment `//` KẾT THÚC bằng dấu `;`**. Quét cơ học bằng đúng 1 lệnh trên các file `.java` vừa sửa:
  ```bash
  grep -nE '^\s*//.*;\s*$' <file1.java> <file2.java> ...
  ```
  Có bất kỳ dòng nào trả về → **PHẢI sửa** (tách câu bằng dấu chấm) rồi mới báo hoàn thành. Không có dòng nào → qua cửa này.
  ⚠️ Bước grep này là BẮT BUỘC, không được thay bằng "tôi đã đọc lại và thấy comment là văn xuôi nên an toàn" — chính suy nghĩ đó đã làm lọt 3 lần.
- 📊 **Bằng chứng đo được (repo `merchant-composite-service`, quét toàn `src/`):**

  | Dạng comment chứa `;` | Số dòng | Sonar flag? |
  |---|---|---|
  | Javadoc `/** ... ; */` | 26 | ❌ không |
  | `//` có `;` **giữa dòng** (vd `at 422; HUB-04 reuses...`) | ~9 | ❌ không |
  | `//` có `;` **cuối dòng** | 2 | ✅ **cả 2 đều bị flag** |

  → Đừng phát biểu rule kiểu "`;` ở bất kỳ đâu là nguy hiểm": ~94% trường hợp không sao, nên rule rộng bị đọc như cảnh báo nền rồi bỏ qua. Rủi ro thật tập trung ở `//` kết thúc bằng `;`.
- ⚠️ **`;` là dấu câu hợp lệ trong tiếng Việt — và vị trí nó rơi vào cuối dòng là NGẪU NHIÊN.** Cùng một câu, wrap lệch 3 chữ là thoát/dính. Vì vậy KHÔNG dùng `;` để ngăn hai vế câu trong comment — dùng dấu chấm hoặc dấu phẩy. Đây là nguồn tái phạm duy nhất qua cả 3 lần dính.
- ✅ **Lối thoát hợp pháp:** ghi chú dài, buộc phải nhắc tên kỹ thuật/contract → đặt trong **Javadoc `/** ... */`** (S125 thực tế bỏ qua Javadoc — 26/26 dòng Javadoc có `;` trong repo đều sạch), KHÔNG viết thành khối `//` nhiều dòng.
- Dấu hiệu nhận biết "code bị comment" (khác với comment giải thích bằng ngôn ngữ tự nhiên): bên trong comment có cú pháp code — dấu `;` **cuối dòng** (rủi ro cao nhất), `{` `}` `()`, từ khóa (`if`, `for`, `return`, `import`, khai báo biến/method), gọi hàm, annotation `@...`, identifier dạng `snake_case`/`camelCase` (tên cột/field/biến viết raw, vd `current_status`, `last_synced_at`), **từ ghép nối bằng gạch ngang** (vd `sub-link` — parser đọc ra phép trừ `sub - link`), toán tử (`+`, `=`, `->`), hoặc một statement/expression hoàn chỉnh.
- ⚠️ **Cạm bẫy FALSE-SAFE — đừng dựa vào "đây là câu giải thích nên an toàn":** engine Sonar chấm S125 theo **cú pháp**, KHÔNG theo ý nghĩa. Một comment **đọc ra vẫn là giải thích** nhưng có chèn token code thì VẪN bị flag. Token nguy hiểm cần tránh trong comment:
  - lời gọi method `tênHàm(...)`, dấu `{...}`/`(...)` bọc token code, path template kiểu `{id}` / `{reason}`, hoặc HTTP verb + path (`PUT /x/{id}`);
  - **tên cột/field/biến viết raw dạng `snake_case`/`camelCase`** (vd `current_status`, `last_synced_at`, `updated_at`) — Sonar đọc ra là identifier;
  - **dấu `;` ở CUỐI dòng comment** và **mệnh đề bọc trong `(...)`** chứa identifier/từ khóa (vd `(Schema has no updated_at column;`) — cặp `(...)` + `;` rất dễ bị chấm là statement.
  - Ví dụ thực tế đã dính (3 lần): (1) comment mô tả contract API chứa `dto.getReason()` và `{reason}`; (2) comment mô tả luồng DB chứa `current_status + last_synced_at` và `(Schema has no updated_at column;`; (3) **hai comment văn xuôi tiếng Việt 100% không có token code nào**, chỉ vì dùng `;` ngăn câu và nó rơi đúng cuối dòng → vẫn bị S125 bắt. Cả ba đều là giải thích, không phải code chết.
  - → Khi mô tả API/contract/luồng/DB trong comment, diễn đạt **bằng lời thuần** (vd "cập nhật trạng thái hiện tại và mốc thời gian đồng bộ"), KHÔNG chèn cú pháp code, KHÔNG nhắc tên cột/field/biến ở dạng raw token; nếu buộc phải nhắc tên kỹ thuật thì để ở Javadoc/tài liệu, không nhúng dạng code vào comment dòng.
- ✅ **Quét thủ công bổ sung cho MỌI comment giải thích nhiều dòng** (chạy SAU lệnh grep ở trên, và quét cả comment có sẵn nằm trong vùng code đã đụng tới): đọc từng dòng comment và tự hỏi "dòng này có chứa `()`/`{}`, `=`/`+`/`->`, `@...`, identifier `snake_case`/`camelCase`, từ ghép gạch ngang, hay path `{...}` không?". Nếu CÓ ≥ 1 token → viết lại dòng đó bằng văn xuôi thuần trước khi báo hoàn thành. Quy tắc an toàn: khối `//` nhiều dòng = **văn xuôi thuần tiếng Việt/tiếng Anh, zero token code, không `;`**.
- Áp dụng cho mọi kiểu comment: `//`, `/* ... */`, `/** ... */`, và comment nhiều dòng bao quanh block code. Lưu ý phân biệt: **code thật bị comment-out** thì kiểu comment nào cũng phải xóa; còn **văn xuôi giải thích bị chấm nhầm** thì rủi ro dồn vào khối `//` — nên đó là lý do đưa ghi chú dài sang Javadoc.
- Cách sửa: **xóa hẳn** khối code đã comment (git/lịch sử đã lưu, không cần giữ). KHÔNG để lại "code chết". Nếu thật sự cần giữ ghi chú thì chuyển thành câu giải thích bằng tiếng Việt, không để nguyên dạng code.
- Khi review cuối task, quét lại từng file đã đụng tới: nếu còn bất kỳ khối code comment-out nào → xóa rồi mới báo hoàn thành.

**`java:S1128` — Unnecessary imports should be removed**
- BẮT BUỘC kiểm tra mọi file `.java` vừa sửa/tạo. Mỗi `import` (kể cả `import static`) khai báo nhưng KHÔNG được dùng ở bất kỳ đâu trong file đều là vi phạm — không có ngưỡng tối thiểu, 1 import thừa cũng bị flag.
- Nguồn phát sinh phổ biến: bỏ bớt code sau refactor nhưng quên xóa import; copy import từ file khác; import static của Mockito/JUnit/AssertJ (`org.mockito.Mockito.when`, `org.mockito.ArgumentMatchers.any`, `assertThrows`, ...) trong file test nhưng method tương ứng không còn được gọi.
- Cũng tính vi phạm: import trùng lặp, import từ chính package hiện tại (redundant), và import `java.lang.*` (luôn thừa).
- Cách kiểm: với mỗi dòng import, tìm định danh cuối (tên class / tên method static) trong phần thân file; nếu không xuất hiện lần nào (ngoài chính dòng import) → xóa dòng import đó. Ưu tiên dùng "Organize Imports" của IDE, nhưng vẫn phải rà lại import static vì IDE đôi khi giữ lại nhầm.
- Cách sửa: **xóa hẳn** dòng import thừa. KHÔNG thay bằng import wildcard `*` để né lỗi.

## Mở rộng Sonar

Đây là các rule trọng tâm; nếu thấy các code smell Sonar phổ biến khác trong file vừa sửa (vd `java:S1186` empty method, `java:S106` dùng `System.out`, unused variable, `java:S2589` điều kiện luôn đúng/sai) thì cũng nên sửa kèm và nêu trong báo cáo. Khi không chắc một literal/method có vượt ngưỡng hay không, ưu tiên đếm cụ thể trước khi kết luận.

# SENIOR BACKEND RULES — DIGITAL FINANCE SYSTEM (OPTIMIZED FOR LLM)

> Stack: Java 17+ · Spring Boot 3.x · JPA/Hibernate · Keycloak · PostgreSQL/Oracle.
> Nguyên tắc xuyên suốt: TIỀN KHÔNG ĐƯỢC SAI — đúng trước, nhanh sau.

## 1. XỬ LÝ TIỀN TỆ & SỐ HỌC
* **CẤM `double`/`float` cho tiền**: bắt buộc `BigDecimal` (Java) / `DECIMAL`,`NUMERIC` (DB). Áp cho cả tỷ giá, lãi suất, phí, phần trăm.
* **So sánh BigDecimal**: dùng `compareTo()`, CẤM `equals()` (`0.10` vs `0.1` không equals nhưng compareTo = 0).
* **Rounding tường minh**: mọi phép chia/nhân tỷ lệ phải khai báo `RoundingMode` + scale rõ ràng (thường `HALF_UP`/`HALF_EVEN` theo quy định nghiệp vụ). CẤM để default.
* **Tiền luôn đi kèm currency**: model dạng `(amount, currencyCode)`; CẤM cộng trừ hai amount khác currency mà không qua conversion tường minh.
* **CẤM tự tính lại số dư từ phía client gửi lên**: amount/balance chỉ tính từ dữ liệu server-side.

## 2. IDEMPOTENCY & CHỐNG DOUBLE-PROCESSING
* **Mọi API ghi tạo giao dịch tiền phải idempotent**: nhận `Idempotency-Key` (hoặc client request id) + unique constraint ở DB; request trùng key trả về kết quả lần đầu, KHÔNG xử lý lại.
* **Chống double-submit ở tầng DB, không chỉ ở code**: unique constraint / insert-first pattern; CẤM chỉ dựa vào check-then-act trong code (race condition).
* **Consumer message/event phải idempotent**: xử lý được message trùng (at-least-once delivery); dedupe bằng message id + bảng processed.
* **Retry chỉ cho operation idempotent**: CẤM auto-retry cho call ghi không idempotent; timeout với đối tác thanh toán → trạng thái `PENDING/UNKNOWN` + job đối soát truy vấn lại, KHÔNG tự đoán thành công/thất bại.

## 3. TRANSACTION & CONSISTENCY
* **Ranh giới `@Transactional` gọn nhất có thể**: CẤM gọi API ngoài / gửi message / I/O chậm bên trong transaction DB.
* **Hiểu proxy Spring**: `@Transactional` không có tác dụng khi self-invocation (gọi method cùng class); tách sang bean khác nếu cần.
* **Update số dư phải chống race**: dùng optimistic lock (`@Version`) hoặc pessimistic lock (`SELECT ... FOR UPDATE`) / atomic update (`UPDATE ... SET balance = balance - :x WHERE balance >= :x`). CẤM read-modify-write không lock.
* **Ghi sổ dạng ledger append-only**: giao dịch tiền ghi bút toán (entry) mới, CẤM update/delete bản ghi giao dịch đã ghi; sửa sai → bút toán đảo (reversal).
* **Cross-service consistency**: dùng outbox pattern / saga cho luồng chạm nhiều service; CẤM two-phase tự chế bằng try-catch gọi API rollback tay.
* **Trạng thái giao dịch là state machine tường minh**: khai báo transition hợp lệ (vd `INIT → PENDING → SUCCESS/FAILED → REVERSED`); CẤM set status tự do bằng setter.

## 4. VALIDATION & INPUT
* **Validate tại biên**: Bean Validation (`@Valid`, `@NotNull`, `@Positive`, `@Digits`) trên DTO request; business rule validate ở service.
* **Amount phải check**: > 0, đúng scale theo currency, trong hạn mức (min/max, hạn mức ngày/user).
* **CẤM bind entity JPA trực tiếp từ request** (mass assignment): luôn qua DTO + mapping tường minh.
* **Whitelist, không blacklist**: enum/status/type từ client → parse về enum Java, CẤM nhận string tự do rồi so sánh chuỗi.

## 5. BẢO MẬT & PHÂN QUYỀN
* **AuthZ ở server cho từng resource**: check user có quyền trên CHÍNH resource đó (ownership check — chủ sở hữu account phải trùng principal đang đăng nhập), không chỉ check role. Chống IDOR: CẤM tin resource id client gửi lên.
* **Method-level security**: `@PreAuthorize` cho operation nhạy cảm; mapping role Keycloak tập trung một chỗ, CẤM rải string role khắp code.
* **CẤM secret trong code/config commit**: credential, API key qua env/vault. Log/response CẤM chứa secret.
* **SQL Injection**: chỉ dùng parameterized query / JPA; CẤM nối chuỗi SQL từ input — kể cả trong native query, `ORDER BY` động phải whitelist.
* **Dữ liệu nhạy cảm at-rest**: PAN/số thẻ/CCCD mã hóa hoặc tokenize theo chuẩn (PCI-DSS nếu chạm thẻ); CẤM lưu CVV dưới mọi hình thức.

## 6. AUDIT & LOGGING
* **Audit trail bất biến cho mọi thao tác tiền + thao tác admin**: ai (userId) — làm gì (action) — trên gì (resource) — khi nào (UTC) — từ đâu (IP/channel) — giá trị trước/sau. Ghi append-only.
* **CẤM log PII/dữ liệu nhạy cảm dạng thô**: số thẻ, mật khẩu, token, OTP, số dư kèm định danh → mask (`****1234`) hoặc bỏ. Review mọi lệnh log có object dump.
* **Correlation id xuyên suốt**: mọi request có trace/correlation id, propagate qua service call + message; log qua MDC.
* **Log có cấu trúc**: key-value/JSON, đủ context để trace 1 giao dịch end-to-end bằng transaction id.
* **CẤM `System.out.println`** (Sonar S106): dùng logger.

## 7. THỜI GIAN & DỮ LIỆU
* **Lưu UTC, hiển thị theo timezone user**: DB dùng `timestamptz`/UTC; code dùng `Instant`/`OffsetDateTime`; CẤM `java.util.Date`, `Calendar` cho code mới.
* **Cut-off time nghiệp vụ khai báo tường minh** (ngày giao dịch khác ngày calendar): logic ngày làm việc/cut-off tách thành service riêng, có test.
* **Soft-delete cho dữ liệu nghiệp vụ**: CẤM hard delete bản ghi tài chính; dùng flag + audit.
* **DB migration qua Flyway/Liquibase**: CẤM sửa schema tay; migration script immutable sau khi merge — sửa bằng script mới.

## 8. API DESIGN & ERROR HANDLING
* **Error response chuẩn hóa 1 format**: error code nghiệp vụ (catalog tập trung) + message + traceId; CẤM trả stack trace / message exception thô ra client.
* **HTTP status đúng nghĩa**: 400 validate, 401/403 auth, 404 not found, 409 conflict/duplicate, 422 business rule, 500 lỗi hệ thống. CẤM trả 200 kèm `success: false` cho lỗi.
* **Exception handling tập trung**: `@RestControllerAdvice`; CẤM try-catch nuốt exception (catch rồi chỉ log, không rethrow / không chuyển trạng thái).
* **Response tiền dạng string hoặc number đúng scale**: thống nhất toàn hệ thống, tránh JS làm tròn sai với số lớn vượt độ chính xác 53 bit.
* **Versioning + backward compatible**: thêm field mới phải optional; breaking change → version mới, CẤM sửa contract đang chạy.

## 9. TÍCH HỢP ĐỐI TÁC (PAYMENT GATEWAY, CORE BANKING)
* **Timeout + circuit breaker bắt buộc** cho mọi outbound call (Resilience4j): CẤM call không timeout.
* **Lưu raw request/response với đối tác** (đã mask dữ liệu nhạy cảm) phục vụ đối soát/tranh chấp.
* **Verify chữ ký/checksum callback**: mọi webhook/callback từ đối tác phải verify signature + chống replay (timestamp + nonce); CẤM tin callback chỉ vì đúng format.
* **Đối soát (reconciliation) là bắt buộc**: mọi luồng tiền qua đối tác phải có job đối soát định kỳ so khớp 2 bên; thiết kế luồng phải trả lời được câu "lệch thì phát hiện thế nào?".

## 10. CONCURRENCY & JOBS
* **Scheduled job chạy multi-instance phải có distributed lock** (ShedLock/DB lock): CẤM `@Scheduled` trần khi deploy nhiều node.
* **Job xử lý batch phải resumable + idempotent**: chết giữa chừng chạy lại không double-process (checkpoint/status per record).
* **CẤM shared mutable state trong bean singleton**: service Spring stateless; cần state → DB/cache.

## 11. TESTING
* **Bắt buộc test cho logic tiền**: tính phí, lãi, làm tròn, chia tách — test boundary (0, âm, max, scale lẻ, currency không decimal như VND/JPY).
* **Test concurrency cho luồng số dư**: ít nhất 1 test chứng minh không âm quỹ / không double-spend khi 2 request song song.
* **Test state machine**: mọi transition không hợp lệ phải bị chặn.
* **Integration test dùng Testcontainers** (DB thật), không chỉ H2 — hành vi lock/constraint khác nhau giữa DB.
