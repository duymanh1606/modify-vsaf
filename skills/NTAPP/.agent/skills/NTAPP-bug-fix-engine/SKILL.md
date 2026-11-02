---
name: NTAPP-bug-fix-engine
description: 'Engine fix MỘT bug đã localize trên một WBS unit — ceremony-adaptive (gate bật/tắt theo lane / atdd_class / contract-change, không full-gate đồng đều; `severity` chỉ là tín hiệu phụ — ordering + fallback suy lane, không trực tiếp bật gate). Đây là LÕI dùng chung, được gọi bởi NTAPP-fix-bug (nguồn file BUGS-*.md, in-place-nocommit) và workflow bug-fix-batch (nguồn Jira, branch-commit); KHÔNG phải lệnh người dùng thường gõ trực tiếp. Chạy: root-cause (superpowers-systematic-debugging) → DD gate (reconstruct v1→v2 khi thiếu DD chạm contract) → ATDD gate (test-first RED→GREEN khi mandatory) → fix tối thiểu → pre-commit 9 rule → verify bậc cao nhất có sẵn → code-review → doc-sync spec. Tôn trọng dual-repo (spec ↔ code). Sử dụng khi một orchestration cần fix đúng một bug đã được localize + phân loại, hoặc khi người dùng chỉ định fix một bug đơn lẻ đã biết unit.'
---

# Bug-Fix Engine (ceremony-adaptive)

## Overview
Fix **đúng một bug đã được localize** trên một WBS unit, end-to-end, với **mức ceremony thích ứng** theo tín hiệu (`lane` / `atdd_class` / có chạm contract hay không — `severity` KHÔNG phải trục gate, xem bảng Inputs). Đây là **nguồn sự thật duy nhất** cho "làm sao fix đúng một bug" — cả `NTAPP-fix-bug` và workflow `bug-fix-batch` đều gọi engine này thay vì tự viết lại.

**Nguyên tắc cốt lõi:** gate KHÔNG luôn bật. Bug critical-domain / đổi contract → nghiêm (test-first RED→GREEN + DD reconstruct); bug vặt (express, style thuần) → nhẹ (fix + verify tĩnh). Nhờ đó batch hết over-fix bug nhỏ, còn fix-bug được rigor đúng lúc.

## When to use
- Một orchestration (NTAPP-fix-bug / bug-fix-batch) đã localize + phân loại một bug và cần **thực thi fix** cho một unit.
- Người dùng chỉ định fix **một bug đơn lẻ** đã biết chắc unit + file (edge case invoke trực tiếp).

## When NOT to use
- Chưa localize (chưa biết unit/file) → dùng intake trước: `receive-bug-jira` (Jira) hoặc `NTAPP-fix-bug` step-01 (file `BUGS-*.md`).
- Muốn gom nhóm N bug fix song song → `receive-bug-jira` + workflow `bug-fix-batch`.
- Feature mới theo WBS → `slice-loop` / `NTAPP-feature-design`.

## Inputs (caller truyền; engine tự classify lại nếu thiếu)
| Param | Bắt buộc | Ghi chú |
|---|---|---|
| `bug_context` | ✅ | keys/summary/expected/actual/evidence + unit(s) đã localize + files/dirs (+ ảnh nếu có) |
| `lane` | mặc định | `express` \| `path-b` \| `ad-hoc` — mức ceremony khuyến nghị; thiếu → engine suy từ severity/scope |
| `atdd_class` | mặc định | `mandatory` (khớp ≥1 trong 5 trigger §5.1) \| `optional`; thiếu → engine classify tại chỗ |
| `severity` | mặc định | Critical..Low (hoặc Jira `priority` từ nhánh batch) — **chỉ để ordering + suy `lane` khi thiếu**; KHÔNG trực tiếp bật gate nào |
| `commit_mode` | ✅ | `branch-commit` (commit lên branch trong worktree) \| `in-place-nocommit` (không commit) |
| `doc_sync_mode` | ✅ | `inline` (doc-sync ngay) \| `deferred` (chỉ emit TODO — orchestration sync serial để tránh tranh ghi spec repo khi fanout) |

**REQUIRED SUB-SKILL:** dùng `superpowers-systematic-debugging` cho root-cause (step-01) trước khi sửa bất kỳ dòng code nào.

## Workflow
Đọc đầy đủ và tuân theo **`./workflow.md`** (INITIALIZATION + CEREMONY RESOLVER + global rules + pipeline map). Progressive disclosure: đọc **đúng một step file mỗi lần**.
