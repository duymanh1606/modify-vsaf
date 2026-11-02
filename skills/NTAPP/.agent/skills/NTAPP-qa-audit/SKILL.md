---
name: ntapp-qa-audit
description: 'Rà soát Shift-Left tài liệu Specs L2 + file thiết kế chi tiết `_detailed_design` (bỏ phần Đảm bảo chất lượng / Kiểm thử), tìm các điểm nhập nhằng (ambiguity), Logic/Parameter/Integration Gaps và UI-Logic inconsistency, rồi tạo danh sách câu hỏi Q&A có sẵn phương án gợi ý để QA Lead/PO làm rõ TRƯỚC khi thiết kế testcase. Input: Specs + `{id}_detailed_design.md` của `{id}` → Output: `{id}_qa_report.md` (Gap Analysis + Checklist Q&A). Workflow DỪNG chờ user trả lời (gate). Alias lệnh cũ: `/audit_advanced_qa`. Dùng khi người dùng nói "audit specs", "rà soát ambiguity", "shift-left testing", "gap analysis", "Q&A trước khi viết testcase".'
---

# NTAPP QA — Ambiguity & Quality Audit (Shift-Left)

Rà soát chéo đa tầng đặc tả + file thiết kế chi tiết để phát hiện sớm lỗ hổng logic, tham số biên mập mờ và bất đồng bộ FE-BE, kết tinh thành Checklist Q&A cho PO/Lead làm rõ trước khi viết bất kỳ testcase nào.

Đọc đầy đủ và tuân theo: `./workflow.md`
