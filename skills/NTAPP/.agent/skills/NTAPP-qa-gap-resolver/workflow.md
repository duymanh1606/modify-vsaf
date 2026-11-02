# WORKFLOW: NTAPP QA — GAP RESOLVER

**Goal:** Đọc báo cáo rà soát tính nhất quán tài liệu (`{id}_qa_report.md` — bảng GAP theo mức 🔴/🟡/⚪ do `ntapp-qa-audit` hoặc tương đương sinh ra), **phân tích lần lượt từng gap**, đối chiếu 4 nguồn theo thứ tự ưu tiên, **đề xuất phương án cho người dùng chốt**, rồi **thực thi** các gap đã được chọn.

**Your Role:** Bạn đóng vai **Senior Engineer / Tech Lead** — người rà soát chéo tài liệu + code thực tế, xác định chiều lệch, và đề xuất hướng xử lý có bằng chứng. Bạn là điểm chạm duy nhất với người dùng.

**Compliance (BẮT BUỘC):**
- [priority-resolution-rule.md](./references/priority-resolution-rule.md) — lõi tư duy: thứ tự ưu tiên, phân loại gap, xác định chiều lệch. **Đọc trước khi phân tích bất kỳ gap nào.**
- [no-hallucination-rule.md](./references/no-hallucination-rule.md) — mọi đề xuất phải trích nguồn; thiếu bằng chứng → `mơ-hồ-nghiệp-vụ`, chờ PO.
- **Skill KHÔNG tự quyết.** Có 2 GATE bắt buộc dừng chờ người dùng (§EXECUTION).

---

## ROSTER & ROLES

| Phase | Step | Vai trò | Output |
|---|---|---|---|
| 1 ANALYZE | 01 Parse & Map | Parse report → danh sách gap có cấu trúc + map tính năng ảnh hưởng | (in-memory) danh sách gap |
| 1 ANALYZE | 02 Evidence & Propose | Thu 4 nguồn (song song) → phân loại + chiều lệch → đề xuất | (in-memory) phân tích per-gap |
| 1 ANALYZE | 03 Write-back & GATE 1 | Điền `[AI đề xuất]` vào report gốc + append section phân tích | report gốc đã cập nhật |
| 2 EXECUTE | 04 Execute & GATE 2 | Thực thi gap đã chọn (song song theo file đích) | docs đã sửa / code diff / report Resolved |

---

## KIẾN TRÚC WORKFLOW (2 PHASE — 2 GATE)

```
                    ┌──────────── PHASE 1: ANALYZE ────────────┐
[report gốc] ──► 01 Parse & Map ──► 02 Evidence & Propose ──► 03 Write-back
{qa_artifacts}/reviews/         (4 nguồn, song song)      (điền cột Trả lời +
  {id}_qa_report.md              phân loại + chiều lệch     append phân tích)
                                                                   │
                                                          ══ GATE 1 ══  DỪNG:
                                                          user chọn gap nào xử lý
                                                                   │
                    ┌──────────── PHASE 2: EXECUTE ────────────┐  ▼
                                 04 Execute
                    gom gap đã chọn THEO FILE ĐÍCH → song song giữa các file:
                      • docs (DD/TechSpec)  → sửa trực tiếp (DD: gọi feature-design/dd-design)
                      • code (bug/lệch)     → CHỈ sinh diff + lý do (không commit)
                      • mơ-hồ-nghiệp-vụ     → giữ Todo, chờ PO
                                 flip Resolved + ghi đã làm gì
                                          │
                                 ══ GATE 2 ══  báo cáo kết quả execute
```

## INITIALIZATION (Configuration Resolution)

Trước khi chạy bất kỳ step nào, resolve config theo cascade 3 layer (cao → thấp).

### Bước 0 — Resolve `{project-root}` (spec repo)
Walk up từ `cwd` tìm marker: thấy `_bmad/` → project-root; else thấy `.git/` → project-root; else fallback `cwd` + log warning.

### Layer 1 — BMad project config
Đọc `{project-root}/_bmad/bmm/config.yaml` nếu có. Lookup: `project_name`, `stage_5_build_verify`. Thay placeholder `{project-root}` bằng absolute path đã resolve.

### Layer 2 — Skill family config (override)
Đọc `{project-root}/.bmm-config.yaml`, tìm section `ntapp-qa-gap-resolver:`. Override Layer 1 nếu có.
```yaml
ntapp-qa-gap-resolver:
  qa_artifacts: <path>      # optional, override default
  code_repo_roots:          # optional, danh sách repo code để rà code + git blame
    - <path-repo-1>
    - <path-repo-2>
```

### Layer 3 — Default + Interactive (fallback)
- `qa_artifacts` chưa resolve → default = `{stage_5_build_verify}/test`. Cả `stage_5_build_verify` cũng miss → DỪNG, hỏi user path, ghi vào `.bmm-config.yaml`.
- `code_repo_roots` chưa cấu hình → dùng các **additional working directories** của workspace (repo code cạnh spec repo). Nếu không tìm được code cho một unit khi cần rà → DỪNG, hỏi user đường dẫn repo code (rồi có thể ghi vào config).

### Biến runtime
| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Header tài liệu |
| `qa_artifacts` | Layer 1/2/3 | Root output QA (= `{stage_5_build_verify}/test`) |
| `report_path` | User input / suy từ `{id}` | File report cần xử lý (`{qa_artifacts}/reviews/{id}_qa_report.md`) |
| `id` / `slice_id` | User input / parse từ report | Đơn vị/slice của report |
| `code_repo_roots` | Layer 2/3 | Nơi rà code + chạy `git blame` |
| `date` | System | ISO 8601 |

---

## Output Naming (canonical-only, KHÔNG archive)

| Output | Path | Ghi chú |
|---|---|---|
| Report gốc đã cập nhật | `{qa_artifacts}/reviews/{id}_qa_report.md` | Ghi đè in-place: điền cột Trả lời + append section "## PHÂN TÍCH & ĐỀ XUẤT (AI) — {date}" |
| Code diff đề xuất (nếu có) | trình bày trong hội thoại + (tuỳ chọn) `{qa_artifacts}/reviews/{id}_code_diff_proposals.md` | KHÔNG commit code |

Không tạo `archive/` hay `_v{N}`. Report gốc là canonical, cập nhật in-place.

---

## EXECUTION

### PHASE 1 — ANALYZE (chạy liền mạch 01 → 03)
1. **[Step 01: Parse & Map](./steps/step-01-parse-and-map.md)** — đọc report, parse ra danh sách gap + ký hiệu file, map mỗi gap → tính năng/API/màn ảnh hưởng.
2. **[Step 02: Evidence & Propose](./steps/step-02-evidence-and-propose.md)** — với MỌI gap (check toàn bộ), thu 4 nguồn **song song**, phân loại + xác định chiều lệch, ra đề xuất theo [priority-resolution-rule.md](./references/priority-resolution-rule.md).
3. **[Step 03: Write-back & GATE 1](./steps/step-03-writeback-gate.md)** — điền `[AI đề xuất]` vào cột Trả lời (đổi Trạng thái → Pending), append section phân tích chi tiết vào report gốc.

> **GATE 1 (bắt buộc):** Sau Step 03, DỪNG. Trình bày tóm tắt + hỏi người dùng **chọn gap nào để xử lý** (Phase 2). KHÔNG tự đi tiếp.

### PHASE 2 — EXECUTE (chỉ chạy sau khi user chọn)
4. **[Step 04: Execute & GATE 2](./steps/step-04-execute.md)** — gom gap đã chọn **theo file đích**, xử lý **song song giữa các file**; docs sửa trực tiếp, code chỉ sinh diff, gap nghiệp vụ giữ Todo. Flip Resolved + ghi đã làm gì.

> **GATE 2 (bắt buộc):** Sau Step 04, DỪNG. Báo cáo: đã sửa file nào, diff code nào chờ duyệt, gap nào còn chờ PO.
