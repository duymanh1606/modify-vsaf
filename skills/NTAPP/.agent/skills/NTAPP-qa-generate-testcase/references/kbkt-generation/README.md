# Danh mục Rule Sinh KBKT

Thư mục này chứa toàn bộ các quy tắc sinh Testcase Manual (KBKT) chuyên biệt cho từng loại UI/Control.

| Nhóm | File | Mục đích |
| --- | --- | --- |
| Core | `00-core/kbkt-format-rule.md` | Chuẩn format testcase |
| Core | `00-core/no-hallucination-rule.md` | Chặn tự đoán |
| Core | `00-core/ntapp-core-compliance.md` | **[NEW]** NTAPP Compliance & Anti-Patterns |
| Core | `00-core/e2e-traceability-rule.md` | E2E Traceability & Tracer-bullet (UI → Gateway → BE → DB) |
| Core | `00-core/test-design-techniques-rule.md` | **[NEW]** Kỹ thuật thiết kế kịch bản |
| Core | `00-core/test-coverage-checklist-rule.md` | **[NEW]** Checklist vét cạn độ bao phủ |
| UI | `01-ui/screen-default-display-rule.md` | Hiển thị mặc định |
| UI | `01-ui/layout-visual-rule.md` | Layout/font/chính tả |
| UI | `01-ui/keyboard-navigation-rule.md` | Tab/Shift-Tab/Enter |
| UI | `01-ui/responsive-zoom-rule.md` | Zoom/responsive |
| Input | `02-input/textbox-base-rule.md` | Textbox/searchbox |
| Input | `02-input/required-field-rule.md` | Required field |
| Input | `02-input/space-handling-rule.md` | Khoảng trắng |
| Input | `02-input/maxlength-rule.md` | Maxlength |
| Input | `02-input/security-input-rule.md` | HTML/JS/security input |
| Input | `02-input/datepicker-rule.md` | **[NEW]** Datepicker, Datetime |
| Input | `02-input/file-upload-rule.md` | **[NEW]** File upload, kéo thả |
| Selection | `03-selection/combobox-base-rule.md` | Combobox |
| Selection | `03-selection/dependent-combobox-rule.md` | Combobox phụ thuộc |
| Selection | `03-selection/checkbox-rule.md` | **[NEW]** Checkbox |
| Selection | `03-selection/radio-rule.md` | **[NEW]** Radio button |
| Dynamic | `04-dynamic-form/multiple-group-toggle-rule.md` | Toggle hiện/ẩn field |
| Dynamic | `04-dynamic-form/dynamic-row-add-remove-rule.md` | Icon + / - |
| Dynamic | `04-dynamic-form/dynamic-form-rendering-rule.md` | **[NEW]** Render Form động theo Profile |
| Filter | `05-dependent-filter/filter-rule-block-rule.md` | Khối Filter Rules |
| Filter | `05-dependent-filter/filter-save-validation-rule.md` | Validate khi lưu filter |
| Validation | `06-validation/inline-error-rule.md` | Lỗi inline |
| Validation | `06-validation/duplicate-data-rule.md` | Dữ liệu trùng |
| Validation | `06-validation/field-level-validation-rule.md` | **[NEW]** Bảng trạm kiểm duyệt theo loại Field |
| Validation | `06-validation/error-response-behavior-rule.md` | **[NEW]** Hành vi phản hồi per mã lỗi (catalog) |
| Save/Cancel | `07-save-cancel/save-button-rule.md` | Button Lưu |
| Save/Cancel | `07-save-cancel/cancel-button-rule.md` | Button Hủy |
| Save/Cancel | `07-save-cancel/action-button-rule.md` | **[NEW]** Mọi button điều hướng/action nghiệp vụ (click → điều hướng/xử lý + click nhiều lần) |
| Review | `08-review/kbkt-review-gate-rule.md` | Review KBKT (Tích hợp NTAPP QC Checklist) |
| Review | `08-review/ntapp-review-anti-patterns.md` | **[NEW]** NTAPP Review Anti-Patterns |
| Review | `08-review/compliance-audit-rule.md` | **[NEW]** Rà soát tính tuân thủ (Compliance Audit) |
| Review | `08-review/coverage-audit-rule.md` | **[NEW]** Rà soát độ bao phủ (Coverage Audit) |
| Data Grid | `09-data-grid/grid-base-rule.md` | **[NEW]** Phân trang, Sorting, Actions |
| Backend | `10-be/backend-resilience-rule.md` | **[NEW]** Kháng lỗi & phục hồi Backend |
| Backend | `10-be/data-visibility-rule.md` | **[NEW]** Phạm vi hiển thị dữ liệu theo actor/role (data scoping) |
| Filter | `11-independent-filter/independent-filter-rule.md` | **[NEW]** Bộ lọc độc lập (Search/Filter) |
