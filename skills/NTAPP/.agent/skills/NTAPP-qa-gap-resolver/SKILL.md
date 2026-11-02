---
name: ntapp-qa-gap-resolver
description: 'Đọc báo cáo rà soát tính nhất quán tài liệu (dạng {id}_qa_report.md / ambiguity-audit — bảng GAP theo mức 🔴/🟡/⚪), phân tích lần lượt từng gap: map ra tính năng ảnh hưởng, đối chiếu 4 nguồn (dữ liệu thực tế nếu report cite → TechSpec/Contract SSoT → DD → code thực tế để đo độ lệch), phân loại gap (stale-docs / code-mới-docs-cũ / lệch-code-vs-contract / mơ-hồ-nghiệp-vụ) và đề xuất phương án xử lý theo thứ tự ưu tiên. Phase 1 ANALYZE điền [AI đề xuất] vào cột Trả lời của report gốc + append section phân tích → GATE chờ user chọn gap. Phase 2 EXECUTE các gap đã chọn (song song theo file đích): docs sửa trực tiếp, code chỉ sinh diff đề xuất, gap nghiệp vụ chờ PO. Dùng khi người dùng nói "phân tích qa report", "xử lý gap", "giải quyết điểm không nhất quán", "resolve ambiguity report".'
---

# NTAPP QA — Gap Resolver

Đọc báo cáo rà soát tính nhất quán (`{id}_qa_report.md`), phân tích từng gap dựa trên 4 nguồn theo thứ tự ưu tiên đã chốt, đề xuất phương án cho người dùng chốt, rồi thực thi các gap được chọn.

**Skill KHÔNG tự quyết** — mọi gap đưa người dùng/PO chốt. Skill chỉ *phân tích + đề xuất* (Phase 1), và chỉ *thực thi* gap đã được chọn (Phase 2).

Đọc đầy đủ và tuân theo: `./workflow.md`
