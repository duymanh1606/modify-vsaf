# WORKFLOW: NTAPP QA — AMBIGUITY & QUALITY AUDIT (SHIFT-LEFT)

**Goal:** Rà soát chéo đa tầng Specs L2 + file thiết kế chi tiết `_detailed_design` (bỏ phần Đảm bảo chất lượng / Kiểm thử) của một đơn vị `{id}` để phát hiện sớm các điểm nhập nhằng (ambiguity), Logic / Parameter / Integration Gaps và UI-Logic inconsistency — TRƯỚC khi viết bất kỳ testcase nào — rồi kết tinh thành Checklist Q&A có sẵn phương án gợi ý cho PO/Lead làm rõ.

**Your Role:** Bạn đóng vai **Senior QA Engineer** ([agents/agent_qa_auditor.md](./agents/agent_qa_auditor.md)) — Shift-Left auditor, quét chéo specs, lập Gap Analysis và soạn câu hỏi Q&A. Bạn là điểm chạm duy nhất với người dùng.

**Compliance:** Workflow này tuân thủ các reference trong [`./references/`](./references/): [ntapp-core-compliance.md](./references/ntapp-core-compliance.md) (Iron Rules — Zero-Fabrication, Zero-Summarization, Traceability) và [no-hallucination-rule.md](./references/no-hallucination-rule.md). Tuyệt đối KHÔNG bịa giải pháp cho gap phát hiện được — mọi điểm thiếu định dạng thành câu hỏi `[TBD]`. Input thiếu/không đọc được → DỪNG, hỏi user; KHÔNG sinh mock.

---

## ROSTER & ROLES

| Step | Agent | Vai trò | Output |
|---|---|---|---|
| 01 | QA Auditor (Senior QA Engineer) | Ambiguity & Gap Analysis + Q&A handshake | `{qa_artifacts}/{id}/{id}_qa_report.md` |

Skill 1-agent: toàn bộ luồng do QA Auditor thực thi tuần tự.

## KIẾN TRÚC WORKFLOW (MICRO-FILE ARCHITECTURE)

Mỗi step là một file độc lập trong `./steps/` với contract I/O rõ ràng. Step mở đầu bằng `> Acting as:` trỏ persona trong `./agents/`.

```
┌─────────────────────────────────────────────────────────┐
│  STEP 01: AMBIGUITY & QUALITY AUDIT                     │
│  (Senior QA Engineer — Shift-Left)                      │
│  → Đọc Specs L2 + DD (bỏ phần QA/Kiểm thử), quét Gaps,  │
│    lập Gap Analysis + Checklist Q&A                      │
│  → Output: {qa_artifacts}/{id}/{id}_qa_report.md        │
│  → GATE: DỪNG, chờ user trả lời Q&A trong file báo cáo  │
└─────────────────────────────────────────────────────────┘
```

## INITIALIZATION (Configuration Resolution)

Trước khi chạy bất kỳ step nào, resolve config theo cascade 3 layer (cao → thấp).

### Bước 0 — Resolve `{project-root}`
Walk up từ `cwd` tìm marker: thấy `_bmad/` → project-root; else thấy `.git/` → project-root; else fallback `cwd` + log warning.

### Layer 1 — BMad project config
Đọc `{project-root}/_bmad/bmm/config.yaml` nếu có. Lookup: `project_name`, `stage_5_build_verify`, `stage_4_design`. Thay placeholder `{project-root}` bằng absolute path đã resolve.

### Layer 2 — Skill family config (override)
Đọc `{project-root}/.bmm-config.yaml`, tìm section `ntapp-qa-audit:`. Override Layer 1 nếu có.
```yaml
ntapp-qa-audit:
  qa_artifacts: <path>            # optional, override default
  detailed_design_root: <path>    # optional, nơi tìm {id}_detailed_design.md
```

### Layer 3 — Default + Interactive (fallback)
Nếu `qa_artifacts` chưa resolve được: default = `{stage_5_build_verify}/test`
(tức `{project-root}/NTAPP-output/Stage_5_Build_Verify/test`). Nếu cả `stage_5_build_verify` cũng miss → DỪNG, hỏi user path, rồi ghi vào `.bmm-config.yaml` section `ntapp-qa-audit:`.

Nếu `detailed_design_root` chưa resolve được: default = `{stage_4_design}/detailed_design`. Nếu cả `stage_4_design` cũng miss → DỪNG, hỏi user nơi chứa các file `{id}_detailed_design.md`.

### Biến runtime
| Biến | Nguồn | Ghi chú |
|---|---|---|
| `project_name` | Layer 1/2/3 | Header tài liệu |
| `qa_artifacts` | Layer 1/2/3 | Root output QA (= `{stage_5_build_verify}/test`) |
| `detailed_design_root` | Layer 1/2/3 | Nơi tìm `{id}_detailed_design.md` (default `{stage_4_design}/detailed_design`) |
| `id` | User input | Đơn vị cần xử lý (SLICE / HUB / WGT / SCR / MPF…) |
| `template_path` | Hardcode | `./templates/...` — relative to **skill root** |
| `agent_personas_path` | Hardcode | `./agents/` — relative skill root |
| `date` | System | ISO 8601 |

---

## Output Naming

| Output | Path | Versioning |
|---|---|---|
| Q&A Report — canonical | `{qa_artifacts}/{id}/{id}_qa_report.md` | 1 **thư mục con riêng theo chức năng** `{id}` (vd `test/HUB-01/`, `test/SLICE-03/`), KHÔNG gom chung vào `reviews/`; overwrite mỗi run (latest pointer) — KHÔNG archive, KHÔNG `_v{N}` |

---

## EXECUTION

Thực hiện tuần tự theo file hướng dẫn trong `./steps/`:

1. **[Step 01: Ambiguity & Quality Audit](./steps/step-01-ambiguity-audit.md)** → `{qa_artifacts}/{id}/{id}_qa_report.md`.

> **GATE (bắt buộc):** Sau khi xuất báo cáo, DỪNG lại và yêu cầu người dùng/PO điền phản hồi trực tiếp vào cột Q&A trong file báo cáo. KHÔNG tự đi tiếp — đây là tiền đề để chuyển sang giai đoạn thiết kế testcase.
