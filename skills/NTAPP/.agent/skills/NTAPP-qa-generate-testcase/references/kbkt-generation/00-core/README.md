# Core Rules

Nhóm rule lõi áp dụng cho toàn bộ quá trình sinh KBKT.

Core rule không phụ thuộc control cụ thể. Bất cứ testcase nào được sinh ra cũng phải tuân thủ nhóm rule này.

---

## Quan hệ với Iron Rules của pipeline

Iron Rules bất biến của pipeline này nằm tại [principles/iron_rules.md](../../../principles/iron_rules.md) (R1–R7). Các core rule trong thư mục này là chi tiết thực thi, ánh xạ tới Iron Rules như sau:

| Iron Rule | Chi tiết thực thi trong thư mục này |
|---|---|
| **R1 (Zero-Fabrication)** | `no-hallucination-rule.md` + `ntapp-core-compliance.md` |
| **R2 (Zero-Summarization)** | `ntapp-core-compliance.md` + `kbkt-format-rule.md` (1-1 Mapping, cấm gộp) |
| **R3 (Traceability)** | `kbkt-format-rule.md` § định danh & viết steps |
| **R4 (Coverage & QC Gate)** | `test-coverage-checklist-rule.md` + `08-review/kbkt-review-gate-rule.md` |
| **R5 (Missing-Input Handling)** | `no-hallucination-rule.md` § Khi thiếu thông tin |
