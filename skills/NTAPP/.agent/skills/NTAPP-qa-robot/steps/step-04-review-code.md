# STEP 04: REVIEW ROBOT CODE (kiểm trước khi chạy test)

> **Acting as:** [Agent Robot Reviewer](../agents/agent_robot_reviewer.md) — kiểm độc lập, **KHÔNG sửa code**.
> **BẮT BUỘC chạy trong subagent riêng** (context sạch), truyền đủ:
> 1. **Hướng dẫn:** file này + [`iron_rules.md`](../principles/iron_rules.md) (absolute path).
> 2. **Biến:** `code_repo_root`, `manual_testcase_path` (absolute), `qa_artifacts`, `id`, `surface_type`, `review_escalation`, `gen_run_id`. *(`review_scope` step này tự tính ở §2 — chỉ truyền vào khi muốn ép `full`.)*

---

> ⛔ Vào được step này nghĩa là cổng HITL `review_gate` ở [step-03 §6](./step-03-generate-suite.md) đã được user duyệt. Dispatch lỗi → DỪNG báo user; CẤM tự review thay.

## 1. Phạm vi

Chấm **đúng 6 Lõi** ở §3, không chấm gì ngoài đó. Vi phạm ghi `file:dòng` + ảnh hưởng thật + cách sửa; Generator sửa ở Step 02/03.

**1 agent duy nhất**, không shard. Không đọc hết trong 1 lượt thì chia theo file `.robot`, gộp vào 1 báo cáo.

Tối đa **2 vòng sửa**; vòng 3 FAIL → xử theo `review_escalation` (§4).

**Rule là chuẩn để chấm, mở đúng § được dẫn ở từng Lõi trước khi kết luận** — [iron_rules](../principles/iron_rules.md) · [robot_rules](../references/automation/auto_robot_rules.md) · [framework_structure](../references/automation/auto_framework_structure.md) · [locator_strategy](../references/automation/auto_locator_strategy.md) · [coding_convention](../references/automation/auto_coding_convention.md) · [db_oracle_rules](../references/automation/auto_db_oracle_rules.md). Không dẫn được rule ID + § cho một vi phạm thì **không được ghi nó thành vi phạm** — để ở phần nhận xét thêm.

## 2. Input

| Nguồn | Dùng để |
|---|---|
| `tests/`, `actions/`, `configs/`, `libraries/`, `datatest/` tại `{code_repo_root}` | code cần kiểm |
| `{id}_testspec.feature` | **canonical** cho bước + expected |
| `{manual_testcase_path}` | thước đo **chỉ khi** lane HUB legacy không có `.feature`; path luôn dùng để tính nơi lưu dự phòng (§5) |
| `{id}_fixtures.yaml`, `{qa_artifacts}/data_sources.yaml` | thước đo dữ liệu |
| `datatest/{id}_gen_manifest.yaml` | `touched_files`, `last_gen_run` per-case → phạm vi `changed` |
| `[Tags]` + `Skip` trong `.robot` | trạng thái run/pending/tbd — cấm bám plan cũ |
| dòng trạng thái `results/{id}_robot_review.md` | tính `round`: trùng `gen_run_id` → `round+1`, ngược lại `round = 1` |

**`review_scope` — tự tính:** có báo cáo cũ cùng `gen_run_id` → `changed`; ngược lại `full`.

`changed` chỉ đọc 3 tập, cấm quét cả cây: (1) `touched_files` có `round = round hiện tại − 1`, hoặc thiếu nhãn `round`; (2) mã `KB-*` ở trường `Case:` của vi phạm vòng trước; (3) lõi vòng trước `FAIL`/`UNVERIFIED`. Lõi `PASS` vòng trước, không đụng 3 tập trên → ghi `PASS (vòng N, không thay đổi)`, không đọc lại.

⛔ **Lõi 1, 2, 4 chấm bằng MỘT lượt đọc/case:** mở case 1 lần, đặt cạnh nhau `When`/`Then` của scenario cùng mã ⟷ thân Test Case ⟷ thân keyword nó gọi, trả lời cả 3 lõi.

## 3. Sáu Lõi

**🔵 Lõi 1 — Khớp bước hành động** · R2
Mọi mệnh đề `When`/`And` của scenario cùng mã trong `.feature` (`.md` chỉ khi vắng `.feature`) phải được **thực thi thật**, kể cả gesture không-nhập-liệu (click, focus out, paste, Enter, double-click).
Gom chuỗi bước vào 1 keyword nghiệp vụ **KHÔNG phải vi phạm** — mở thân keyword để xác minh. Vi phạm là khi gesture không được thực thi ở đâu cả, hoặc 2 scenario bị nhồi vào 1 test.

**🔵 Lõi 2 — Assert thật & phủ đều Oracle** · R11 · R13 · [robot §7](../references/automation/auto_robot_rules.md)
- Không "nuốt assert": gán biến / ghi log mà không gọi lệnh so sánh thực tế; hoặc gom assert vào keyword tên chung chung (`Should Be Complete` / `Valid` / `Correct`, `Verify Screen`) làm mất dấu kiểm cái gì.
- Mỗi mệnh đề kết quả mong muốn (`Then`) có ≥1 assert.
- Tag `@oracle:api` / `@oracle:db` phải có code check API / DB tương ứng, không chỉ kiểm UI.
- **Không còn `[Documentation]`** và **không còn dòng comment `#`** trong file vừa sinh/sửa. Còn sót → xoá ([coding_convention §4](../references/automation/auto_coding_convention.md)).
- Ca **tạo mới** có `@oracle:db`: phải assert từng cột của bản ghi vừa tạo đã có dữ liệu (kể cả bảng phụ thuộc). Chỉ `COUNT(*) = 1` hoặc chỉ kiểm cột trạng thái → FAIL ([db §9](../references/automation/auto_db_oracle_rules.md)).

**🔵 Lõi 3 — Độc lập dữ liệu & UI teardown** · R4 · R7b · R15 · [db §5 §11](../references/automation/auto_db_oracle_rules.md)
- Tên bản ghi tạo ra **unique per-run** (`$uuid` / `$timestamp`).
- Định danh kiểu chuỗi tạo ra **bắt đầu bằng `auto_`** (R7d). FAIL nếu thiếu tiền tố mà không thuộc ngoại lệ (trường chỉ nhận số, ca biên độ dài).
- Cấm xóa dữ liệu trong DB ở teardown (để giữ audit). Teardown chỉ reset trạng thái giao diện UI.
- Seed **kiểm trùng trước khi tạo mới**.

**🔵 Lõi 4 — Test "đỏ" khi app lỗi** · R11 · R14
Giả định app hỏng đúng điểm case này nhắm tới (microcopy lệch spec, grid sai số dòng, API lỗi) — test có **ĐỎ** không? Không đỏ = vi phạm.

**🔵 Lõi 5 — Chờ đợi an toàn** · R7 · R7s · [robot §3](../references/automation/auto_robot_rules.md)
Click / input phải chờ **lớp phủ (overlay, loading spinner) biến mất** mới thao tác — `Wait Until Element Is Enabled` KHÔNG đủ. Bề mặt `service`: ghi `N/A` phần overlay, thay bằng `Wait Until Keyword Succeeds`.

**🔵 Lõi 6 — Thiết kế sạch & chuẩn POM** · R4 · [robot §1 §4 §5](../references/automation/auto_robot_rules.md) · [structure §2-§3](../references/automation/auto_framework_structure.md)
- **POM:** `.robot` chỉ có Settings + Variables (hằng số) + Test Cases — không `*** Keywords ***`, không locator thô, không SQL (kể cả trong `[Teardown]`). Locator 100% ở `{Page}Variables.resource`. Keyword chạm locator / bảng DB của **một màn** — kể cả teardown của màn đó — thuộc Page/Service Keywords, không để trong `actions/common/`. Import một chiều: test → `configs/imports.resource` + BaseTest + file data (cấm import lẻ từng Keywords); Keywords → Variables của nó + BasePage; Variables không import Keywords; không import chéo page ↔ page.
- **KISS:** 1 keyword = 1 trách nhiệm, ≤20 bước. Dùng keyword thư viện chuẩn, không tự viết Python cho việc thư viện đã làm được.
- **YAGNI:** cấm khai biến / keyword / `[Arguments]` mà chưa test nào dùng tới (code mồ côi); không scaffold file config rỗng hoặc không được import. Bộ dò lời gọi phải xử dòng nối `...` và các dạng gọi động (`Run Keyword*`, `Wait Until Keyword Succeeds`, Setup/Teardown) — grep thô báo mồ côi oan.
- **DRY:** trùng tên **hoặc** trùng hành vi dù khác tên → giữ 1 đại diện. Cụm bước lặp ≥3 chỗ → keyword chung; Suite Setup/Teardown + fixtures điều hướng ở `SuiteFixtures.resource`, không copy-paste vào từng `.robot`; ≥3 locator chỉ khác 1 tham số → gom template.

⛔ **Sửa Lõi 6 phải kiểm lại Lõi 3** — xoá keyword "mồ côi" từng làm mất cơ chế sinh định danh unique.

## 4. Kết luận

* `FAIL` nếu còn ≥1 vi phạm chưa sửa/miễn, hoặc lõi chưa đọc hết phạm vi §2 (`UNVERIFIED`).
* Vòng 3 FAIL: `interactive` → DỪNG chờ user · `ci` → ghi `FAIL`, không chạy test, thoát.
* Mọi vi phạm đều phải sửa, không phân nặng nhẹ.
* **Waive:** cần `results/{id}_review_override.yaml` (`approved_by` người thật, bù trong 48h). Được miễn: Lõi 6, và phần unique-naming / seed của Lõi 3. Cấm miễn: Lõi 1, 2, 4, 5, và **teardown xoá sai bản ghi** (Lõi 3).

## 5. Báo cáo — `results/{id}_robot_review.md`

```markdown
# {id} Robot Code Review
`verdict: FAIL · round: <số> · gen_run_id: <id> · generated_at: <ngày>`

## 1. Tóm tắt kết quả
[FAIL/PASS: lý do chính trong 1-2 câu]
[Phạm vi: full | changed. Lõi nào `UNVERIFIED` (đọc chưa hết) — ghi rõ lõi + lý do, để trống nếu không có.]

## 2. Danh sách vi phạm (theo 6 Lõi Chính)
*Chỉ liệt kê lõi bị FAIL, bỏ qua lõi đạt.*

### 🔴 Lõi <số>: <tên lõi>
- **Case**: `KB-{id}-NN, KB-{id}-NN` — mọi mã bị ảnh hưởng (vòng sau đọc đúng các case này)
- **Vị trí**: `tests/<Screen>Test.robot:<dòng>` (+N chỗ tương tự, liệt kê ≤5 vị trí)
- **Nguyên nhân**: [nguyên nhân + ảnh hưởng thực tế: case nào xanh oan, treo ở đâu, dữ liệu nào hỏng]
- **Cách sửa đề xuất**: [cách khắc phục nhanh]

## 3. Nhật ký các vòng sửa (Rounds History)
- **Round <hiện tại>**: [X] lỗi mới (regression) do lần sửa trước gây ra, [Y] lỗi cũ chưa xong.
- **Round <trước>**: [tóm tắt ngắn gọn]
```

Cùng nguyên nhân + cùng cách sửa ở nhiều chỗ → **1 vi phạm**. `PASS` thì §2 ghi `Không có vi phạm`, §3 vẫn ghi nhật ký. Không kẻ bảng liệt kê chỗ đạt.

> **Nơi lưu:** `{code_repo_root}/results/`. Nếu repo gitignore `results/` → ghi thêm 1 bản vào thư mục cha của `{manual_testcase_path}` (KHÔNG tự ghép `{qa_artifacts}/{id}/`), chép nguyên văn, nêu cả 2 đường dẫn ở đầu báo cáo.

## 6. Sáu điều làm bản review bị loại

| # | Sai | Phải làm |
|---|---|---|
| A1 | Nhận xét không kèm `file:dòng` | Không chỉ được vị trí + trích code thì đừng ghi |
| A2 | Đoán qua tên keyword, chưa đọc thân | Kết luận theo nội dung đã đọc |
| A3 | Ghi đạt khi mới đọc mẫu vài case | `UNVERIFIED` → `FAIL` |
| A4 | Thấy chữ giống dấu hiệu sai là chấm luôn | Đọc cả dòng + ngữ cảnh (ghi chú / tên keyword / chuỗi thông báo) |
| A5 | Chẻ 1 vấn đề thành nhiều vi phạm, hoặc bỏ qua vì "không quan trọng" | Gộp theo nguyên nhân; ghi hết |
| A6 | Tự sửa code · kết luận "sản phẩm có bug" | Chỉ ghi vi phạm + gợi ý sửa; lệch spec → ghi "tài liệu và code test lệch nhau" + ai cần chốt (R11) |

⛔ Mỗi vi phạm phải nêu **hậu quả thật**; không nêu được thì không phải vi phạm. **0 vi phạm là kết quả hợp lệ.**

**Next:** Đọc và thực hiện theo `./step-05-execute-and-analyze-logs.md`
