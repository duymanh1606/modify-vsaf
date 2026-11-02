# STEP 06: FINAL ASSEMBLY + DUAL-WRITE

> **Thực hiện bởi:** Agent UXS0 (UX Sketch Lead — Sally)
> **Tuân thủ:** [iron_rules.md](../principles/iron_rules.md) — emphasize **R1, R2**.

## 1. Mục tiêu

Hợp nhất parts thành Master Sketch + dual-write canonical (overwrite latest) + archive (versioned snapshot).

## 2. Đầu vào

| Part file | Section đích |
|:--|:--|
| Master scaffold (đã có §1 Executive Brief từ Step 01) | §1 |
| `uxs1_personas_part.md` | §2 |
| `uxs0_journey_part.md` | §3 + §4 + §5 |

## 3. Chỉ thị thực thi

### 3.1. Verbatim Injection (R1)

**ĐÂY LÀ BƯỚC HỢP NHẤT CUỐI CÙNG. Bơm nguyên văn theo R1, không tóm tắt theo R2.**

1. Mở Master scaffold tại `{planning_artifacts}/ux_sketch.md`.
2. Đọc TỪNG part file theo thứ tự:
   - `uxs1_personas_part.md` → §2
   - `uxs0_journey_part.md` → §3 + §4 + §5
3. **Bơm nguyên văn** vào section tương ứng. KHÔNG tóm tắt, KHÔNG diễn đạt lại, KHÔNG bỏ sót diagram / row nào của Screen Intent Table.
4. Xóa GENERATION INSTRUCTION comments khỏi template.
5. Cập nhật frontmatter:
   ```yaml
   stepsCompleted: [step-01, step-02, step-03, step-04, step-05, step-06]
   inputDocuments: [path/to/prd.md, path/to/epics.md]
   ```
6. Update Change Log nếu có sửa đổi trong validation (Step 05 loop back).

### 3.1b. Preview Index (append cuối §4 — machine-readable mapping cho downstream)

Cuối §4 của master, thêm bảng **Preview Index** — downstream (`feature-design` Stage 4a) resolve frame liên quan unit của mình theo bảng NÀY, không parse HTML:

```markdown
### Preview Index

| Screen (sketch identifier) | Journey | Preview anchor |
|:--|:--|:--|
| Compose Message | J1 Onboarding | previews/{feature_slug}_ux_sketch_preview.html#compose-message |
```

- ĐÚNG 1 hàng / row Screen Intent Table §4. `Preview anchor` = `previews/{feature_slug}_ux_sketch_preview.html#{screen_slug}` — relative từ vị trí `ux_sketch.md` (cùng folder cha với `previews/`). Anchor này dùng được cả khi mở file tĩnh (đọc) lẫn khi ghép sau session URL lavish (`…/session/{key}#{screen_slug}` — annotate được).
- `{screen_slug}` = kebab-case cột `Screen`, khớp 1-1 `<section id>` trong preview hi-fi (anchor contract step-05 §3.1b (b) mục 5). Mismatch → sửa cho khớp TRƯỚC khi dual-write.
- Preview chưa render (step-05 (b) bị bỏ sót) → quay lại chạy (b), KHÔNG ghi index rỗng. `sketch_preview: off` → bỏ hẳn bảng Preview Index, KHÔNG ghi anchor trỏ file không tồn tại.

### 3.2. Quick Audit

Trước khi dual-write, đối soát nhanh:

| Hạng mục | Đếm | Threshold |
|:--|:--|:--|
| Sections | 5 | = 5 (§1-§5) |
| Personas (§2) | — | 2-3 |
| Nav items cấp 1 (§3.1) | — | 3-5 |
| Integration points (§3.2) | — | ≥ 0 (greenfield OK) |
| Journeys (§4) | — | 1-2 |
| Screen Intent rows per journey | — | 3-5 (mỗi row đủ 6 cột: Screen / Role / Content blocks / Primary CTA / Branch / Trace) |
| Preview Index rows (§4 cuối) | — | = tổng Screen Intent rows §4; mỗi anchor khớp `<section id>` trong `previews/{feature_slug}_ux_sketch_preview.html` |
| Open Questions (§5) | — | 1-10 (sketch tốt thường phát hiện 3-7) |

Nếu mismatch → báo cáo, không tự fix (escalate user).

### 3.3. Dual-Write

**Auto-detect version N:**

```bash
ls {planning_artifacts}/archive/ux_sketch_v*.md 2>/dev/null
```

Nếu list rỗng → N = 1. Nếu có `ux_sketch_v3.md` là max → N = 4.

**Write 2 files:**

1. **Canonical (overwrite latest):** `{planning_artifacts}/ux_sketch.md`
2. **Archive (versioned snapshot):** `{planning_artifacts}/archive/ux_sketch_v{N}.md` — copy of canonical

Tạo thư mục `archive/` nếu chưa tồn tại:

```bash
mkdir -p {planning_artifacts}/archive
```

### 3.4. Bàn giao trên review surface **sống** (đóng session)

Session lavish mở ở [step-05](./step-05-validation.md) §3.1b (c) **vẫn đang sống** ở đây (step-05 cố ý không `end`). Bàn giao mà không làm bước này = user nhận được 1 đường dẫn file tĩnh và phải tự gõ lệnh mới annotate lại được — đúng thứ (d) tồn tại để chặn. Trình tự:

1. `sketch_preview: off` → bỏ qua mục 3.4 hoàn toàn.
2. **Nội dung §1-§5 có đổi trong lúc assemble?** (Step 05 loop-back, sửa Preview Index, đổi tên screen…) → re-render preview (step-05 §3.1b (b)) TRƯỚC, để bản đang mở khớp master. Lavish watch file → browser tự reload, không cần mở lại session.
3. **Resume + poll lần cuối** (agent chạy, không bắt user gõ):
   ```bash
   npx -y lavish-axi "{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html"
   npx -y lavish-axi poll "…_ux_sketch_preview.html" --agent-reply "UX Sketch {feature_slug} đã chốt: {N journeys} journey / {N screens} frame, {N open_questions} Open Questions. Sketch vẫn mở — click element bất kỳ để comment, tôi sửa part + re-render + ghi lại master. Xong thì bấm Send & End."
   ```
   Session đã bị user tự end ở Step 05 (Send & End) → **KHÔNG tự mở lại**, chỉ đưa lệnh `npx -y lavish-axi "<path>" --reopen` trong báo cáo và để user quyết.
4. **Feedback đến sau khi đã dual-write** → xử lý đúng bảng map step-05 §3.1b (c) mục 2, rồi chạy lại §3.1-§3.3 cho phần bị đổi (canonical + **ghi đè archive `v{N}` vừa tạo**, không đẻ version mới cho cùng 1 vòng bàn giao). Re-render preview + poll tiếp kèm `--agent-reply` báo đã áp gì.
5. **Đóng:** user bấm Send & End (poll báo kết thúc) hoặc xác nhận không sửa nữa → `npx -y lavish-axi end "…_ux_sketch_preview.html"`. Đây là chỗ DUY NHẤT trong workflow được chạy `end`.

## 4. Đầu ra yêu cầu

- **Master canonical:** `{planning_artifacts}/ux_sketch.md` (5 sections hoàn chỉnh)
- **Master archive:** `{planning_artifacts}/archive/ux_sketch_v{N}.md`
- Audit report: bảng đối soát
- Session lavish đã đóng đúng cách (§3.4 mục 5) — không để session treo, cũng không đóng sớm trước bàn giao
- Báo cáo cuối:
  > "UX SKETCH hoàn tất. {N personas} personas, {N nav_items} nav items, {N integration_points} integration points, {N journeys} journey với {N screens} screen, {N open_questions} Open Questions cho HLD. Preview hi-fi: `previews/{feature_slug}_ux_sketch_preview.html` (skin: {design source}) — mở lại để comment: `npx -y lavish-axi \"<path>\"`. Sẵn sàng handoff cho SA ở Stage 2."

## 5. Bàn giao

Trình bày cho User:
1. **Review surface trước, file sau:**
   - Session URL đang mở: `http://127.0.0.1:4387/session/{key}` — click là comment được ngay (§3.4). Nói trong chat thôi, **không ghi vào artifact**: URL machine-local, chỉ sống trên máy đang chạy session (step-05 §3.1b (d) mục 5).
   - Lệnh mở lại bất cứ lúc nào (URL không đổi — `{key}` = sha256 đường dẫn preview): `npx -y lavish-axi "{planning_artifacts}/previews/{feature_slug}_ux_sketch_preview.html"`. Nói rõ 1 dòng: mở file bằng `file://` chỉ xem được, `lavish-axi export` cũng chỉ ra bản tĩnh — annotate luôn cần lệnh trên (step-05 §3.1b (d)).
   - Đường dẫn Master file + archive.
2. Tóm tắt §5 Open Questions — danh sách câu hỏi gửi Tech Lead/SA ở Stage 2
3. Đề xuất next steps:
   - Trigger `/ntapp-architecture-design` ở Stage 2 với sketch là input bổ sung
   - SA xem §3 Rough IA để inform module breakdown trong HLD WBS
   - SA xem §5 Open Questions để giải đáp ở Module 0 / HLD §3.2.2 sequence diagrams

---

*Sketch hoàn tất. Đây là phiên bản v0 lightweight. UX Journey Spec + Conventions vẫn cần ở Stage 3b sau khi HLD/Module 0 ra (`/ntapp-ux-design`).*
