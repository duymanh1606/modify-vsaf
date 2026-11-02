---
name: ntapp-qa-setup-data
description: 'Quản lý vòng đời dữ liệu test. Đọc manual testcase chuẩn 10 cột đã chốt, bóc tách dữ liệu mồi, sinh script Setup (pre-condition) + Teardown (post-condition) độc lập với isolation bằng timestamp/UUID. Có Reuse-Gate (Get-Or-Create): trước khi tạo mới, query 5 bản ghi automation gần nhất (hậu tố "auto") + chấm trạng thái theo precondition → tái sử dụng nếu thỏa, tạo mới ngay nếu không (đỡ mất thời gian). Input: manual testcase → output: script data tại {qa_artifacts}/data/. Sử dụng khi người dùng nói "setup test data", "/setup_test_data", "chuẩn bị dữ liệu mồi", "teardown dữ liệu test", "tái sử dụng data auto", "check data trước khi tạo".'
---

# NTAPP QA Setup Test Data

Quản lý vòng đời dữ liệu kiểm thử: phân tích kịch bản manual testcase đã chốt, bóc tách dữ liệu mồi, sinh cơ chế Setup/Teardown độc lập và sạch sẽ (Clean State) phục vụ Automation.

Đọc đầy đủ và tuân theo: `./workflow.md`
