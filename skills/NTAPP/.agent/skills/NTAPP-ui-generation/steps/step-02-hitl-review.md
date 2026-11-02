# Step 2: Human-in-the-Loop Review
> 🎭 HITL gate — không có persona agent; bạn điều phối review giữa DS Owner và workflow. Global rules (U1–U5) ở `../workflow.md`.
> ⛔ Chỉ đọc step kế SAU KHI qua [GATE] ở cuối file này ([A] Approved).

## GOAL
Đảm bảo proposed Design System updates được review và approve chính thức bởi DS Owner / approver (vai trò team-defined: vd Lead FE, DSO, System Architect) trước khi schema generation tiếp tục.

## 1. Inputs

- `{design_system_root}/feature_deltas/{id}/proposed_ds_updates.md` — vừa sinh ở Step 1.
- `master_token.json`, `components_metadata.json` — Master DS hiện tại (để DSO đối chiếu khi review).

## 2. Pipeline

### Stage 2.1: Present findings

Show nội dung `proposed_ds_updates.md` (vừa sinh ở Step 1, đặt tại `{design_system_root}/feature_deltas/{id}/`) cho user. Highlight:
- Tổng số `[NEW]` items + `[MODIFIED]` items + `[WARNINGS]` entries (đặc biệt `WCAG_CONTRAST_FAIL` — block).
- Bảng `[REUSE AUDIT]` — DSO soi cột `Reuse rejection` của mỗi `[NEW]`: candidate bị loại có đáng loại không.
- Hint path tới file để DSO mở trực tiếp trong editor (markdown checkbox dễ tick).

### Stage 2.1b: Visual delta preview (optional — `hitl_surface: lavish`)

Chạy khi `.bmm-config.yaml` block skill có `hitl_surface: lavish` (default `markdown` — bỏ qua stage này; headless/CI luôn dùng markdown). Biến review text thành review **trên bản render** để DSO thấy proposal trông thế nào trước khi approve:

1. **Generate preview HTML** (disposable — KHÔNG commit, KHÔNG phải SSoT; schema/proposal vẫn là artifact chuẩn):
   - Path: `{design_system_root}/feature_deltas/{id}/preview/delta_preview.html`.
   - Nội dung: mỗi item `[NEW]`/`[MODIFIED]` render các variants × states khai báo trong proposal, style bằng **CSS vars resolve từ `master_token.json`** (+ giá trị token đang propose) — TUYỆT ĐỐI không dùng CDN framework/DaisyUI/Tailwind default (đó chính là failure mode "library-default look" cần chặn).
   - Cạnh mỗi `[NEW]`: render **top-3 reuse candidates** từ `[REUSE AUDIT]` (theo `tokens_used` + variants của chúng trong `components_metadata.json`) để DSO so trực tiếp "cái đề xuất" vs "cái đang có".
   - Kèm strip ảnh từ `{design_system_root}/_reference/pages/` (nếu có) làm bối cảnh style thật.
2. **Mở review — AGENT chạy lệnh:** `npx -y lavish-axi "{path}/delta_preview.html"` rồi `npx -y lavish-axi poll "{path}/delta_preview.html" --agent-reply "Delta preview {id}: N NEW / M MODIFIED — annotate trực tiếp item cần sửa"`. Lệnh mở in ra session URL `http://127.0.0.1:4387/session/{key}` — **đưa URL cho DSO**; mở file bằng `file://` chỉ xem được (chrome annotate do server inject), đừng bảo DSO tự dựng session.
3. **Map feedback:** annotation của DSO → quay lại Step 1 refine ([R]) hoặc DSO tick/untick trong `proposed_ds_updates.md` như thường. `layout_warnings` từ lavish (nếu có) chỉ áp cho preview — sửa preview, không ảnh hưởng proposal.
4. Kết thúc: `npx -y lavish-axi end "{path}/delta_preview.html"` — chạy **sau khi DSO confirm ở Stage 2.2**, KHÔNG đóng ngay cuối 2.1b (DSO còn phải tick/untick checkbox trong `proposed_ds_updates.md` khi đang nhìn preview; đóng sớm = DSO mất visual giữa lúc quyết). Guardrails: KHÔNG chạy `lavish-axi share` (đẩy spec nội bộ lên host bên thứ 3); telemetry tắt qua `LAVISH_AXI_TELEMETRY=0` (xem CLAUDE.md).

### Stage 2.2: Wait DSO reply (HALT)

> [!IMPORTANT]
> **HALT:** PHẢI dừng ở đây và đợi user confirm rằng Design System updates đã được commit hoặc approve chính thức. KHÔNG proceed Step 3 cho đến khi nhận confirmation này.

DSO actions trên report (làm trong editor):
- Tick checkbox `[x]` cho proposals đồng ý.
- Untick `[ ]` cho proposals reject (downstream skill bỏ qua khi apply).
- Resolve `[WARNINGS]` entries (vd: consolidate `STYLE_FRAGMENTATION` qua coordination với owner sibling proposal).
- Reply tại đây để báo trạng thái.

### Stage 2.3: Commit path (agentic / manual)

Sau khi DSO approve:

- **Khuyến nghị (agentic path):** DSO/UI Engineer gõ `/ntapp-ds-build-component`. Skill consume `proposed_ds_updates.md`, apply NEW/MODIFIED tokens vào `master_token.json`, scaffold/patch components, update `components_metadata.json`, sinh `build_report.md` (artifact bắt buộc cho pre-commit Rule 7).
- **Manual fallback:** DSO có thể sửa thủ công `master_token.json` / `components_metadata.json` cho trường hợp khẩn — nhưng vẫn cần `build_report.md` (chạy `/ntapp-ds-build-component` sau hoặc sinh tay) trước khi commit feature code, nếu không pre-commit hook sẽ block.

### Stage 2.4: Re-parse approval status

Sau khi DSO reply `[A]` Approved:
- Validate JSON files (`master_token.json`, `components_metadata.json`) vẫn parse-able sau khi DSO edit (nếu manual path).
- Pass validation → transition Step 3.

## 3. Decision Points

### USER MENU

- **[A] Approved**: DS updates đã commit (qua `/ntapp-ds-build-component` hoặc manual). Proceed Step 3.
- **[R] Refine**: Cần thay đổi một số proposals. Quay lại Step 1.
- **[S] Stop**: Abort process.

### Auxiliary

- **DSO reply `[A]` nhưng JSON files invalid** (manual path sai cú pháp) → STOP: *"`master_token.json` hoặc `components_metadata.json` parse fail sau khi DSO edit. Fix JSON syntax rồi reply lại `[A]`."*
- **DSO reply `[A]` nhưng `proposed_ds_updates.md` không tồn tại** (vd: agent invoke step-02 đơn lẻ) → quay lại Step 1.
- **DSO không reply** (idle timeout) → skill state vẫn HALT, no auto-decision. DSO chạy lại skill khi sẵn sàng.

## 4. Output

- KHÔNG sinh file mới ở step này. Chỉ confirm approval state để gate Step 3.
- (Side effect khi DSO chọn agentic path) `master_token.json` + `components_metadata.json` + `build_report.md` được sinh/update bởi `/ntapp-ds-build-component`.

## [GATE: DSO APPROVE] — ⛔ DỪNG TẠI ĐÂY
> **HALT:** PHẢI đợi DSO/approver reply (Stage 2.2). Phân nhánh theo USER MENU (§3):
> - **[A] Approved** → tiến Step 3 (forward edge dưới).
> - **[R] Refine** → quay lại `./step-01-audit.md` (re-audit; không phải forward edge).
> - **[S] Stop** → abort workflow.
> KHÔNG đọc step kế cho đến khi DSO reply `[A]`.

**Next:** [A] Approved → Read fully and follow `./step-03-schema-gen.md`
